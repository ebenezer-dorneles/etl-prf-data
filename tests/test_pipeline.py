import sqlite3

import pytest
import requests

from conftest import faz_zip, linha
from etl_prf import db, pipeline
from etl_prf.config import IDS_README, URL_DOWNLOAD, URL_PAGINA
from etl_prf.pipeline import formatar_resumo
from etl_prf.pipeline import run as _run
from test_crawler import Resp as RespPagina
from test_crawler import linha as linha_pagina
from test_drive import Resp, resp_ok
from test_latest import drive_de, linhas, log, zip_de

SENTINELA = "SENTINELA-XYZ-123"


def run(*args, **kw):
    """`readme={}`: só os anos da página de teste, sem o preenchimento de D-18."""
    return _run(*args, readme={}, **kw)


class Roteador:
    """Sessão falsa: a página e uma fila de respostas por ID do Drive; conta GETs por destino."""

    def __init__(self, anos, respostas=None) -> None:
        html = "<table>" + "".join(linha_pagina(a, IDS_README[a]) for a in anos) + "</table>"
        self.pagina = RespPagina(200, html)
        self.filas = {IDS_README[a]: list(r) for a, r in (respostas or {}).items()}
        self.gets = {}

    def get(self, url, **kw):
        self.gets[url] = self.gets.get(url, 0) + 1
        if url == URL_PAGINA:
            return self.pagina
        for id_, fila in self.filas.items():
            if url == URL_DOWNLOAD.format(id=id_):
                if not fila:
                    raise AssertionError(f"GET inesperado no Drive: {url}")
                r = fila.pop(0)
                if isinstance(r, Exception):
                    raise r
                return r
        raise AssertionError(f"URL inesperada: {url}")

    def n(self, ano) -> int:
        return self.gets.get(URL_DOWNLOAD.format(id=IDS_README[ano]), 0)


@pytest.fixture
def conn(tmp_path):
    c = db.conectar(tmp_path / "t.sqlite")
    yield c
    c.close()


def por_ano(ex):
    return {r.ano: r for r in ex.resultados}


def test_ac16_falha_em_um_ano_nao_impede_os_outros(conn, tmp_path):
    zip_de(tmp_path, 2018, 3)
    z20 = zip_de(tmp_path, 2020, 2)
    s = Roteador([2018, 2019, 2020], {2019: [Resp(b"", {}, 429)], 2020: [drive_de(z20)]})
    ex = run(conn, s, tmp_path)
    r = por_ano(ex)
    assert (r[2018].status, r[2019].status, r[2020].status) == ("ok", "erro", "ok")
    assert "429" in r[2019].mensagem
    assert ex.falhas == 1
    erro = [x for x in log(conn) if x["ano"] == 2019]
    assert [x["status"] for x in erro] == ["erro"] and "429" in erro[0]["mensagem"]
    assert (linhas(conn, 2018), linhas(conn, 2020)) == (3, 2)


def test_ac11_so_baixa_o_ano_sem_zip(conn, tmp_path):
    zip_de(tmp_path, 2018, 1)
    z19 = zip_de(tmp_path, 2019, 2)
    z19.rename(tmp_path / "guardado.bin")
    z20 = zip_de(tmp_path, 2020, 1)
    dados19 = (tmp_path / "guardado.bin").read_bytes()
    s = Roteador([2018, 2019, 2020], {2019: [resp_ok(dados19)], 2020: [drive_de(z20)]})
    ex = run(conn, s, tmp_path)
    assert (s.n(2018), s.n(2019), s.n(2020)) == (0, 1, 1)  # 2020: só a sonda
    assert por_ano(ex)[2019].origem == "download" and por_ano(ex)[2019].status == "ok"
    assert (tmp_path / "acidentes2019_todas_causas_tipos.zip").exists()
    assert linhas(conn, 2019) == 2


def test_ac12_com_todos_os_zips_nao_baixa_anos_fechados(conn, tmp_path):
    for a in (2018, 2019):
        zip_de(tmp_path, a, 1)
    z20 = zip_de(tmp_path, 2020, 1)
    s = Roteador([2018, 2019, 2020], {2020: [drive_de(z20)]})
    run(conn, s, tmp_path)
    assert (s.n(2018), s.n(2019), s.n(2020)) == (0, 0, 1)


def test_segunda_execucao_pula_tudo_com_uma_sonda(conn, tmp_path):
    for a in (2018, 2019):
        zip_de(tmp_path, a, 1)
    z20 = zip_de(tmp_path, 2020, 1)
    run(conn, Roteador([2018, 2019, 2020], {2020: [drive_de(z20)]}), tmp_path)
    s = Roteador([2018, 2019, 2020], {2020: [drive_de(z20)]})
    ex = run(conn, s, tmp_path)
    assert {r.status for r in ex.resultados} == {"pulado"}
    assert (s.n(2018), s.n(2019), s.n(2020)) == (0, 0, 1)
    assert [r.linhas for r in ex.resultados] == [1, 1, 1]  # linhas do banco, mesmo pulado


def test_ano_fechado_repete_marca_e_nao_consulta_drive_ac39(conn, tmp_path):
    zip_de(tmp_path, 2019, 1)
    z20 = zip_de(tmp_path, 2020, 1)
    run(conn, Roteador([2019, 2020], {2020: [drive_de(z20)]}), tmp_path)
    conn.execute("UPDATE etl_log SET fechado = 1 WHERE ano = 2019")
    conn.commit()
    s = Roteador([2019, 2020], {2020: [drive_de(z20)]})
    run(conn, s, tmp_path)
    assert s.n(2019) == 0
    assert log(conn)[-2]["ano"] == 2019 and log(conn)[-2]["status"] == "pulado" and log(conn)[-2]["fechado"] == 1


