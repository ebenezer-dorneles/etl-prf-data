import argparse
from pathlib import Path

import requests

from . import db
from .config import IDS_README
from .pipeline import formatar_resumo, run

RAIZ = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None, *, raiz: Path = RAIZ, session=None, readme: dict[int, str] = IDS_README) -> int:
    """Carrega os acidentes da PRF em `data/prf.sqlite`; saída ≠ 0 se algum ano falhou (FR-9, D-23)."""
    ap = argparse.ArgumentParser(prog="python -m etl_prf", description="ETL dos acidentes da PRF (dados abertos).")
    ap.add_argument("--force", action="store_true", help="recarrega o ano mais recente sem comparar e aceita download sem crc32c")
    args = ap.parse_args(argv)
    (raiz / "data").mkdir(exist_ok=True)
    conn = db.conectar(raiz / "data" / "prf.sqlite")
    try:
        ex = run(conn, session or requests.Session(), raiz, force=args.force, readme=readme)
    finally:
        conn.close()
    print(formatar_resumo(ex))
    return 1 if ex.falhas else 0
