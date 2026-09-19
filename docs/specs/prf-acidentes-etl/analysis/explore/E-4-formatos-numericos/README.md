# E-4 — Formato de decimais entre anos

- **Date:** 2026-09-19
- **Author:** LLM (Claude Sonnet 5)
- **Question:** lat/long, km, idade e ano de fabricação têm o mesmo formato em todos os anos?
- **Evidence tier:** scripted
- **Code at:** N/A (projeto sem VCS; sem código de ETL ainda)

## Environment

Local, somente leitura. Sem dados pessoais nas saídas (só agregados).

## Inputs

Primeiras 20.000 linhas de 2023, 2024 e 2025.

## Reproduce

```
cd docs/specs/prf-acidentes-etl/analysis/explore/E-4-formatos-numericos
python3 sample_formats.py > output.txt
```

Scripts: `sample_formats.py` — amostra e contagem de separadores decimais.

## Expected output

`output.txt`: 2023 e 2025 com vírgula em lat/long; 2024 com ponto (`-22.72935968`); `km` com vírgula nos três.

## Conclusion

O separador decimal de latitude/longitude muda em 2024 (ponto), enquanto `km` mantém vírgula. Um parser único com `decimal=","` erra 2024. Sustenta F-5.

## Supersedes / caveats

Amostra de 20k linhas de 3 anos; E-1 confirma para o arquivo inteiro que 2024 tem `lat_comma=0` e os demais têm vírgula em quase todas as linhas. Anos 2017–2022 e 2026 não foram amostrados aqui.
