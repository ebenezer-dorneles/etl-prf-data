"""E-4: amostra (20k linhas) de 2023/2024/2025: formato de lat/long, km, idade, ano_fabricacao, id. Somente leitura."""
import zipfile, io, os, pandas as pd
ROOT = os.path.join(os.path.dirname(__file__), *[".."] * 6)
for y in (2023, 2024, 2025):
    zf = zipfile.ZipFile(os.path.join(ROOT, f"acidentes{y}_todas_causas_tipos.zip"))
    with zf.open(zf.namelist()[0]) as f:
        df = pd.read_csv(f, sep=";", encoding="cp1252", dtype=str, keep_default_na=False, nrows=20000)
    print(y, {c: df[c].iloc[[0, 5000, 15000]].tolist() for c in ("latitude", "longitude", "km", "idade", "ano_fabricacao_veiculo", "id", "data_inversa")})
    print("   lat sep: comma", int(df.latitude.str.contains(",").sum()), "dot", int(df.latitude.str.contains(r"\.", regex=True).sum()),
          "| idade com '.':", int(df.idade.str.contains(r"\.", regex=True).sum()), "| id com '.':", int(df.id.str.contains(r"\.", regex=True).sum()))
