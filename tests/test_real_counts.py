from pathlib import Path

import pytest

from etl_prf.transform import transformar
from etl_prf.zipcsv import iterar_chunks

RAIZ = Path(__file__).resolve().parent.parent

CONTAGENS = {
    2017: 342_497, 2018: 316_638, 2019: 324_192, 2020: 384_640, 2021: 436_523,
    2022: 507_204, 2023: 571_052, 2024: 603_215, 2025: 584_010, 2026: 353_107,
}

pytestmark = pytest.mark.real


@pytest.mark.parametrize("ano,esperado", sorted(CONTAGENS.items()))
def test_ac1_contagem_de_linhas_e_transformacao_sem_descarte(ano, esperado):
    zip_ = RAIZ / f"acidentes{ano}_todas_causas_tipos.zip"
    if not zip_.exists():
        pytest.skip(f"{zip_.name} ausente")
    total = 0
    for chunk in iterar_chunks(zip_):
        saida, _ = transformar(chunk)
        assert len(saida) == len(chunk)
        total += len(saida)
    if ano == 2026 and total != esperado:
        pytest.skip("ZIP 2026 mudou desde o E-1 (ano em andamento)")
    assert total == esperado
