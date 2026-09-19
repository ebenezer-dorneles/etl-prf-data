from pathlib import Path

import pytest
import requests

from etl_prf.config import IDS_README
from etl_prf.crawler import descobrir, parse_pagina

HTML = (Path(__file__).parent / "fixtures" / "pagina_prf.html").read_text(encoding="utf-8")


def linha(ano: int, id_: str) -> str:
    return (
        f"<tr><td><p>Documento CSV de Acidentes {ano} (Agrupados por pessoa - Todas as causas "
        f"e tipos de acidentes)</p></td><td><p><a href=\"https://drive.google.com/file/d/{id_}"
        f"/view?usp=sharing/download\">Baixar planilha</a></p></td></tr>"
    )


def pagina(**trocas: str) -> str:
    """Página com os 10 anos do README; `a2019=None`-style: ano ausente via chave 'sem'."""
    linhas = []
    for ano, id_ in IDS_README.items():
        if str(ano) in trocas.get("sem", ""):
            continue
        linhas.append(linha(ano, trocas.get(f"a{ano}", id_)))
    return "<table>" + "".join(linhas) + "</table>"


class Resp:
    def __init__(self, status: int = 200, text: str = "") -> None:
        self.status_code, self.text = status, text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, resp: Resp | Exception) -> None:
        self.resp, self.chamadas = resp, []

    def get(self, url: str, **kw):
        self.chamadas.append(url)
        if isinstance(self.resp, Exception):
            raise self.resp
        return self.resp


def test_ac9_pagina_real_devolve_10_pares_iguais_ao_readme():
    ids, avisos = parse_pagina(HTML)
    assert ids == IDS_README
    assert avisos == []


def test_ac9_ignora_links_de_ruido():
    ids, _ = parse_pagina(HTML)
    assert sorted(ids) == list(range(2017, 2027))


def test_ac9_descobrir_sem_fallback():
    r = descobrir(FakeSession(Resp(text=HTML)))
    assert r.ids == IDS_README
    assert not r.fallback_usado and r.anos_fallback == [] and r.divergencias == []


@pytest.mark.parametrize("resp", [Resp(500), Resp(text=""), Resp(text="<html><a href='x'>oi</a></html>"),
                                  requests.ConnectionError("sem rede")])
def test_ac10_erro_ou_sem_links_usa_readme(resp):
    r = descobrir(FakeSession(resp))
    assert r.ids == IDS_README
    assert r.fallback_usado and r.anos_fallback == sorted(IDS_README)
    assert r.avisos


def test_ac27_ano_ausente_vem_do_readme():
    r = descobrir(FakeSession(Resp(text=pagina(sem="2019"))))
    assert r.ids == IDS_README
    assert r.anos_fallback == [2019]
    assert not r.fallback_usado


def test_ac28_id_divergente_da_pagina_vence():
    novo = "N" * 33
    r = descobrir(FakeSession(Resp(text=pagina(a2021=novo))))
    assert r.ids[2021] == novo
    assert r.divergencias == [2021]
    assert any("2021" in a for a in r.avisos)


@pytest.mark.parametrize("ruim", ["abc&def" + "x" * 20, "curto123"])
def test_ac29_id_invalido_descartado_com_aviso(ruim):
    r = descobrir(FakeSession(Resp(text=pagina(a2020=ruim))))
    assert r.ids[2020] == IDS_README[2020]
    assert r.anos_fallback == [2020]
    assert any("2020" in a for a in r.avisos)


def test_parse_pagina_id_invalido_nao_entra():
    ids, avisos = parse_pagina(pagina(a2020="curto"))
    assert 2020 not in ids and avisos


def test_descobrir_faz_uma_requisicao():
    s = FakeSession(Resp(text=HTML))
    descobrir(s)
    assert len(s.chamadas) == 1
