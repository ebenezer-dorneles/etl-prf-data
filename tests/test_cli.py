import sqlite3
import subprocess
import sys
from pathlib import Path

from conftest import faz_zip, linha
from etl_prf.cli import main
from test_drive import Resp
from test_latest import drive_de, zip_de
from test_pipeline import Roteador

RAIZ = Path(__file__).resolve().parent.parent


def tabelas(caminho):
    with sqlite3.connect(caminho) as c:
        return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def test_ac34_sem_data_cria_banco_e_tabelas(tmp_path, capsys):
    z20 = zip_de(tmp_path, 2020, 2)
    assert not (tmp_path / "data").exists()
    codigo = main([], raiz=tmp_path, readme={}, session=Roteador([2020], {2020: [drive_de(z20)]}))
    assert codigo == 0
    assert {"acidentes", "etl_log"} <= tabelas(tmp_path / "data" / "prf.sqlite")


def test_ac35_tudo_ok_sai_com_zero_e_imprime_resumo(tmp_path, capsys):
    zip_de(tmp_path, 2018, 3)
    z20 = zip_de(tmp_path, 2020, 2)
    codigo = main([], raiz=tmp_path, readme={}, session=Roteador([2018, 2020], {2020: [drive_de(z20)]}))
    saida = capsys.readouterr().out
    assert codigo == 0
    assert "2018" in saida and "2020" in saida and "ok" in saida and "local" in saida


def test_ac16_falha_em_um_ano_sai_com_codigo_diferente_de_zero(tmp_path, capsys):
    zip_de(tmp_path, 2018, 1)
    z20 = zip_de(tmp_path, 2020, 1)
    s = Roteador([2018, 2019, 2020], {2019: [Resp(b"", {}, 429)], 2020: [drive_de(z20)]})
    assert main([], raiz=tmp_path, readme={}, session=s) == 1
    saida = capsys.readouterr().out
    assert "erro" in saida and "429" in saida


def test_force_e_repassado_ao_ano_mais_recente(tmp_path):
    z20 = zip_de(tmp_path, 2020, 1)
    main([], raiz=tmp_path, readme={}, session=Roteador([2020], {2020: [drive_de(z20)]}))
    s = Roteador([2020], {2020: [drive_de(z20), drive_de(z20)]})
    assert main(["--force"], raiz=tmp_path, readme={}, session=s) == 0
    assert s.n(2020) == 2


def test_python_m_etl_prf_help():
    r = subprocess.run([sys.executable, "-m", "etl_prf", "--help"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0 and "--force" in r.stdout
