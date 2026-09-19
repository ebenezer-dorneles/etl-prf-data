import base64
import io
import zipfile
from pathlib import Path

import pytest
import requests

from etl_prf.crc32c import crc32c
from etl_prf.drive import download_validated
from etl_prf.errors import EtlError

ID = "1DAJYKVfkTcPhQodSmHp9rsG1Q8XJW-m3"


def zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("dados.csv", "a;b\n1;2\n" * 50)
    return buf.getvalue()


def goog(dados: bytes) -> str:
    return "crc32c=" + base64.b64encode(crc32c(dados).to_bytes(4, "big")).decode() + ",md5=abc"


class Resp:
    def __init__(self, corpo: bytes, headers: dict[str, str], status: int = 200) -> None:
        self.corpo, self.headers, self.status_code = corpo, headers, status
        self.fechada = False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int = 1):
        for i in range(0, len(self.corpo), 100):
            yield self.corpo[i : i + 100]

    def close(self) -> None:
        self.fechada = True


class FakeSession:
    def __init__(self, resp: Resp | Exception) -> None:
        self.resp, self.chamadas = resp, []

    def get(self, url: str, **kw) -> Resp:
        self.chamadas.append((url, kw))
        if isinstance(self.resp, Exception):
            raise self.resp
        return self.resp


def resp_ok(dados: bytes, *, hash_: str | None = "auto", tamanho: int | None = None) -> Resp:
    headers = {"content-length": str(len(dados) if tamanho is None else tamanho), "last-modified": "Mon, 01 Jan 2026 00:00:00 GMT"}
    if hash_ == "auto":
        headers["x-goog-hash"] = goog(dados)
    elif hash_ is not None:
        headers["x-goog-hash"] = hash_
    return Resp(dados, headers)


def sobrou_part(pasta: Path) -> list[Path]:
    return list(pasta.glob("*.part"))


def test_download_valido_grava_zip_e_devolve_cabecalhos(tmp_path):
    dados = zip_bytes()
    destino = tmp_path / "2019.zip"
    v = download_validated(FakeSession(resp_ok(dados)), ID, destino, ano=2019)
    assert destino.read_bytes() == dados
    assert v.content_length == len(dados)
    assert v.x_goog_hash == goog(dados)
    assert v.last_modified == "Mon, 01 Jan 2026 00:00:00 GMT"
    assert v.avisos == []
    assert sobrou_part(tmp_path) == []


def test_download_usa_url_do_drive_com_o_id(tmp_path):
    dados = zip_bytes()
    s = FakeSession(resp_ok(dados))
    download_validated(s, ID, tmp_path / "2019.zip", ano=2019)
    url, kw = s.chamadas[0]
    assert url == f"https://drive.google.com/uc?export=download&id={ID}"
    assert kw["stream"] is True


def test_truncado_falha_por_tamanho_e_nao_cria_zip_ac25(tmp_path):
    dados = zip_bytes()
    destino = tmp_path / "2019.zip"
    with pytest.raises(EtlError, match="tamanho divergente") as e:
        download_validated(FakeSession(resp_ok(dados, tamanho=len(dados) + 10)), ID, destino, ano=2019)
    assert e.value.ano == 2019
    assert not destino.exists()
    assert sobrou_part(tmp_path) == []


def test_truncado_preserva_zip_anterior_ac25(tmp_path):
    destino = tmp_path / "2019.zip"
    destino.write_bytes(b"antigo")
    dados = zip_bytes()
    with pytest.raises(EtlError, match="tamanho divergente"):
        download_validated(FakeSession(resp_ok(dados, tamanho=len(dados) + 1)), ID, destino, ano=2019)
    assert destino.read_bytes() == b"antigo"


