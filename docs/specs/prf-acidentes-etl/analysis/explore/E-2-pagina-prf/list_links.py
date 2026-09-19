"""E-2: 1 GET na página de dados abertos da PRF; lista links do Drive e o ano do texto. Somente leitura."""
import re, requests
from bs4 import BeautifulSoup
URL = "https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf"
r = requests.get(URL, timeout=30, headers={"User-Agent": "etl-prf-data-exploration/0.1 (leitura, 1 req)"})
print("status", r.status_code, "content-type", r.headers.get("content-type"), "bytes", len(r.content))
soup = BeautifulSoup(r.text, "lxml")
for a in soup.select('a[href*="drive.google.com"]'):
    txt = " ".join(a.get_text().split())
    m = re.search(r"/file/d/([\w-]+)", a["href"])
    print(re.search(r"\b(20\d\d)\b", txt) and re.search(r"\b(20\d\d)\b", txt).group(1), "|", m and m.group(1), "|", txt[:90])
