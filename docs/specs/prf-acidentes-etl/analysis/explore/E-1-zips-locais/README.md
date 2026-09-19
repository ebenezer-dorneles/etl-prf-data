# E-1 — Inspeção dos 10 ZIPs locais

- **Date:** 2026-09-19
- **Author:** LLM (Claude Sonnet 5)
- **Question:** Esquema, encoding, marcadores de nulo, chaves e duplicatas dos CSVs 2017–2026 são consistentes?
- **Evidence tier:** scripted
- **Code at:** N/A (projeto sem VCS; sem código de ETL ainda)

## Environment

Local, somente leitura. Sem dados pessoais nas saídas (só agregados).

## Inputs

`acidentes{2017..2026}_todas_causas_tipos.zip` na raiz do projeto (1 CSV cada). Lidos por completo em memória (`dtype=str`).

## Reproduce

```
cd docs/specs/prf-acidentes-etl/analysis/explore/E-1-zips-locais
python3 inspect_zips.py > output.txt   # ~3–5 min
```

Scripts: `inspect_zips.py` — imprime, por arquivo, linhas, ids, cabeçalho, encoding, nulos, duplicatas, datas.

## Expected output

`output.txt`: 10 blocos; todos com `cols=37`, `same_header_as_first=True`, `enc=cp1252`, `dup_by_key_rows=0`, `dup_full_rows=0`.

## Conclusion

Mesmo cabeçalho de 37 colunas e cp1252 em todos os anos; separador `;`; datas ISO `aaaa-mm-dd`; `km` com vírgula; nulos como `NA`/`N/A` (nunca `(null)`); sem duplicatas pela chave candidata; 2026 vai de 2026-01-01 a 2026-07-31. Sustenta F-2..F-6.

## Supersedes / caveats

A métrica `idade_nonnum`/`ano_fab_nonnum` da saída é inválida (escape de regex errado no script) e deve ser ignorada; não sustenta nenhum achado. `lat_comma=0` em 2024 é tratado em E-4.
