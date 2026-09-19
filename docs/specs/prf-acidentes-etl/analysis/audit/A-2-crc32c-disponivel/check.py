"""A-2: crc32c esta disponivel? Somente leitura, sem rede. Compara o crc32c (Python puro) do ZIP 2026 local com o x-goog-hash do E-3."""
import base64, time
for m in ("google_crc32c", "crc32c", "crcmod"):
    try: __import__(m); print(m, "instalado")
    except ImportError: print(m, "nao instalado")
import zlib; print("zlib.crc32c:", hasattr(zlib, "crc32c"))
T = []
for i in range(256):
    c = i
    for _ in range(8): c = (c >> 1) ^ 0x82F63B78 if c & 1 else c >> 1
    T.append(c)
def crc32c(d):
    c = 0xFFFFFFFF
    for b in d: c = T[(c ^ b) & 0xFF] ^ (c >> 8)
    return c ^ 0xFFFFFFFF
d = open("acidentes2026_todas_causas_tipos.zip", "rb").read(); t = time.time()
h = base64.b64encode(crc32c(d).to_bytes(4, "big")).decode()
print("bytes", len(d), "crc32c", h, "esperado (E-3) zauaUg==", "IGUAL" if h == "zauaUg==" else "DIFERENTE", f"{time.time()-t:.1f}s")
