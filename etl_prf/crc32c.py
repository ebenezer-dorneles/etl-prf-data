"""CRC-32C (Castagnoli) em Python puro e leitura do cabeçalho x-goog-hash (D-25, D-28)."""

import base64
import binascii
from typing import BinaryIO

_POLINOMIO = 0x82F63B78
_BLOCO = 1024 * 1024


def _montar_tabela() -> tuple[int, ...]:
    tabela = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ _POLINOMIO if c & 1 else c >> 1
        tabela.append(c)
    return tuple(tabela)


_TABELA = _montar_tabela()


def _atualizar(crc: int, dados: bytes) -> int:
    tabela = _TABELA
    for b in dados:
        crc = tabela[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc


def crc32c(fonte: bytes | BinaryIO) -> int:
    """CRC-32C como inteiro de 32 bits; aceita bytes ou arquivo aberto em modo binário."""
    crc = 0xFFFFFFFF
    if isinstance(fonte, (bytes, bytearray, memoryview)):
        crc = _atualizar(crc, bytes(fonte))
    else:
        while bloco := fonte.read(_BLOCO):
            crc = _atualizar(crc, bloco)
    return crc ^ 0xFFFFFFFF


def parse_goog_hash(cabecalho: str | None) -> int | None:
    """Extrai o item `crc32c=` de `x-goog-hash` (base64, 4 bytes big-endian); None se ausente."""
    if not cabecalho:
        return None
    for item in cabecalho.split(","):
        nome, _, valor = item.strip().partition("=")
        if nome == "crc32c" and valor:
            try:
                bruto = base64.b64decode(valor, validate=True)
            except (binascii.Error, ValueError):
                return None
            return int.from_bytes(bruto, "big") if len(bruto) == 4 else None
    return None
