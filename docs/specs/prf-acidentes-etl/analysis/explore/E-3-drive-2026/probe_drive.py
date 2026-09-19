"""E-3: 1 GET em stream no Drive (ID do 2026); le so cabecalhos e 4 primeiros bytes; nao baixa o corpo. Somente leitura."""
import os, requests
FID = "1EsGox0UnBWSaM6mrkNSUlYUOecubLCsh"  # README: Acidentes 2026
local = os.path.join(os.path.dirname(__file__), *[".."] * 6, "acidentes2026_todas_causas_tipos.zip")
r = requests.get("https://drive.google.com/uc", params={"export": "download", "id": FID}, stream=True, timeout=30,
                 headers={"User-Agent": "etl-prf-data-exploration/0.1 (leitura, 1 req)"})
print("redirects:", [(h.status_code, h.headers.get("location", "")[:80]) for h in r.history])
print("final:", r.status_code, r.url.split("?")[0])
for k in ("content-type", "content-length", "content-disposition", "last-modified", "etag", "x-goog-hash"):
    print(f"{k}: {r.headers.get(k)}")
head = next(r.iter_content(4), b"")
print("first_bytes:", head, "is_zip:", head[:2] == b"PK")
r.close()
print("local_zip_bytes:", os.path.getsize(local), "mtime:", os.path.getmtime(local))
