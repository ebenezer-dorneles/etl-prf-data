"""E-3b: 1 GET completo (~7,7 MB) do ZIP 2026 no Drive, gravado FORA do projeto; compara SHA-256 com o ZIP local. Somente leitura."""
import hashlib, os, sys, requests, zipfile
FID = "1EsGox0UnBWSaM6mrkNSUlYUOecubLCsh"
out = sys.argv[1]
local = os.path.join(os.path.dirname(__file__), *[".."] * 6, "acidentes2026_todas_causas_tipos.zip")
r = requests.get("https://drive.google.com/uc", params={"export": "download", "id": FID}, timeout=60,
                 headers={"User-Agent": "etl-prf-data-exploration/0.1 (leitura, 1 req)"})
open(out, "wb").write(r.content)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
print("status", r.status_code, "bytes", len(r.content), "is_zipfile", zipfile.is_zipfile(out))
print("sha256 remoto", sha(out)); print("sha256 local ", sha(local)); print("identicos:", sha(out) == sha(local))
