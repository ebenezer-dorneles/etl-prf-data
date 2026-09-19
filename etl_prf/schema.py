import sqlite3

INTEIRO, REAL, DATA, TEXTO = "inteiro", "real", "data", "texto"

COLUNAS: list[tuple[str, str]] = [
    ("id", INTEIRO), ("pesid", INTEIRO), ("data_inversa", DATA), ("dia_semana", TEXTO),
    ("horario", TEXTO), ("uf", TEXTO), ("br", INTEIRO), ("km", REAL),
    ("municipio", TEXTO), ("causa_principal", TEXTO), ("causa_acidente", TEXTO),
    ("ordem_tipo_acidente", INTEIRO), ("tipo_acidente", TEXTO),
    ("classificacao_acidente", TEXTO), ("fase_dia", TEXTO), ("sentido_via", TEXTO),
    ("condicao_metereologica", TEXTO), ("tipo_pista", TEXTO), ("tracado_via", TEXTO),
    ("uso_solo", TEXTO), ("id_veiculo", INTEIRO), ("tipo_veiculo", TEXTO),
    ("marca", TEXTO), ("ano_fabricacao_veiculo", INTEIRO), ("tipo_envolvido", TEXTO),
    ("estado_fisico", TEXTO), ("idade", INTEIRO), ("sexo", TEXTO), ("ilesos", INTEIRO),
    ("feridos_leves", INTEIRO), ("feridos_graves", INTEIRO), ("mortos", INTEIRO),
    ("latitude", REAL), ("longitude", REAL), ("regional", TEXTO), ("delegacia", TEXTO),
    ("uop", TEXTO),
]

NOMES_COLUNAS: list[str] = [nome for nome, _ in COLUNAS]

_TIPO_SQL = {INTEIRO: "INTEGER", REAL: "REAL", DATA: "TEXT", TEXTO: "TEXT"}

DDL_ACIDENTES = (
    "CREATE TABLE IF NOT EXISTS acidentes (\n"
    + ",\n".join(f"    {nome} {_TIPO_SQL[tipo]}" for nome, tipo in COLUNAS)
    + ",\n    ano INTEGER NOT NULL\n)"
)

DDL_ETL_LOG = """CREATE TABLE IF NOT EXISTS etl_log (
    ano INTEGER NOT NULL,
    origem TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok', 'pulado', 'erro')),
    linhas INTEGER,
    tamanho INTEGER,
    sha256 TEXT,
    drive_content_length INTEGER,
    drive_x_goog_hash TEXT,
    drive_last_modified TEXT,
    fechado INTEGER NOT NULL DEFAULT 0,
    mensagem TEXT,
    timestamp TEXT NOT NULL
)"""

DDL_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_acidentes_ano ON acidentes (ano)",
    "CREATE INDEX IF NOT EXISTS idx_acidentes_id ON acidentes (id)",
    "CREATE INDEX IF NOT EXISTS idx_acidentes_data_inversa ON acidentes (data_inversa)",
]


def criar_tabelas(conn: sqlite3.Connection) -> None:
    conn.execute(DDL_ACIDENTES)
    conn.execute(DDL_ETL_LOG)
    for ddl in DDL_INDICES:
        conn.execute(ddl)
    conn.commit()
