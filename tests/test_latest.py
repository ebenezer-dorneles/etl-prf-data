import sqlite3
from pathlib import Path

import pytest
import requests

from conftest import faz_zip, linha
from etl_prf import db
from etl_prf.drive import probe_headers
from etl_prf.errors import EtlError
from etl_prf.pipeline import Acao, atualizar_ano, decidir_acao
from test_drive import Resp, goog, resp_ok

ID = "1EsGox0UnBWSaM6mrkNSUlYUOecubLCsh"


class Sessao:
    """Sessão falsa: uma resposta (ou exceção) por chamada, na ordem; guarda as chamadas."""

    def __init__(self, *respostas) -> None:
        self.respostas, self.chamadas = list(respostas), []

    def get(self, url, **kw):
        self.chamadas.append((url, kw))
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def zip_de(pasta: Path, ano: int, n: int, sufixo: str = "") -> Path:
    return faz_zip(pasta, ano, [linha(id=str(i), municipio=f"M{i}{sufixo}") for i in range(n)])


def drive_de(caminho: Path, **cab) -> Resp:
    """Resposta do Drive para o ZIP `caminho`; `cab` sobrescreve cabeçalhos."""
    dados = caminho.read_bytes()
    r = resp_ok(dados)
    r.headers.update(cab)
    return r


@pytest.fixture
def conn(tmp_path):
    c = db.conectar(tmp_path / "t.sqlite")
    yield c
    c.close()


def log(conn):
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM etl_log ORDER BY rowid")]
    finally:
        conn.row_factory = None


def linhas(conn, ano=2026):
    return conn.execute("SELECT COUNT(*) FROM acidentes WHERE ano = ?", (ano,)).fetchone()[0]


def carga_inicial(conn, tmp_path, n=3):
    """2026 carregado com cabeçalhos do Drive iguais aos do ZIP local."""
    z = zip_de(tmp_path, 2026, n)
    r = drive_de(z)
    db.carregar_ano(
        conn, 2026, z, "drive",
        {"content_length": int(r.headers["content-length"]), "x_goog_hash": r.headers["x-goog-hash"],
         "last_modified": r.headers["last-modified"]},
    )
    return z


def rodar(conn, sessao, tmp_path, **kw):
    return atualizar_ano(conn, sessao, 2026, ID, tmp_path, **kw)


# --- probe_headers --------------------------------------------------------

def test_probe_le_so_cabecalhos_e_fecha_sem_ler_o_corpo(tmp_path):
    z = zip_de(tmp_path, 2026, 2)
    r = drive_de(z)
    lidos = []
    r.iter_content = lambda chunk_size=1: lidos.append(1) or iter(())
    s = Sessao(r)
    v = probe_headers(s, ID, 2026)
    assert (v.content_length, v.x_goog_hash) == (z.stat().st_size, goog(z.read_bytes()))
    assert v.last_modified == "Mon, 01 Jan 2026 00:00:00 GMT"
    assert r.fechada and lidos == []
    assert s.chamadas[0][1]["stream"] is True


def test_probe_falha_de_rede_ou_http_vira_etlerror():
    with pytest.raises(EtlError, match="sondagem falhou") as e:
        probe_headers(Sessao(requests.ConnectionError("fora")), ID, 2026)
    assert e.value.ano == 2026
    with pytest.raises(EtlError, match="sondagem falhou"):
        probe_headers(Sessao(Resp(b"", {}, status=500)), ID, 2026)


def test_probe_sem_content_length_falha():
    with pytest.raises(EtlError, match="content-length ausente"):
        probe_headers(Sessao(Resp(b"", {})), ID, 2026)


# --- decidir_acao (pura) --------------------------------------------------

def ref(cl=100, h="crc32c=AAAAAA==", lm="a", tamanho=100):
    return db.Referencia(tamanho, "x", cl, h, lm)


def cab(cl=100, h="crc32c=AAAAAA==", lm="a"):
    from etl_prf.drive import Validacao
    return Validacao(cl, h, lm)


def test_decidir_tabela():
    assert decidir_acao(ref(), cab(), None, force=False).tipo == "pular"
    assert decidir_acao(ref(), cab(cl=101), None, force=False).tipo == "baixar"
    assert decidir_acao(ref(), cab(h="crc32c=BBBBBB=="), None, force=False).tipo == "baixar"
    assert decidir_acao(ref(), cab(lm="b"), None, force=False).tipo == "pular"
    assert decidir_acao(ref(), cab(), None, force=True).tipo == "baixar"
    assert decidir_acao(None, cab(cl=100), 100, force=False).tipo == "carregar_local"
    assert decidir_acao(None, cab(cl=100), 99, force=False).tipo == "baixar"
    assert decidir_acao(None, cab(cl=100), None, force=False).tipo == "baixar"
    assert decidir_acao(None, cab(cl=100), 100, force=True).tipo == "baixar"


