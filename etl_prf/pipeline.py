"""Orquestração por ano: ano mais recente (FR-7), anos fechados, isolamento de falhas (FR-8) e resumo (NFR-2)."""

from dataclasses import dataclass, field
from pathlib import Path

from . import db
from .config import IDS_README
from .crawler import descobrir
from .crc32c import parse_goog_hash
from .drive import AVISO_SEM_CRC, Validacao, download_validated, probe_headers
from .errors import EtlError
from .zipcsv import listar_zips


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
    origem: str = "-"  # "local" | "download" | "pulado" (NFR-2)
    linhas: int | None = None


@dataclass
class Execucao:
    resultados: list[Resultado]
    avisos: list[str] = field(default_factory=list)

    @property
    def falhas(self) -> int:
        return sum(r.status == "erro" for r in self.resultados)


_ORIGEM = {"local": "local", "drive": "download"}


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
            return Resultado(ano, "pulado", avisos=avisos, origem="pulado")
        origem = "local"
        if acao.tipo == "baixar":
            cab = download_validated(session, id_, destino, ano, force)
            avisos += cab.avisos
            origem = "drive"
        n = db.carregar_ano(conn, ano, destino, origem, _drive(cab), fechar=fechar, avisos=avisos)
        return Resultado(ano, "ok", avisos=avisos, origem=_ORIGEM[origem], linhas=n)
    except EtlError as e:
        db.registrar_erro(conn, ano, "drive", e.mensagem, _drive(cab) if cab else None)
        return Resultado(ano, "erro", e.mensagem)


def _ano_fechado(conn, session, ano: int, id_: str, pasta: Path) -> Resultado:
    """Ano fechado: nunca consulta o Drive; só baixa se o ZIP faltar (FR-6, AC-11/12, AC-39)."""
    destino = Path(pasta) / nome_zip(ano)
    if not destino.exists():
        cab = download_validated(session, id_, destino, ano)
        n = db.carregar_ano(conn, ano, destino, "drive", _drive(cab), avisos=cab.avisos)
        return Resultado(ano, "ok", avisos=cab.avisos, origem="download", linhas=n)
    if db.ano_inalterado(conn, ano, db.impressao(destino)):
        db.registrar_pulado(conn, ano, "local")
        return Resultado(ano, "pulado", origem="pulado")
    return Resultado(ano, "ok", origem="local", linhas=db.carregar_ano(conn, ano, destino, "local"))


def _pendente_de_fechamento(conn, ano: int) -> bool:
    """O ano foi o mais recente (tem cabeçalhos do Drive na referência) e ainda não foi fechado (D-22)."""
    ref = db.referencia(conn, ano)
    return ref is not None and ref.drive_content_length is not None and not db.esta_fechado(conn, ano)


def _processar(conn, session, ano: int, id_: str, pasta: Path, recente: int, anterior: int | None, force: bool) -> Resultado:
    if ano == recente:
        return atualizar_ano(conn, session, ano, id_, pasta, force=force)
    if ano == anterior and _pendente_de_fechamento(conn, ano):
        return atualizar_ano(conn, session, ano, id_, pasta, fechar=True)
    return _ano_fechado(conn, session, ano, id_, pasta)


def _registrar_erro(conn, ano: int, mensagem: str) -> Resultado:
    try:
        db.registrar_erro(conn, ano, "local", mensagem)
    except Exception:  # noqa: BLE001 — o log não pode derrubar os outros anos
        pass
    return Resultado(ano, "erro", mensagem)


def run(conn, session, pasta: Path, *, force: bool = False, readme: dict[int, str] = IDS_README) -> Execucao:
    """Processa cada ano descoberto isoladamente; falha de um ano não interrompe os outros (FR-8)."""
    desc = descobrir(session, readme=readme)
    _, avisos_zip = listar_zips(pasta)
    anos = sorted(desc.ids)
    recente = anos[-1]
    anterior = anos[-2] if len(anos) > 1 else None
    resultados = []
    for ano in anos:
        try:
            r = _processar(conn, session, ano, desc.ids[ano], pasta, recente, anterior, force)
        except EtlError as e:
            r = _registrar_erro(conn, ano, e.mensagem)
        except Exception as e:  # noqa: BLE001 — OSError, sqlite3.Error, ZIP corrompido…
            r = _registrar_erro(conn, ano, f"{type(e).__name__}: {e}")
        if r.linhas is None and r.status in ("pulado", "fechado"):
            r.linhas = db.contar_linhas(conn, ano)
        if r.status != "fechado":
            r.mensagem = db.ultima_mensagem(conn, ano)  # já inclui os avisos gravados no log
        resultados.append(r)
    return Execucao(resultados, [*desc.avisos, *avisos_zip])


def formatar_resumo(ex: Execucao) -> str:
    """Resumo por ano (NFR-2): só contagens e mensagens, nunca valores de linhas."""
    linhas = [f"{'ano':<6}{'status':<9}{'origem':<10}{'linhas':>8}  mensagem"]
    for r in ex.resultados:
        n = "-" if r.linhas is None else str(r.linhas)
        linhas.append(f"{r.ano:<6}{r.status:<9}{r.origem:<10}{n:>8}  {r.mensagem or ''}".rstrip())
    linhas += [f"aviso: {a}" for a in ex.avisos]
    linhas.append(f"{len(ex.resultados)} anos, {ex.falhas} com erro")
    return "\n".join(linhas)
