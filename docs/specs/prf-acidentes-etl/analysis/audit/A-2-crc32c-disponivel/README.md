# A-2 — crc32c está disponível para validar downloads (D-17)?

- **Pergunta:** o D-17 exige conferir o `crc32c` de `x-goog-hash`. A biblioteca padrão ou as libs instaladas calculam crc32c?
- **Como rodar:** na raiz do projeto, `python docs/specs/prf-acidentes-etl/analysis/audit/A-2-crc32c-disponivel/check.py`. Somente leitura, sem rede.
- **Resultado (`output.txt`):** nem `google_crc32c`, nem `crc32c`, nem `crcmod`, nem `zlib` calculam crc32c. Uma implementação em Python puro sobre o ZIP 2026 (7 716 046 bytes) dá `zauaUg==`, igual ao `x-goog-hash` do E-3, em 2,7 s.
- **Limite:** o tempo é para 7,7 MB; ZIPs de 13 MB levariam cerca do dobro.
