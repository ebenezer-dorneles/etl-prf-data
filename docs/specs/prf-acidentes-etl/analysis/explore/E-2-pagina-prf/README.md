# E-2 — Página de dados abertos da PRF

- **Date:** 2026-09-19
- **Author:** LLM (Claude Sonnet 5)
- **Question:** A página ainda expõe os links do Drive de forma parseável? Como o ano é identificado?
- **Evidence tier:** scripted
- **Code at:** N/A (projeto sem VCS; sem código de ETL ainda)

## Environment

Externo (internet), somente leitura, poucas requisições, User-Agent identificável. Autorizado pelo usuário em 2026-09-19.

## Inputs

1 GET em https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf e IDs de `README.md`.

## Reproduce

```
cd docs/specs/prf-acidentes-etl/analysis/explore/E-2-pagina-prf
python3 list_links.py > output.txt
python3 context_of_known_ids.py > output_context.txt
```

Scripts: `list_links.py` — lista todos os `<a href*=drive.google.com>` e o texto do link. `context_of_known_ids.py` — para os 10 IDs do README, mostra o texto do contêiner; salva `page.html`.

## Expected output

`output.txt`: HTTP 200, ~466 KB, ~80 links do Drive, texto de link "Baixar planilha" sem ano. `output_context.txt`: os 10 IDs do README encontrados, cada um numa `<tr>` com "Documento CSV de Acidentes <ano> …".

## Conclusion

A página responde 200 e é HTML estático parseável. Todos os 10 IDs do README existem na página, mas o ano só aparece no texto da linha (`<tr>`), não no texto do link. A página tem muito mais links do Drive que os de acidentes (multas etc.). Sustenta F-7, F-8.

## Supersedes / caveats

Uma só captura da página em 2026-09-19; o HTML pode mudar. Em uma segunda captura no mesmo dia `page.html` não ficou byte a byte igual (diferença já na linha 2, provavelmente conteúdo dinâmico do portal), mas `output.txt` e `output_context.txt` foram idênticos. `page.html` (~466 KB) é amostra da página no momento.