def test_crc32c_errado_falha_e_preserva_zip_anterior_ac26(tmp_path):
    destino = tmp_path / "2019.zip"
    destino.write_bytes(b"antigo")
    dados = zip_bytes()
    errado = "crc32c=" + base64.b64encode((crc32c(dados) ^ 1).to_bytes(4, "big")).decode()
    with pytest.raises(EtlError, match="checksum divergente"):
        download_validated(FakeSession(resp_ok(dados, hash_=errado)), ID, destino, ano=2019)
    assert destino.read_bytes() == b"antigo"
    assert sobrou_part(tmp_path) == []


def test_sem_crc32c_falha_com_dica_de_force_ac38(tmp_path):
    destino = tmp_path / "2019.zip"
    with pytest.raises(EtlError, match="x-goog-hash sem crc32c") as e:
        download_validated(FakeSession(resp_ok(zip_bytes(), hash_="md5=abc")), ID, destino, ano=2019)
    assert "--force" in e.value.mensagem
    assert not destino.exists()
    assert sobrou_part(tmp_path) == []


def test_sem_cabecalho_x_goog_hash_tambem_falha_ac38(tmp_path):
    with pytest.raises(EtlError, match="x-goog-hash sem crc32c"):
        download_validated(FakeSession(resp_ok(zip_bytes(), hash_=None)), ID, tmp_path / "2019.zip", ano=2019)


def test_force_aceita_sem_crc32c_e_avisa_ac40(tmp_path):
    dados = zip_bytes()
    destino = tmp_path / "2019.zip"
    v = download_validated(FakeSession(resp_ok(dados, hash_="md5=abc")), ID, destino, ano=2019, force=True)
    assert destino.read_bytes() == dados
    assert v.avisos == ["crc32c ausente, validado só por tamanho e formato"]


def test_force_com_tamanho_divergente_ainda_falha_ac40(tmp_path):
    dados = zip_bytes()
    destino = tmp_path / "2019.zip"
    with pytest.raises(EtlError, match="tamanho divergente"):
        download_validated(FakeSession(resp_ok(dados, hash_="md5=abc", tamanho=len(dados) + 1)), ID, destino, ano=2019, force=True)
    assert not destino.exists()


def test_force_nao_aceita_crc32c_errado(tmp_path):
    dados = zip_bytes()
    errado = "crc32c=" + base64.b64encode((crc32c(dados) ^ 1).to_bytes(4, "big")).decode()
    with pytest.raises(EtlError, match="checksum divergente"):
        download_validated(FakeSession(resp_ok(dados, hash_=errado)), ID, tmp_path / "2019.zip", ano=2019, force=True)


def test_html_no_lugar_de_zip_falha_ac17(tmp_path):
    html = b"<html><body>confirmar download</body></html>" * 5
    destino = tmp_path / "2019.zip"
    destino.write_bytes(b"antigo")
    with pytest.raises(EtlError, match="resposta não é ZIP"):
        download_validated(FakeSession(resp_ok(html)), ID, destino, ano=2019)
    assert destino.read_bytes() == b"antigo"
    assert sobrou_part(tmp_path) == []


def test_content_length_ausente_falha(tmp_path):
    dados = zip_bytes()
    r = resp_ok(dados)
    del r.headers["content-length"]
    with pytest.raises(EtlError, match="content-length ausente"):
        download_validated(FakeSession(r), ID, tmp_path / "2019.zip", ano=2019)


def test_erro_http_vira_etlerror_sem_part(tmp_path):
    r = Resp(b"", {}, status=429)
    with pytest.raises(EtlError, match="HTTP 429"):
        download_validated(FakeSession(r), ID, tmp_path / "2019.zip", ano=2019)
    assert sobrou_part(tmp_path) == []


def test_falha_de_rede_vira_etlerror(tmp_path):
    with pytest.raises(EtlError, match="download falhou"):
        download_validated(FakeSession(requests.ConnectionError("sem rede")), ID, tmp_path / "2019.zip", ano=2019)


def test_resposta_e_fechada(tmp_path):
    r = resp_ok(zip_bytes())
    download_validated(FakeSession(r), ID, tmp_path / "2019.zip", ano=2019)
    assert r.fechada