def test_ano_anterior_recebe_a_ultima_verificacao_e_depois_nao_e_consultado(conn, tmp_path):
    z19 = zip_de(tmp_path, 2019, 1)
    run(conn, Roteador([2019], {2019: [drive_de(z19)]}), tmp_path)  # 2019 era o mais recente
    z20 = zip_de(tmp_path, 2020, 1)
    s = Roteador([2019, 2020], {2019: [drive_de(z19)], 2020: [drive_de(z20)]})
    ex = run(conn, s, tmp_path)
    assert (s.n(2019), s.n(2020)) == (1, 1)
    assert por_ano(ex)[2019].status == "pulado"
    assert db.esta_fechado(conn, 2019)
    s2 = Roteador([2019, 2020], {2020: [drive_de(z20)]})
    run(conn, s2, tmp_path)
    assert s2.n(2019) == 0


def test_falha_na_sonda_do_ano_anterior_nao_grava_fechado(conn, tmp_path):
    z19 = zip_de(tmp_path, 2019, 1)
    run(conn, Roteador([2019], {2019: [drive_de(z19)]}), tmp_path)
    z20 = zip_de(tmp_path, 2020, 1)
    s = Roteador([2019, 2020], {2019: [requests.ConnectionError("fora")], 2020: [drive_de(z20)]})
    ex = run(conn, s, tmp_path)
    assert por_ano(ex)[2019].status == "erro" and por_ano(ex)[2020].status == "ok"
    assert not db.esta_fechado(conn, 2019)


def test_force_vale_so_para_o_ano_mais_recente(conn, tmp_path):
    zip_de(tmp_path, 2019, 1)
    z20 = zip_de(tmp_path, 2020, 1)
    run(conn, Roteador([2019, 2020], {2020: [drive_de(z20)]}), tmp_path)
    s = Roteador([2019, 2020], {2020: [drive_de(z20), drive_de(z20)]})
    ex = run(conn, s, tmp_path, force=True)
    r = por_ano(ex)
    assert (r[2019].status, r[2020].status) == ("pulado", "ok")
    assert (s.n(2019), s.n(2020)) == (0, 2)


def test_excecao_inesperada_em_um_ano_e_isolada(conn, tmp_path, monkeypatch):
    zip_de(tmp_path, 2018, 1)
    zip_de(tmp_path, 2019, 1)
    z20 = zip_de(tmp_path, 2020, 1)
    original = db.carregar_ano

    def falha_2019(conn_, ano, *a, **kw):
        if ano == 2019:
            raise sqlite3.OperationalError("disco cheio")
        return original(conn_, ano, *a, **kw)

    monkeypatch.setattr(db, "carregar_ano", falha_2019)
    ex = run(conn, Roteador([2018, 2019, 2020], {2020: [drive_de(z20)]}), tmp_path)
    r = por_ano(ex)
    assert (r[2018].status, r[2019].status, r[2020].status) == ("ok", "erro", "ok")
    assert "disco cheio" in r[2019].mensagem
    assert [x["status"] for x in log(conn) if x["ano"] == 2019] == ["erro"]


def test_zip_com_dois_csvs_falha_so_esse_ano_ac19(conn, tmp_path):
    zip_de(tmp_path, 2018, 1)
    faz_zip(tmp_path, 2019, [linha()], nomes_csv=["a.csv", "b.csv"])
    z20 = zip_de(tmp_path, 2020, 1)
    ex = run(conn, Roteador([2018, 2019, 2020], {2020: [drive_de(z20)]}), tmp_path)
    r = por_ano(ex)
    assert (r[2018].status, r[2019].status, r[2020].status) == ("ok", "erro", "ok")
    assert "esperado 1 CSV, encontrado 2" in r[2019].mensagem


def test_zip_fora_do_padrao_vira_aviso_do_resumo(conn, tmp_path):
    (tmp_path / "outro.zip").write_bytes(b"x")
    z20 = zip_de(tmp_path, 2020, 1)
    ex = run(conn, Roteador([2020], {2020: [drive_de(z20)]}), tmp_path)
    assert any("outro.zip" in a for a in ex.avisos)
    assert "outro.zip" in formatar_resumo(ex)


def test_resumo_lista_ano_linhas_status_e_origem(conn, tmp_path):
    zip_de(tmp_path, 2018, 3)
    z20 = zip_de(tmp_path, 2020, 2)
    ex = run(conn, Roteador([2018, 2020], {2020: [drive_de(z20)]}), tmp_path)
    linhas_resumo = {l.split()[0]: l.split() for l in formatar_resumo(ex).splitlines() if l[:4].isdigit()}
    assert linhas_resumo["2018"][:4] == ["2018", "ok", "local", "3"]
    assert linhas_resumo["2020"][:4] == ["2020", "ok", "local", "2"]
    ex2 = run(conn, Roteador([2018, 2020], {2020: [drive_de(z20)]}), tmp_path)
    assert all(l.split()[1:3] == ["pulado", "pulado"] for l in formatar_resumo(ex2).splitlines() if l[:4].isdigit())


def test_resumo_e_log_nao_trazem_valores_das_linhas(conn, tmp_path):
    faz_zip(tmp_path, 2018, [linha(id=SENTINELA, municipio=SENTINELA)])
    z20 = zip_de(tmp_path, 2020, 1)
    ex = run(conn, Roteador([2018, 2020], {2020: [drive_de(z20)]}), tmp_path)
    assert por_ano(ex)[2018].status == "ok"
    assert "id" in por_ano(ex)[2018].mensagem  # contagem de falhas de conversão por coluna
    assert SENTINELA not in formatar_resumo(ex)
    assert SENTINELA not in repr(log(conn))
