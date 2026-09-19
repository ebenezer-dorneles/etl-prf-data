"""A-1: auditoria de dados (somente leitura, sem rede). Le os ZIPs locais em chunks.
Verifica: (a) parseabilidade das colunas numericas, (b) marcadores de nulo alem de NA/N/A, (c) ids repetidos entre anos,
(d) espacos/vazios, (e) efeito do na_values padrao do pandas."""
import zipfile, glob, re, collections, pandas as pd
NUL = {"NA", "N/A"}
INT = re.compile(r"-?\d+")
FLT = re.compile(r"-?\d+([.,]\d+)?")
numeric_int = ["id","pesid","id_veiculo","br","idade","ano_fabricacao_veiculo","ilesos","feridos_leves","feridos_graves","mortos","ordem_tipo_acidente"]
numeric_flt = ["km","latitude","longitude"]
years_ids = {}
for z in sorted(glob.glob("acidentes*_todas_causas_tipos.zip")):
    y = int(re.search(r"acidentes(\d{4})", z).group(1)); bad = collections.Counter(); ex = {}
    other_null = collections.Counter(); blank = collections.Counter(); pd_default = collections.Counter(); ids = set(); cols = None
    with zipfile.ZipFile(z) as zf:
        with zf.open(zf.namelist()[0]) as f:
            for ch in pd.read_csv(f, sep=";", encoding="cp1252", dtype=str, keep_default_na=False, chunksize=200000):
                cols = list(ch.columns); ids.update(ch["id"].unique())
                for c in ch.columns:
                    s = ch[c]
                    blank[c] += int((s.str.strip() == "").sum()) + int((s != s.str.strip()).sum())
                    other_null[c] += int(s.str.lower().isin({"null","(null)","nan","none","n/a-"}).sum())
                    pd_default[c] += int(s.isin({"","#N/A","N/A","NA","NULL","NaN","n/a","nan","null","None","<NA>","-nan","-NaN","#NA","1.#IND","1.#QNAN","#N/A N/A"}).sum()) - int(s.isin(NUL).sum())
                for c in numeric_int + numeric_flt:
                    if c not in ch: continue
                    s = ch[c][~ch[c].isin(NUL)]
                    pat = INT if c in numeric_int else FLT
                    m = ~s.str.fullmatch(pat)
                    if m.any():
                        bad[c] += int(m.sum()); ex.setdefault(c, s[m].iloc[0])
    years_ids[y] = ids
    print(y, "nao_parseavel:", dict(bad), "exemplos:", ex)
    print("  outros_nulos:", {k:v for k,v in other_null.items() if v}, "| brancos/espacos:", {k:v for k,v in blank.items() if v}, "| extra_do_pandas_default:", {k:v for k,v in pd_default.items() if v})
ys = sorted(years_ids); print("ids repetidos entre anos:")
for i,a in enumerate(ys):
    for b in ys[i+1:]:
        n = len(years_ids[a] & years_ids[b])
        if n: print(f"  {a} x {b}: {n}")
print("fim")
