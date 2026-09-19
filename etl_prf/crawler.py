import re
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from .config import IDS_README, URL_PAGINA

REGEX_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
REGEX_LINHA = re.compile(r"Documento CSV de Acidentes (\d{4}) \(Agrupados por pessoa - Todas as causas")
REGEX_LINK = re.compile(r"/file/d/([^/?#]+)")


@dataclass
class Descoberta:
    ids: dict[int, str]
    fallback_usado: bool = False
    anos_fallback: list[int] = field(default_factory=list)
    divergencias: list[int] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def parse_pagina(html: str) -> tuple[dict[int, str], list[str]]:
    """Extrai {ano: id} das linhas `Documento CSV de Acidentes <ano>`; descarta IDs inválidos (D-21)."""
    ids: dict[int, str] = {}
    avisos: list[str] = []
    for tr in BeautifulSoup(html, "html.parser").find_all("tr"):
        m = REGEX_LINHA.search(" ".join(tr.get_text(" ").split()))
        a = tr.find("a", href=REGEX_LINK)
        if not m or not a:
            continue
        ano, id_ = int(m.group(1)), REGEX_LINK.search(a["href"]).group(1)
        if not REGEX_ID.match(id_):
            avisos.append(f"{ano}: ID do Drive fora do padrão na página, descartado")
        elif ano in ids and ids[ano] != id_:
            avisos.append(f"{ano}: mais de um link na página, mantido o primeiro")
        else:
            ids.setdefault(ano, id_)
    return ids, avisos


def mesclar(pagina: dict[int, str], avisos: list[str], readme: dict[int, str]) -> Descoberta:
    """Link da página vence; anos ausentes vêm do README; divergências são registradas (D-18)."""
    d = Descoberta(ids={}, avisos=list(avisos))
    for ano in sorted(set(pagina) | set(readme)):
        if ano in pagina:
            d.ids[ano] = pagina[ano]
            if ano in readme and readme[ano] != pagina[ano]:
                d.divergencias.append(ano)
                d.avisos.append(f"{ano}: ID da página difere do README, usado o da página")
        else:
            d.ids[ano] = readme[ano]
            d.anos_fallback.append(ano)
    d.fallback_usado = not pagina
    if pagina and d.anos_fallback:
        d.avisos.append(f"anos preenchidos pelo README: {', '.join(map(str, d.anos_fallback))}")
    return d


def descobrir(session, url: str = URL_PAGINA, readme: dict[int, str] = IDS_README,
              timeout: float = 30) -> Descoberta:
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        pagina, avisos = parse_pagina(resp.text)
    except requests.RequestException as e:
        pagina, avisos = {}, [f"falha ao acessar a página da PRF: {e}"]
    if not pagina:
        avisos.append("nenhum link de acidentes na página; usados os IDs do README")
    return mesclar(pagina, avisos, readme)