def test_decidir_sem_crc_compara_so_tamanho_com_aviso():
    a = decidir_acao(ref(), cab(h="md5=abc"), None, force=False)
    assert a.tipo == "pular" and "crc32c ausente" in a.aviso
    assert decidir_acao(ref(), cab(cl=7, h="md5=abc"), None, force=False).tipo == "baixar"


# --- AC-13 / NFR-3 --------------------------------------------------------

def test_ac13_cabecalhos_iguais_nao_baixa_e_nfr3_uma_requisicao(conn, tmp_path):
    z = carga_inicial(conn, tmp_path)
    antes = conn.execute("SELECT * FROM acidentes ORDER BY id").fetchall()
    s = Sessao(drive_de(z))
    res = rodar(conn, s, tmp_path)
    assert res.status == "pulado" and len(s.chamadas) == 1
    assert conn.execute("SELECT * FROM acidentes ORDER BY id").fetchall() == antes
    assert [l["status"] for l in log(conn)] == ["ok", "pulado"]


# --- AC-14 / AC-15 --------------------------------------------------------

def zip_remoto(tmp_path, n, sufixo="novo"):
    """ZIP que só existe no Drive (pasta à parte), com `n` linhas."""
    pasta = tmp_path / "remoto"
    pasta.mkdir(exist_ok=True)
    return zip_de(pasta, 2026, n, sufixo)


def test_ac14_hash_diferente_recarrega_e_registra_novos_cabecalhos(conn, tmp_path):
    carga_inicial(conn, tmp_path, 3)
    zn = zip_remoto(tmp_path, 5)
    s = Sessao(drive_de(zn), drive_de(zn))
    res = rodar(conn, s, tmp_path)
    assert res.status == "ok" and len(s.chamadas) == 2
    assert linhas(conn) == 5
    ultimo = log(conn)[-1]
    assert ultimo["status"] == "ok" and ultimo["drive_x_goog_hash"] == goog(zn.read_bytes())


def test_ac14_so_o_crc_diferente_dispara_download_e_validacao_barra_corpo_incoerente(conn, tmp_path):
    z = carga_inicial(conn, tmp_path, 3)
    outro = goog(b"outro conteudo")
    s = Sessao(drive_de(z, **{"x-goog-hash": outro}), drive_de(z, **{"x-goog-hash": outro}))
    res = rodar(conn, s, tmp_path)
    assert res.status == "erro" and "checksum divergente" in res.mensagem  # o corpo não bate com o hash anunciado
    assert linhas(conn) == 3


def test_ac15_force_recarrega_com_cabecalhos_iguais(conn, tmp_path):
    z = carga_inicial(conn, tmp_path)
    s = Sessao(drive_de(z), drive_de(z))
    res = rodar(conn, s, tmp_path, force=True)
    assert res.status == "ok" and len(s.chamadas) == 2
    assert [l["status"] for l in log(conn)] == ["ok", "ok"]


# --- AC-30 ----------------------------------------------------------------

def test_ac30_sem_ok_e_tamanho_igual_carrega_o_local_sem_baixar(conn, tmp_path):
    z = zip_de(tmp_path, 2026, 4)
    s = Sessao(drive_de(z))
    res = rodar(conn, s, tmp_path)
    assert res.status == "ok" and len(s.chamadas) == 1
    assert linhas(conn) == 4
    ultimo = log(conn)[-1]
    assert ultimo["origem"] == "local" and ultimo["drive_content_length"] == z.stat().st_size


def test_ac30_tamanho_diferente_baixa_e_carrega_o_do_drive(conn, tmp_path):
    zip_de(tmp_path, 2026, 4)
    remoto = tmp_path / "remoto"
    remoto.mkdir()
    zr = zip_de(remoto, 2026, 6, "drive")
    s = Sessao(drive_de(zr), drive_de(zr))
    res = rodar(conn, s, tmp_path)
    assert res.status == "ok" and len(s.chamadas) == 2
    assert linhas(conn) == 6 and log(conn)[-1]["origem"] == "drive"
    assert (tmp_path / "acidentes2026_todas_causas_tipos.zip").read_bytes() == zr.read_bytes()


# --- AC-31 ----------------------------------------------------------------

