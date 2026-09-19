"""E-5: 1 GET em robots.txt do gov.br; avalia se a página de dados abertos da PRF é permitida. Somente leitura."""
import requests, urllib.robotparser as rp
U = "https://www.gov.br/robots.txt"; P = "https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf"
r = requests.get(U, timeout=30, headers={"User-Agent": "etl-prf-data-exploration/0.1 (leitura, 1 req)"})
print("status", r.status_code, "bytes", len(r.content))
print("linhas com 'prf':", [l for l in r.text.splitlines() if "prf" in l.lower()])
p = rp.RobotFileParser(); p.parse(r.text.splitlines())
print("can_fetch pagina PRF (UA generico *):", p.can_fetch("*", P))
print("can_fetch pagina PRF (UA etl-prf-data):", p.can_fetch("etl-prf-data", P))
