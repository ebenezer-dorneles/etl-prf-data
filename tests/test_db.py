import sqlite3

import pytest

import etl_prf.db as db
from etl_prf.errors import EtlError
from tests.conftest import faz_zip, linha

DRIVE = {"content_length": 7716046, "x_goog_hash": "crc32c=abc==,md5=def==", "last_modified": "Mon, 01 Jan 2026"}


@pytest.fixture
def conn(tmp_path):
    c = db.conectar(tmp_path / "prf.db")
    yield c
    c.close()


def contagens(conn):
    return dict(conn.execute("SELECT ano, COUNT(*) FROM acidentes GROUP BY ano ORDER BY ano"))


def log(conn):
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM etl_log ORDER BY rowid")]
    finally:
        conn.row_factory = None


def zip_ano(tmp_path, ano, n, sufixo=""):
    return faz_zip(tmp_path, ano, [linha(id=str(i), municipio=f"M{i}{sufixo}") for i in range(n)])


def test_carga_grava_linhas_e_etl_log_ok(conn, tmp_path):
    z = zip_ano(tmp_path, 2019, 3)
    db.carregar_ano(conn, 2019, z, origem="local")
    assert contagens(conn) == {2019: 3}
    (l,) = log(conn)
    assert (l["ano"], l["origem"], l["status"], l["linhas"], l["fechado"]) == (2019, "local", "ok", 3, 0)
    assert l["tamanho"] == z.stat().st_size and len(l["sha256"]) == 64 and l["timestamp"]


def test_falhas_de_conversao_vao_para_a_mensagem(conn, tmp_path):
    z = faz_zip(tmp_path, 2019, [linha(idade="abc"), linha(idade="x"), linha()])
    db.carregar_ano(conn, 2019, z, origem="local")
    assert conn.execute("SELECT COUNT(*) FROM acidentes WHERE idade IS NULL").fetchone()[0] == 2
    assert "idade: 2" in log(conn)[0]["mensagem"]


def test_cabecalhos_do_drive_sao_gravados(conn, tmp_path):
    db.carregar_ano(conn, 2026, zip_ano(tmp_path, 2026, 1), origem="download", drive=DRIVE)
    (l,) = log(conn)
    assert (l["drive_content_length"], l["drive_x_goog_hash"], l["drive_last_modified"]) == (
        DRIVE["content_length"], DRIVE["x_goog_hash"], DRIVE["last_modified"])


def test_recarga_do_mesmo_ano_nao_duplica(conn, tmp_path):
    z = zip_ano(tmp_path, 2019, 3)
    db.carregar_ano(conn, 2019, z, origem="local")
    db.carregar_ano(conn, 2019, z, origem="local")
    assert contagens(conn) == {2019: 3}


def test_ac7_pulado_repete_tamanho_sha_e_cabecalhos(conn, tmp_path):
    z = zip_ano(tmp_path, 2026, 2)
    db.carregar_ano(conn, 2026, z, origem="download", drive=DRIVE)
    ref = db.referencia(conn, 2026)
    assert db.ano_inalterado(conn, 2026, db.impressao(z))
    db.registrar_pulado(conn, 2026, "local")
    ok, pulado = log(conn)
    assert pulado["status"] == "pulado" and contagens(conn) == {2026: 2}
    for campo in ("tamanho", "sha256", "drive_content_length", "drive_x_goog_hash", "drive_last_modified"):
        assert pulado[campo] == ok[campo]
    assert ref.sha256 == ok["sha256"]


