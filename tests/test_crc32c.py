import io
from pathlib import Path

import pytest

from etl_prf.crc32c import crc32c, parse_goog_hash

RAIZ = Path(__file__).resolve().parent.parent
ZIP_2026 = RAIZ / "acidentes2026_todas_causas_tipos.zip"


def test_vetor_padrao():
    assert crc32c(b"123456789") == 0xE3069283


def test_vazio():
    assert crc32c(b"") == 0


def test_arquivo_aberto_igual_a_bytes():
    dados = bytes(range(256)) * 5000
    assert crc32c(io.BytesIO(dados)) == crc32c(dados)


def test_parse_crc32c_e_md5():
    assert parse_goog_hash("crc32c=zauaUg==,md5=abc") == 0xCDAB9A52


def test_parse_ordem_invertida_e_espacos():
    assert parse_goog_hash("md5=abc, crc32c=zauaUg==") == 0xCDAB9A52


def test_parse_sem_crc32c():
    assert parse_goog_hash("md5=abc") is None
    assert parse_goog_hash("") is None
    assert parse_goog_hash(None) is None


@pytest.mark.real
def test_crc32c_zip_2026_real():
    if not ZIP_2026.exists() or ZIP_2026.stat().st_size != 7_716_046:
        pytest.skip("ZIP 2026 ausente ou diferente do registrado em A-2")
    with ZIP_2026.open("rb") as f:
        assert crc32c(f) == 0xCDAB9A52
