"""E-2b: 1 GET; para os IDs do README, mostra o texto do contêiner do link (onde o ano aparece). Salva o HTML (amostra)."""
import re, requests, sys, os
from bs4 import BeautifulSoup
URL = "https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf"
README = os.path.join(os.path.dirname(__file__), *[".."] * 6, "README.md")
ids = re.findall(r"/file/d/([\w-]+)", open(README, encoding="utf-8").read())
r = requests.get(URL, timeout=30, headers={"User-Agent": "etl-prf-data-exploration/0.1 (leitura, 1 req)"})
open(os.path.join(os.path.dirname(__file__), "page.html"), "w", encoding="utf-8").write(r.text)
soup = BeautifulSoup(r.text, "lxml")
for i in ids:
    a = soup.select_one(f'a[href*="{i}"]')
    if not a: print(i, "NAO ENCONTRADO NA PAGINA"); continue
    p = a
    for _ in range(4):
        p = p.parent
        t = " ".join(p.get_text(" ").split())
        if re.search(r"20\d\d", t) and len(t) < 300: break
    print(i, "|", p.name, p.get("class"), "|", t[:160])