def test_ac8_falha_no_segundo_chunk_preserva_linhas_anteriores(conn, tmp_path, monkeypatch):
    db.carregar_ano(conn, 2019, zip_ano(tmp_path, 2019, 5), origem="local")
    nova = zip_ano(tmp_path, 2019, 250, "novo")
    orig = db.iterar_chunks

    def quebrado(caminho, chunksize=100_000):
        for i, chunk in enumerate(orig(caminho, chunksize=100)):
            if i == 1:
                raise RuntimeError("falha injetada")
            yield chunk

    monkeypatch.setattr(db, "iterar_chunks", quebrado)
    with pytest.raises(RuntimeError):
        db.carregar_ano(conn, 2019, nova, origem="local")
    assert contagens(conn) == {2019: 5}
    assert conn.execute("SELECT COUNT(*) FROM acidentes WHERE municipio LIKE '%novo'").fetchone()[0] == 0
    assert [l["status"] for l in log(conn)] == ["ok"]


def test_erro_de_cabecalho_do_zip_nao_apaga_o_ano(conn, tmp_path):
    db.carregar_ano(conn, 2019, zip_ano(tmp_path, 2019, 4), origem="local")
    ruim = faz_zip(tmp_path, 2019, [linha()], nomes_csv=[])
    with pytest.raises(EtlError):
        db.carregar_ano(conn, 2019, ruim, origem="local")
    assert contagens(conn) == {2019: 4}


def test_registrar_erro_nao_vira_referencia(conn, tmp_path):
    z = zip_ano(tmp_path, 2026, 2)
    db.carregar_ano(conn, 2026, z, origem="download", drive=DRIVE)
    db.registrar_erro(conn, 2026, "download", "rede caiu", drive={"content_length": 1, "x_goog_hash": "x", "last_modified": "y"})
    ref = db.referencia(conn, 2026)
    assert ref.drive_content_length == DRIVE["content_length"] and ref.drive_x_goog_hash == DRIVE["x_goog_hash"]
    ult = log(conn)[-1]
    assert ult["status"] == "erro" and ult["mensagem"] == "rede caiu" and ult["linhas"] is None
    assert db.referencia(conn, 2019) is None


def test_ac24_zip_com_sha_diferente_recarrega_so_esse_ano(conn, tmp_path):
    zips = {a: zip_ano(tmp_path, a, 2) for a in (2018, 2019)}
    for a, z in zips.items():
        db.carregar_ano(conn, a, z, origem="local")
    zips[2019] = zip_ano(tmp_path, 2019, 5, "v2")
    for a, z in zips.items():
        if db.ano_inalterado(conn, a, db.impressao(z)):
            db.registrar_pulado(conn, a, "local")
        else:
            db.carregar_ano(conn, a, z, origem="local")
    assert contagens(conn) == {2018: 2, 2019: 5}
    assert [(l["ano"], l["status"]) for l in log(conn)] == [
        (2018, "ok"), (2019, "ok"), (2018, "pulado"), (2019, "ok")]


def test_referencia_e_a_mais_recente_ok_ou_pulado(conn, tmp_path):
    z = zip_ano(tmp_path, 2026, 2)
    db.carregar_ano(conn, 2026, z, origem="local")
    db.registrar_pulado(conn, 2026, "local")
    db.registrar_erro(conn, 2026, "local", "boom")
    assert db.referencia(conn, 2026).sha256 == db.impressao(z).sha256
    assert not db.ano_inalterado(conn, 2026, db.Impressao(tamanho=1, sha256="0" * 64))


def test_fechado_e_repetido_em_pulado_ac39(conn, tmp_path):
    z = zip_ano(tmp_path, 2026, 2)
    db.carregar_ano(conn, 2026, z, origem="local")
    assert not db.esta_fechado(conn, 2026)
    db.registrar_pulado(conn, 2026, "local", fechado=True)
    assert db.esta_fechado(conn, 2026)
    db.registrar_pulado(conn, 2026, "local")
    assert [l["fechado"] for l in log(conn)] == [0, 1, 1]
    db.carregar_ano(conn, 2026, z, origem="local")
    assert log(conn)[-1]["fechado"] == 1
    assert not db.esta_fechado(conn, 2019)


def test_fechado_ignora_linha_de_erro(conn, tmp_path):
    db.registrar_erro(conn, 2026, "local", "boom")
    assert not db.esta_fechado(conn, 2026)
