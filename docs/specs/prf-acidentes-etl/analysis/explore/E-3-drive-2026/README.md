# E-3 — Download programático do Drive (2026)

- **Date:** 2026-09-19
- **Author:** LLM (Claude Sonnet 5)
- **Question:** O Drive entrega o ZIP 2026 por `uc?export=download`? Expõe metadados para detectar mudança sem baixar?
- **Evidence tier:** scripted
- **Code at:** N/A (projeto sem VCS; sem código de ETL ainda)

## Environment

Externo (internet), somente leitura, poucas requisições, User-Agent identificável. Autorizado pelo usuário em 2026-09-19.

## Inputs

ID do Drive do 2026 (README) e ZIP local `acidentes2026_todas_causas_tipos.zip`. O ZIP baixado vai para o scratchpad da sessão, fora do projeto.

## Reproduce

```
cd docs/specs/prf-acidentes-etl/analysis/explore/E-3-drive-2026
python3 probe_drive.py > output.txt
python3 download_and_compare.py <caminho-de-saida.zip> > output_download.txt
```

Scripts: `probe_drive.py` — 1 GET em stream, só cabeçalhos. `download_and_compare.py` — 1 GET completo, compara SHA-256 com o ZIP local.

## Expected output

`output.txt`: 303 → drive.usercontent.google.com, 200, `application/octet-stream`, `content-length: 7716046`, `last-modified` 2026-09-01, `x-goog-hash: crc32c`, magic `PK`. `output_download.txt`: `identicos: True`.

## Conclusion

O download funciona sem página de confirmação para este arquivo (7,7 MB). O ZIP local de 2026 é idêntico ao remoto em 2026-09-19. `Content-Length`, `Last-Modified` e `x-goog-hash` permitem detectar mudança sem baixar. Sustenta F-9, F-10.

## Supersedes / caveats

Uma tentativa, um arquivo (o menor). Comportamento sob cota/429 e para os 13 MB de 2025 não foi testado (não convém provocar cota). Sem `ETag`.
