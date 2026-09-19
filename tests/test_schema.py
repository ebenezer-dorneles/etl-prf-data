import sqlite3

from etl_prf.schema import COLUNAS, criar_tabelas
from tests.conftest import COLUNAS_CSV


def _conn():
    conn = sqlite3.connect(":memory:")
    criar_tabelas(conn)
    return conn


def test_colunas_de_dados_sao_as_37_do_csv_na_ordem():
    assert [n for n, _ in COLUNAS] == COLUNAS_CSV
    assert len(COLUNAS) == 37


def test_ac3_table_info_tem_37_colunas_mais_ano():
    info = _conn().execute("PRAGMA table_info(acidentes)").fetchall()
    nomes = [r[1] for r in info]
    assert nomes[:37] == COLUNAS_CSV
    assert nomes[37:] == ["ano"]


def test_d15_tipos_das_colunas():
    tipos = {r[1]: r[2] for r in _conn().execute("PRAGMA table_info(acidentes)")}
    reais = {"km", "latitude", "longitude"}
    inteiros = {
        "id", "pesid", "id_veiculo", "br", "idade", "ano_fabricacao_veiculo",
        "ordem_tipo_acidente", "ilesos", "feridos_leves", "feridos_graves",
        "mortos", "ano",
    }
    for nome, tipo in tipos.items():
        esperado = "REAL" if nome in reais else "INTEGER" if nome in inteiros else "TEXT"
        assert tipo == esperado, nome


def test_ac23_indices_cobrem_ano_id_data_inversa():
    conn = _conn()
    cobertas = set()
    for _, nome, *_ in conn.execute("PRAGMA index_list(acidentes)").fetchall():
        cobertas.add(conn.execute(f"PRAGMA index_info({nome})").fetchone()[2])
    assert {"ano", "id", "data_inversa"} <= cobertas


def test_sem_chave_unica():
    conn = _conn()
    unicos = [r for r in conn.execute("PRAGMA index_list(acidentes)") if r[2] == 1]
    assert unicos == []


def test_criar_tabelas_e_idempotente():
    conn = _conn()
    criar_tabelas(conn)
