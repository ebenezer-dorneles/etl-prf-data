import pandas as pd
import pytest

from etl_prf.schema import COLUNAS
from etl_prf.transform import transformar
from tests.conftest import COLUNAS_CSV, linha


def _uma(**campos):
    df = pd.DataFrame([linha(**campos)], columns=COLUNAS_CSV, dtype=str)
    saida, falhas = transformar(df)
    return saida.iloc[0].to_dict(), falhas


def test_saida_tem_as_37_colunas_na_ordem():
    saida, _ = transformar(pd.DataFrame([linha()], columns=COLUNAS_CSV, dtype=str))
    assert list(saida.columns) == [n for n, _ in COLUNAS]


def test_ac4_km_virgula_real_e_br_na_nulo():
    r, falhas = _uma(km="123,4", br="NA")
    assert r["km"] == 123.4 and isinstance(r["km"], float)
    assert r["br"] is None
    assert falhas == {}


@pytest.mark.parametrize("bruto", ["-9,123", "-9.123"])
def test_ac5_latitude_virgula_ou_ponto(bruto):
    r, _ = _uma(latitude=bruto, longitude=bruto)
    assert r["latitude"] == -9.123 and r["longitude"] == -9.123


def test_ac6_valor_que_nao_converte_vira_nulo_e_conta():
    r, falhas = _uma(idade="abc")
    assert r["idade"] is None
    assert falhas == {"idade": 1}


def test_ac6_contagem_por_coluna_soma_linhas():
    df = pd.DataFrame(
        [linha(idade="abc"), linha(idade="x"), linha(km="??")],
        columns=COLUNAS_CSV, dtype=str,
    )
    _, falhas = transformar(df)
    assert falhas == {"idade": 2, "km": 1}


def test_ac20_id_cientifico_vira_inteiro_exato():
    r, falhas = _uma(id="4e+05")
    assert r["id"] == 400000 and isinstance(r["id"], int)
    assert falhas == {}


def test_d13_cientifico_grande_sem_perda_de_precisao():
    r, _ = _uma(id="1.2345678901234567e+17")
    assert r["id"] == 123456789012345670


def test_ac21_id_nao_inteiro_exato_vira_nulo_e_conta():
    r, falhas = _uma(id="1.5e+00")
    assert r["id"] is None
    assert falhas == {"id": 1}


def test_inteiro_com_decimal_zero_e_aceito_mas_fracao_nao():
    r, falhas = _uma(idade="19.0", ilesos="1.5")
    assert r["idade"] == 19
    assert r["ilesos"] is None
    assert falhas == {"ilesos": 1}


def test_ac22_vazio_vira_nulo_e_NULL_literal_permanece():
    df = pd.DataFrame(
        [linha(tipo_acidente=""), linha(tipo_acidente="NULL")],
        columns=COLUNAS_CSV, dtype=str,
    )
    saida, falhas = transformar(df)
    assert saida["tipo_acidente"].iloc[0] is None
    assert saida["tipo_acidente"].iloc[1] == "NULL"
    assert falhas == {}


@pytest.mark.parametrize("marcador", ["NA", "N/A", ""])
def test_d14_marcadores_de_nulo_em_texto_inteiro_real_e_data(marcador):
    r, falhas = _uma(uf=marcador, br=marcador, km=marcador, data_inversa=marcador)
    assert r["uf"] is None and r["br"] is None
    assert r["km"] is None and r["data_inversa"] is None
    assert falhas == {}


@pytest.mark.parametrize("texto", ["nan", "null", "None", "n/a", "na"])
def test_d14_outros_textos_nao_viram_nulo(texto):
    r, _ = _uma(uf=texto)
    assert r["uf"] == texto


def test_data_inversa_iso_e_horario_texto():
    r, falhas = _uma(data_inversa="2017-04-03", horario="07:05:00")
    assert r["data_inversa"] == "2017-04-03"
    assert r["horario"] == "07:05:00"
    assert falhas == {}


def test_data_invalida_vira_nulo_e_conta():
    r, falhas = _uma(data_inversa="03/04/2017")
    assert r["data_inversa"] is None
    assert falhas == {"data_inversa": 1}


def test_real_nao_finito_conta_como_falha():
    r, falhas = _uma(km="inf")
    assert r["km"] is None and falhas == {"km": 1}


def test_acentos_preservados():
    r, _ = _uma(causa_acidente="Fenômenos da Natureza")
    assert r["causa_acidente"] == "Fenômenos da Natureza"


def test_chunk_vazio():
    saida, falhas = transformar(pd.DataFrame(columns=COLUNAS_CSV, dtype=str))
    assert len(saida) == 0 and falhas == {}
