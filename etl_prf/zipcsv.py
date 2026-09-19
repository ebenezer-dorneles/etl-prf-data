import csv
import io
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from etl_prf.errors import EtlError
from etl_prf.schema import NOMES_COLUNAS

ENCODING = "cp1252"
CHUNKSIZE = 100_000
_NOME_ZIP = re.compile(r"^acidentes(\d{4})_todas_causas_tipos\.zip$")


def ano_do_nome(caminho: str | Path) -> int | None:
    m = _NOME_ZIP.match(Path(caminho).name)
    return int(m.group(1)) if m else None


def listar_zips(pasta: Path) -> tuple[dict[int, Path], list[str]]:
    """ZIPs do padrão por ano; outros `.zip` são ignorados com aviso (D-21)."""
    zips: dict[int, Path] = {}
    avisos: list[str] = []
    for caminho in sorted(Path(pasta).glob("*.zip")):
        ano = ano_do_nome(caminho)
        if ano is None:
            avisos.append(f"{caminho.name}: nome fora do padrão acidentes<ano>_todas_causas_tipos.zip, ignorado")
        else:
            zips[ano] = caminho
    return zips, avisos


def _validar_cabecalho(ano: int | None, cabecalho: list[str]) -> None:
    if cabecalho == NOMES_COLUNAS:
        return
    faltando = [c for c in NOMES_COLUNAS if c not in cabecalho]
    sobrando = [c for c in cabecalho if c not in NOMES_COLUNAS]
    detalhe = f"faltando {faltando}, inesperadas {sobrando}"
    if not faltando and not sobrando:
        detalhe = "mesmas colunas em outra ordem"
    raise EtlError(ano, f"cabeçalho diferente dos 37 campos: {detalhe}")


def iterar_chunks(caminho: Path, chunksize: int = CHUNKSIZE) -> Iterator[pd.DataFrame]:
    """Chunks de texto do único CSV do ZIP, em stream, sem extrair (D-21, AC-18/19)."""
    ano = ano_do_nome(caminho)
    with zipfile.ZipFile(caminho) as z:
        csvs = [i for i in z.infolist() if not i.is_dir() and i.filename.lower().endswith(".csv")]
        if len(csvs) != 1:
            raise EtlError(ano, f"esperado 1 CSV, encontrado {len(csvs)}")
        with z.open(csvs[0]) as bruto:
            texto = io.TextIOWrapper(bruto, encoding=ENCODING, newline="")
            _validar_cabecalho(ano, next(csv.reader(texto, delimiter=";"), []))
        with z.open(csvs[0]) as bruto:
            leitor = pd.read_csv(
                bruto, sep=";", encoding=ENCODING, dtype=str,
                keep_default_na=False, chunksize=chunksize,
            )
            yield from leitor
