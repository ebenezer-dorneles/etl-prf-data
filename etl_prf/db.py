import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from etl_prf.schema import NOMES_COLUNAS, criar_tabelas
from etl_prf.transform import transformar
from etl_prf.zipcsv import iterar_chunks

SQL_DELETE_ANO = "DELETE FROM acidentes WHERE ano = ?"
SQL_INSERT_ACIDENTE = (
    f"INSERT INTO acidentes ({', '.join(NOMES_COLUNAS)}, ano) "
    f"VALUES ({', '.join('?' * (len(NOMES_COLUNAS) + 1))})"
)
SQL_INSERT_LOG = (
    "INSERT INTO etl_log (ano, origem, status, linhas, tamanho, sha256, drive_content_length, "
    "drive_x_goog_hash, drive_last_modified, fechado, mensagem, timestamp) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
SQL_REFERENCIA = (
    "SELECT tamanho, sha256, drive_content_length, drive_x_goog_hash, drive_last_modified "
    "FROM etl_log WHERE ano = ? AND status IN ('ok', 'pulado') ORDER BY rowid DESC LIMIT 1"
)
SQL_FECHADO = "SELECT EXISTS (SELECT 1 FROM etl_log WHERE ano = ? AND status IN ('ok', 'pulado') AND fechado = 1)"

_BLOCO_SHA = 1024 * 1024


@dataclass(frozen=True)
class Impressao:
    tamanho: int
    sha256: str


@dataclass(frozen=True)
class Referencia:
    tamanho: int
    sha256: str
    drive_content_length: int | None
    drive_x_goog_hash: str | None
    drive_last_modified: str | None


def conectar(caminho: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(caminho, isolation_level=None)
    criar_tabelas(conn)
    return conn


def impressao(caminho: Path) -> Impressao:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        while bloco := f.read(_BLOCO_SHA):
            h.update(bloco)
    return Impressao(Path(caminho).stat().st_size, h.hexdigest())


def referencia(conn: sqlite3.Connection, ano: int) -> Referencia | None:
    """Linha `ok`/`pulado` mais recente do ano; `erro` nunca é referência (D-26)."""
    row = conn.execute(SQL_REFERENCIA, (ano,)).fetchone()
    return Referencia(*row) if row else None


def esta_fechado(conn: sqlite3.Connection, ano: int) -> bool:
    return bool(conn.execute(SQL_FECHADO, (ano,)).fetchone()[0])


def ano_inalterado(conn: sqlite3.Connection, ano: int, imp: Impressao) -> bool:
    ref = referencia(conn, ano)
    return ref is not None and (ref.tamanho, ref.sha256) == (imp.tamanho, imp.sha256)


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _drive(drive: dict | None) -> tuple:
    d = drive or {}
    return d.get("content_length"), d.get("x_goog_hash"), d.get("last_modified")


def _gravar_log(conn, ano, origem, status, linhas, tamanho, sha256, drive, fechado, mensagem) -> None:
    conn.execute(
        SQL_INSERT_LOG,
        (ano, origem, status, linhas, tamanho, sha256, *drive, int(fechado), mensagem, _agora()),
    )


def carregar_ano(
    conn: sqlite3.Connection, ano: int, caminho: Path, origem: str, drive: dict | None = None,
    fechar: bool = False, avisos: list[str] = (),
) -> int:
    """Apaga e reinsere o ano numa transação, junto da linha `ok` do log (FR-4, AC-8).

    Qualquer exceção desfaz tudo e é repassada; quem chama registra o `erro`.
    """
    imp = impressao(caminho)
    fechado = fechar or esta_fechado(conn, ano)
    linhas = 0
    falhas: dict[str, int] = {}
    conn.execute("BEGIN")
    try:
        conn.execute(SQL_DELETE_ANO, (ano,))
        for chunk in iterar_chunks(caminho):
            saida, f = transformar(chunk)
            for nome, n in f.items():
                falhas[nome] = falhas.get(nome, 0) + n
            conn.executemany(SQL_INSERT_ACIDENTE, [(*t, ano) for t in saida.itertuples(index=False, name=None)])
            linhas += len(saida)
        partes = list(avisos)
        if falhas:
            partes.append("falhas de conversão (NULL): " + ", ".join(f"{c}: {n}" for c, n in falhas.items()))
        mensagem = "; ".join(partes) or None
        _gravar_log(conn, ano, origem, "ok", linhas, imp.tamanho, imp.sha256, _drive(drive), fechado, mensagem)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return linhas


def registrar_pulado(
    conn: sqlite3.Connection, ano: int, origem: str, fechado: bool = False,
    drive: dict | None = None, mensagem: str | None = None,
) -> None:
    """Linha `pulado` repetindo tamanho e sha256 da referência (AC-7, D-26/27).

    Os cabeçalhos são os da referência, salvo `drive` (sondagem atual, AC-32).
    """
    ref = referencia(conn, ano)
    if ref is None:
        raise ValueError(f"ano {ano} sem referência para registrar pulado")
    cabecalhos = _drive(drive) if drive else (ref.drive_content_length, ref.drive_x_goog_hash, ref.drive_last_modified)
    marca = fechado or esta_fechado(conn, ano)
    _gravar_log(conn, ano, origem, "pulado", None, ref.tamanho, ref.sha256, cabecalhos, marca, mensagem)


def registrar_erro(conn: sqlite3.Connection, ano: int, origem: str, mensagem: str, drive: dict | None = None) -> None:
    _gravar_log(conn, ano, origem, "erro", None, None, None, _drive(drive), False, mensagem)


def contar_linhas(conn: sqlite3.Connection, ano: int) -> int:
    return conn.execute("SELECT COUNT(*) FROM acidentes WHERE ano = ?", (ano,)).fetchone()[0]


def ultima_mensagem(conn: sqlite3.Connection, ano: int) -> str | None:
    """Mensagem da linha mais recente do ano (avisos e contagens de falhas; nunca valores, AC-6)."""
    row = conn.execute("SELECT mensagem FROM etl_log WHERE ano = ? ORDER BY rowid DESC LIMIT 1", (ano,)).fetchone()
    return row[0] if row else None
