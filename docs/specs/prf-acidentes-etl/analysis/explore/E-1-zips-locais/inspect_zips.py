"""E-1: inspeção somente leitura dos ZIPs locais (esquema, encoding, nulos, chaves)."""
import zipfile, io, glob, os, sys, collections
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 6))
KEY = ["id", "pesid", "id_veiculo", "causa_acidente", "ordem_tipo_acidente"]
NULLS = {"", "(null)", "NA", "NULL", "null", "nan", "N/A"}
ref = None
for z in sorted(glob.glob(os.path.join(ROOT, "acidentes*_todas_causas_tipos.zip"))):
    zf = zipfile.ZipFile(z)
    names = zf.namelist()
    info = zf.infolist()[0]
    raw = zf.read(info)
    enc = None
    for e in ("utf-8", "cp1252", "latin-1"):
        try:
            raw.decode(e); enc = e; break
        except UnicodeDecodeError:
            pass
    df = pd.read_csv(io.BytesIO(raw), sep=";", encoding=enc, dtype=str, keep_default_na=False)
    cols = list(df.columns)
    ref = ref or cols
    nulls = {c: int(df[c].isin(NULLS).sum()) for c in df.columns if df[c].isin(NULLS).any()}
    markers = collections.Counter(v for c in df.columns for v in df[c].unique() if v in NULLS - {""})
    dup_key = int(df.duplicated(KEY, keep=False).sum())
    dup_full = int(df.duplicated(keep=False).sum())
    dec = df["km"].str.contains(",").sum(), df["km"].str.contains(r"\.").sum()
    dts = df["data_inversa"].str.slice(0, 10).sample(3, random_state=1).tolist()
    print(f"== {os.path.basename(z)} files={names} csv_bytes={info.file_size} enc={enc}")
    print(f"   rows={len(df)} ids={df['id'].nunique()} cols={len(cols)} same_header_as_first={cols == ref}")
    print(f"   null_markers={dict(markers)} cols_with_nulls={len(nulls)}")
    print(f"   dup_by_key_rows={dup_key} dup_full_rows={dup_full} km_comma/dot={dec} sample_dates={dts}")
    br_bad = df.loc[~df["br"].str.fullmatch(r"\d+"), "br"].value_counts().head(5).to_dict()
    dates = pd.to_datetime(df["data_inversa"], errors="coerce")
    print(f"   uf={df['uf'].nunique()} br_nonnumeric={br_bad} date_min={dates.min().date()} date_max={dates.max().date()} date_unparsed={int(dates.isna().sum())}")
    print(f"   nulls_by_col={nulls}")
    print(f"   lat_comma={int(df['latitude'].str.contains(',').sum())} horario_sample={df['horario'].iloc[0]!r} idade_nonnum={int((~df['idade'].str.fullmatch(r'\\d+') & ~df['idade'].isin(NULLS)).sum())} ano_fab_nonnum={int((~df['ano_fabricacao_veiculo'].str.fullmatch(r'\\d+') & ~df['ano_fabricacao_veiculo'].isin(NULLS)).sum())}")
