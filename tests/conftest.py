import zipfile
from pathlib import Path

COLUNAS_CSV = [
    "id", "pesid", "data_inversa", "dia_semana", "horario", "uf", "br", "km",
    "municipio", "causa_principal", "causa_acidente", "ordem_tipo_acidente",
    "tipo_acidente", "classificacao_acidente", "fase_dia", "sentido_via",
    "condicao_metereologica", "tipo_pista", "tracado_via", "uso_solo",
    "id_veiculo", "tipo_veiculo", "marca", "ano_fabricacao_veiculo",
    "tipo_envolvido", "estado_fisico", "idade", "sexo", "ilesos",
    "feridos_leves", "feridos_graves", "mortos", "latitude", "longitude",
    "regional", "delegacia", "uop",
]

LINHA_BASE = {
    "id": "8", "pesid": "1", "data_inversa": "2017-01-01", "dia_semana": "domingo",
    "horario": "00:00:00", "uf": "PR", "br": "376", "km": "112",
    "municipio": "PARANAVAI", "causa_principal": "Sim",
    "causa_acidente": "Fenômenos da Natureza", "ordem_tipo_acidente": "1",
    "tipo_acidente": "Queda de ocupante de veículo",
    "classificacao_acidente": "Com Vítimas Feridas", "fase_dia": "Plena Noite",
    "sentido_via": "Crescente", "condicao_metereologica": "Chuva",
    "tipo_pista": "Simples", "tracado_via": "Reta", "uso_solo": "Não",
    "id_veiculo": "5", "tipo_veiculo": "Motocicleta", "marca": "HONDA/CG 150",
    "ano_fabricacao_veiculo": "2005", "tipo_envolvido": "Condutor",
    "estado_fisico": "Lesões Graves", "idade": "19", "sexo": "Masculino",
    "ilesos": "0", "feridos_leves": "0", "feridos_graves": "1", "mortos": "0",
    "latitude": "-23,09880731", "longitude": "-52,38789369",
    "regional": "SPRF-PR", "delegacia": "DEL07-PR", "uop": "UOP02-DEL09-PR",
}


def linha(**campos):
    return {**LINHA_BASE, **campos}


def csv_bytes(linhas, colunas=None):
    colunas = colunas or COLUNAS_CSV
    cab = ";".join(f'"{c}"' for c in colunas)
    corpo = [";".join(f'"{l[c]}"' for c in colunas) for l in linhas]
    return ("\n".join([cab, *corpo]) + "\n").encode("cp1252")


def faz_zip(pasta: Path, ano: int, linhas, colunas=None, nomes_csv=None, nome_zip=None):
    """ZIP sintético; `nomes_csv` lista os CSVs a gravar (padrão: um só)."""
    caminho = pasta / (nome_zip or f"acidentes{ano}_todas_causas_tipos.zip")
    nomes_csv = [f"acidentes{ano}_todas_causas_tipos.csv"] if nomes_csv is None else nomes_csv
    with zipfile.ZipFile(caminho, "w") as z:
        for n in nomes_csv:
            z.writestr(n, csv_bytes(linhas, colunas))
    return caminho
