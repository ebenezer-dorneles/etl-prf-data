"""Orquestração por ano. Aqui: o ano mais recente (FR-7); o isolamento e o resumo vêm na Phase 7."""

from dataclasses import dataclass, field
from pathlib import Path

from . import db
from .crc32c import parse_goog_hash
from .drive import AVISO_SEM_CRC, Validacao, download_validated, probe_headers
from .errors import EtlError


@dataclass(frozen=True)
class Acao:
    tipo: str  # "pular" | "carregar_local" | "baixar"
    aviso: str | None = None


@dataclass
class Resultado:
    ano: int
    status: str  # "ok" | "pulado" | "erro" | "fechado" (sem consulta nem gravação)
    mensagem: str | None = None
    avisos: list[str] = field(default_factory=list)


def nome_zip(ano: int) -> str:
    return f"acidentes{ano}_todas_causas_tipos.zip"


def decidir_acao(ref: db.Referencia | None, cab: Validacao, tamanho_local: int | None, force: bool) -> Acao:
    """Regra de mudança do FR-7 (D-19, D-24, D-29), sem I/O."""
    if force:
        return Acao("baixar")
    if ref is None:
        return Acao("carregar_local" if tamanho_local == cab.content_length else "baixar")
    anterior = ref.drive_content_length if ref.drive_content_length is not None else ref.tamanho
    novo_crc, antigo_crc = parse_goog_hash(cab.x_goog_hash), parse_goog_hash(ref.drive_x_goog_hash)
    aviso = AVISO_SEM_CRC if novo_crc is None else None
    mudou = cab.content_length != anterior or (novo_crc is not None and antigo_crc is not None and novo_crc != antigo_crc)
    return Acao("baixar" if mudou else "pular", aviso)


def _drive(v: Validacao) -> dict:
    return {"content_length": v.content_length, "x_goog_hash": v.x_goog_hash, "last_modified": v.last_modified}


def atualizar_ano(conn, session, ano: int, id_: str, pasta: Path, *, force: bool = False, fechar: bool = False) -> Resultado:
    """Sonda o Drive e carrega, pula ou baixa o ano; `fechar` faz a última verificação (D-22, D-27).

    Falhas de rede, de validação ou de leitura do ZIP viram `Resultado(status="erro")` e linha `erro`.
    """
    if fechar and db.esta_fechado(conn, ano):
        return Resultado(ano, "fechado")
    destino = Path(pasta) / nome_zip(ano)
    cab = None
    try:
        cab = probe_headers(session, id_, ano)
        local = destino.stat().st_size if destino.exists() else None
        acao = decidir_acao(db.referencia(conn, ano), cab, local, force)
        avisos = [acao.aviso] if acao.aviso else []
        if acao.tipo == "pular":
            db.registrar_pulado(conn, ano, "local", fechado=fechar, drive=_drive(cab), mensagem="; ".join(avisos) or None)
            return Resultado(ano, "pulado", avisos=avisos)
        origem = "local"
        if acao.tipo == "baixar":
            cab = download_validated(session, id_, destino, ano, force)
            avisos += cab.avisos
            origem = "drive"
        db.carregar_ano(conn, ano, destino, origem, _drive(cab), fechar=fechar, avisos=avisos)
        return Resultado(ano, "ok", avisos=avisos)
    except EtlError as e:
        db.registrar_erro(conn, ano, "drive", e.mensagem, _drive(cab) if cab else None)
        return Resultado(ano, "erro", e.mensagem)
