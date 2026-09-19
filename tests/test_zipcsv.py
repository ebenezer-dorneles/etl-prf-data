import pytest

from etl_prf.errors import EtlError
from etl_prf.zipcsv import ano_do_nome, iterar_chunks, listar_zips
from tests.conftest import COLUNAS_CSV, faz_zip, linha


def _todas(caminho, **kw):
    return list(iterar_chunks(caminho, **kw))


def test_ac2_cp1252_preserva_acentos(tmp_path):
    z = faz_zip(tmp_path, 2017, [linha(municipio="SÃO JOSÉ", causa_acidente="Ação/Omissão ç")])
    (df,) = _todas(z)
    assert df["municipio"].iloc[0] == "SÃO JOSÉ"
    assert df["causa_acidente"].iloc[0] == "Ação/Omissão ç"


def test_le_tudo_como_texto_sem_perder_marcadores(tmp_path):
    z = faz_zip(tmp_path, 2017, [linha(br="NA", uf="", km="1,5")])
    (df,) = _todas(z)
    assert list(df.columns) == COLUNAS_CSV
    assert df["br"].iloc[0] == "NA"
    assert df["uf"].iloc[0] == ""
    assert df["km"].iloc[0] == "1,5"


def test_chunks_respeitam_o_tamanho_e_nao_descartam_linhas(tmp_path):
    z = faz_zip(tmp_path, 2017, [linha(id=str(i)) for i in range(5)])
    chunks = _todas(z, chunksize=2)
    assert [len(c) for c in chunks] == [2, 2, 1]


def test_nao_extrai_nada_para_o_disco(tmp_path):
    z = faz_zip(tmp_path, 2017, [linha()])
    _todas(z)
    assert [p.name for p in tmp_path.iterdir()] == [z.name]


def test_ac18_cabecalho_diferente_lista_colunas_divergentes(tmp_path):
    colunas = [c for c in COLUNAS_CSV if c != "uop"] + ["coluna_nova"]
    z = faz_zip(tmp_path, 2022, [linha(coluna_nova="x")], colunas=colunas)
    with pytest.raises(EtlError) as e:
        _todas(z)
    assert e.value.ano == 2022
    assert "uop" in e.value.mensagem and "coluna_nova" in e.value.mensagem


def test_ac18_ordem_diferente_tambem_falha(tmp_path):
    colunas = COLUNAS_CSV[1:] + COLUNAS_CSV[:1]
    z = faz_zip(tmp_path, 2022, [linha()], colunas=colunas)
    with pytest.raises(EtlError):
        _todas(z)


def test_ac18_falha_antes_de_entregar_qualquer_chunk(tmp_path):
    colunas = COLUNAS_CSV[:-1]
    z = faz_zip(tmp_path, 2022, [linha()], colunas=colunas)
    entregues = []
    with pytest.raises(EtlError):
        for c in iterar_chunks(z):
            entregues.append(c)
    assert entregues == []


@pytest.mark.parametrize("nomes,ano,n", [([], 2020, 0), (["a.csv", "b.csv"], 2021, 2)])
def test_ac19_zip_sem_csv_ou_com_dois(tmp_path, nomes, ano, n):
    z = faz_zip(tmp_path, ano, [linha()], nomes_csv=nomes)
    with pytest.raises(EtlError) as e:
        _todas(z)
    assert e.value.ano == ano
    assert e.value.mensagem == f"esperado 1 CSV, encontrado {n}"


def test_ano_do_nome():
    assert ano_do_nome("acidentes2019_todas_causas_tipos.zip") == 2019
    assert ano_do_nome("/x/y/acidentes2026_todas_causas_tipos.zip") == 2026
    assert ano_do_nome("dados.zip") is None
    assert ano_do_nome("acidentes2019_outro.zip") is None


def test_listar_zips_ignora_nome_fora_do_padrao_com_aviso(tmp_path):
    a = faz_zip(tmp_path, 2018, [linha()])
    faz_zip(tmp_path, 2019, [linha()], nome_zip="backup.zip")
    (tmp_path / "notas.txt").write_text("x")
    zips, avisos = listar_zips(tmp_path)
    assert zips == {2018: a}
    assert len(avisos) == 1 and "backup.zip" in avisos[0]