def test_ac31_referencia_ignora_erro_e_tenta_recarregar(conn, tmp_path):
    z = carga_inicial(conn, tmp_path, 3)
    zr = zip_remoto(tmp_path, 7)
    # 1ª execução: Drive mudou, download falha (linha `erro` com os cabeçalhos novos)
    falha = drive_de(zr)
    falha.corpo = falha.corpo[:-10]
    assert rodar(conn, Sessao(drive_de(zr), falha), tmp_path).status == "erro"
    assert log(conn)[-1]["drive_content_length"] == zr.stat().st_size
    # 2ª execução: compara com a linha `ok` (não com a `erro`), vê a mudança e recarrega
    s = Sessao(drive_de(zr), drive_de(zr))
    assert rodar(conn, s, tmp_path).status == "ok"
    assert linhas(conn) == 7 and len(s.chamadas) == 2


# --- AC-32 ----------------------------------------------------------------

def test_ac32_so_last_modified_diferente_nao_baixa_e_registra_o_novo(conn, tmp_path):
    z = carga_inicial(conn, tmp_path)
    s = Sessao(drive_de(z, **{"last-modified": "Tue, 02 Feb 2027 00:00:00 GMT"}))
    res = rodar(conn, s, tmp_path)
    assert res.status == "pulado" and len(s.chamadas) == 1
    assert log(conn)[-1]["drive_last_modified"] == "Tue, 02 Feb 2027 00:00:00 GMT"


# --- AC-33 / AC-39 / AC-37 ------------------------------------------------

def test_ac33_fechar_grava_fechado_e_depois_nao_consulta(conn, tmp_path):
    z = carga_inicial(conn, tmp_path)
    s = Sessao(drive_de(z))
    res = rodar(conn, s, tmp_path, fechar=True)
    assert res.status == "pulado" and log(conn)[-1]["fechado"] == 1
    assert db.esta_fechado(conn, 2026)
    s2 = Sessao()
    res2 = rodar(conn, s2, tmp_path, fechar=True)
    assert s2.chamadas == [] and res2.status == "fechado"


def test_ac33_fechar_com_cabecalhos_mudados_recarrega_e_marca_fechado(conn, tmp_path):
    carga_inicial(conn, tmp_path, 3)
    remoto = tmp_path / "remoto"
    remoto.mkdir()
    zr = zip_de(remoto, 2026, 9, "r")
    s = Sessao(drive_de(zr), drive_de(zr))
    res = rodar(conn, s, tmp_path, fechar=True)
    assert res.status == "ok" and linhas(conn) == 9
    assert log(conn)[-1]["fechado"] == 1


def test_ac39_pulado_de_ano_fechado_repete_a_marca(conn, tmp_path):
    z = carga_inicial(conn, tmp_path)
    rodar(conn, Sessao(drive_de(z)), tmp_path, fechar=True)
    db.registrar_pulado(conn, 2026, "local")
    assert [l["fechado"] for l in log(conn)] == [0, 1, 1]
    assert db.esta_fechado(conn, 2026)


def test_ac37_falha_de_rede_na_sonda_nao_grava_fechado_e_repete(conn, tmp_path):
    z = carga_inicial(conn, tmp_path)
    res = rodar(conn, Sessao(requests.ConnectionError("fora")), tmp_path, fechar=True)
    assert res.status == "erro" and "sondagem falhou" in res.mensagem
    assert not db.esta_fechado(conn, 2026)
    assert log(conn)[-1]["status"] == "erro" and log(conn)[-1]["fechado"] == 0
    s = Sessao(drive_de(z))
    rodar(conn, s, tmp_path, fechar=True)
    assert len(s.chamadas) == 1 and db.esta_fechado(conn, 2026)


# --- AC-41 ----------------------------------------------------------------

def test_ac41_sem_crc_e_tamanho_igual_nao_baixa_e_avisa(conn, tmp_path):
    z = carga_inicial(conn, tmp_path)
    s = Sessao(drive_de(z, **{"x-goog-hash": "md5=abc"}))
    res = rodar(conn, s, tmp_path)
    assert res.status == "pulado" and len(s.chamadas) == 1
    assert any("crc32c ausente" in a for a in res.avisos)
    assert "crc32c ausente" in log(conn)[-1]["mensagem"]


def test_ac41_sem_crc_e_tamanho_diferente_falha_sem_tocar_zip_nem_linhas(conn, tmp_path):
    z = carga_inicial(conn, tmp_path)
    original = z.read_bytes()
    zr = zip_remoto(tmp_path, 8)
    sem_crc = {"x-goog-hash": "md5=abc"}
    s = Sessao(drive_de(zr, **sem_crc), drive_de(zr, **sem_crc))
    res = rodar(conn, s, tmp_path)
    assert res.status == "erro" and "x-goog-hash sem crc32c" in res.mensagem
    assert z.read_bytes() == original and linhas(conn) == 3
    assert log(conn)[-1]["status"] == "erro"
