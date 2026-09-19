import re
from decimal import Decimal, InvalidOperation

import numpy as np
import pandas as pd

from etl_prf.schema import COLUNAS, DATA, INTEIRO, REAL

MARCADORES_NULO = ("NA", "N/A", "")

_INTEIRO_SIMPLES = re.compile(r"-?\d{1,18}")


def _inteiro_exato(texto: str) -> int | None:
    """Notação científica ou decimal (`1e+05`, `19.0`) -> inteiro exato, senão None."""
    try:
        d = Decimal(texto)
    except InvalidOperation:
        return None
    if not d.is_finite() or d != d.to_integral_value():
        return None
    return int(d)


def _converter_inteiro(serie: pd.Series) -> pd.Series:
    simples = serie.str.fullmatch(_INTEIRO_SIMPLES).fillna(False).astype(bool)
    saida = pd.Series([None] * len(serie), index=serie.index, dtype=object)
    saida[simples] = serie[simples].astype("int64").astype(object)
    resto = ~simples & serie.notna()
    for i in serie.index[resto]:
        saida[i] = _inteiro_exato(serie[i])
    return saida


def _converter_real(serie: pd.Series) -> pd.Series:
    numeros = pd.to_numeric(serie.str.replace(",", ".", regex=False), errors="coerce")
    numeros = numeros.where(np.isfinite(numeros))
    return numeros.astype(object).where(numeros.notna(), None)


def _converter_data(serie: pd.Series) -> pd.Series:
    datas = pd.to_datetime(serie, format="%Y-%m-%d", errors="coerce")
    return datas.dt.strftime("%Y-%m-%d").astype(object).where(datas.notna(), None)


def transformar(chunk: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Chunk lido como texto -> tipos do schema (NULL como None) e falhas por coluna.

    Só contam como falha os valores que não são marcador de nulo e não convertem.
    """
    saida: dict[str, pd.Series] = {}
    falhas: dict[str, int] = {}
    for nome, tipo in COLUNAS:
        bruto = chunk[nome]
        serie = bruto.where(~bruto.isin(MARCADORES_NULO), None)
        if tipo == INTEIRO:
            convertida = _converter_inteiro(serie)
        elif tipo == REAL:
            convertida = _converter_real(serie)
        elif tipo == DATA:
            convertida = _converter_data(serie)
        else:
            convertida = serie.astype(object).where(serie.notna(), None)
        n = int((serie.notna() & convertida.isna()).sum())
        if n:
            falhas[nome] = n
        saida[nome] = convertida
    return pd.DataFrame(saida, columns=[n for n, _ in COLUNAS]), falhas
