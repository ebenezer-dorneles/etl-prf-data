"""Download validado do Drive: arquivo temporário, conferência e substituição atômica (D-17, D-28, D-29)."""

import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .config import URL_DOWNLOAD
from .crc32c import _atualizar, parse_goog_hash
from .errors import EtlError

AVISO_SEM_CRC = "crc32c ausente, validado só por tamanho e formato"
_TIMEOUT = 60
_BLOCO = 1024 * 1024


@dataclass
class Validacao:
    content_length: int
    x_goog_hash: str | None
    last_modified: str | None
    avisos: list[str] = field(default_factory=list)


def download_validated(session, id_: str, destino: Path, ano: int, force: bool = False) -> Validacao:
    """Baixa para `<destino>.part`, valida tamanho, formato ZIP e crc32c e só então `os.replace`.

    Qualquer falha levanta `EtlError` e apaga o `.part`; o ZIP anterior nunca é tocado.
    """
    destino = Path(destino)
    parcial = destino.with_name(destino.name + ".part")
    resp = None
    try:
        try:
            resp = session.get(URL_DOWNLOAD.format(id=id_), stream=True, timeout=_TIMEOUT)
            resp.raise_for_status()
            validacao, crc = _gravar(resp, parcial, ano)
        except requests.RequestException as e:
            raise EtlError(ano, f"download falhou: {e}") from e
        _validar(validacao, crc, parcial, ano, force)
        os.replace(parcial, destino)
        return validacao
    finally:
        if resp is not None:
            resp.close()
        parcial.unlink(missing_ok=True)


def _gravar(resp, parcial: Path, ano: int) -> tuple[Validacao, int]:
    cabecalhos = {k.lower(): v for k, v in resp.headers.items()}
    anunciado = cabecalhos.get("content-length")
    if anunciado is None or not anunciado.isdigit():
        raise EtlError(ano, "content-length ausente na resposta do Drive")
    crc, recebido = 0xFFFFFFFF, 0
    with open(parcial, "wb") as f:
        for bloco in resp.iter_content(chunk_size=_BLOCO):
            f.write(bloco)
            crc = _atualizar(crc, bloco)
            recebido += len(bloco)
    if recebido != int(anunciado):
        raise EtlError(ano, f"tamanho divergente: recebidos {recebido} bytes, anunciados {anunciado}")
    return Validacao(int(anunciado), cabecalhos.get("x-goog-hash"), cabecalhos.get("last-modified")), crc ^ 0xFFFFFFFF


def _validar(validacao: Validacao, crc: int, parcial: Path, ano: int, force: bool) -> None:
    if not zipfile.is_zipfile(parcial):
        raise EtlError(ano, "resposta não é ZIP")
    esperado = parse_goog_hash(validacao.x_goog_hash)
    if esperado is None:
        if not force:
            raise EtlError(ano, "x-goog-hash sem crc32c; use --force para aceitar validando só tamanho e formato")
        validacao.avisos.append(AVISO_SEM_CRC)
    elif esperado != crc:
        raise EtlError(ano, f"checksum divergente: calculado {crc:#010x}, anunciado {esperado:#010x}")
