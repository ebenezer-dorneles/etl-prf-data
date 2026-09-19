# A-1 — tipos, marcadores de nulo e ids entre anos

- **Pergunta:** os 37 campos parseiam como a spec supõe (FR-3)? Há marcadores de nulo além de `NA`/`N/A`? Há ids repetidos entre anos (D-6)?
- **Como rodar:** na raiz do projeto, `python docs/specs/prf-acidentes-etl/analysis/audit/A-1-tipos-e-ids-entre-anos/check.py`. Somente leitura, sem rede, lê os 10 ZIPs locais em chunks.
- **Resultado (`output.txt`):**
  - `id` aparece em notação científica (ex.: `1e+05`) em 2018 (2 linhas), 2019 (2), 2020 (6), 2021 (30), 2024 (3).
  - String vazia em `tipo_acidente` (55/40/1 linhas em 2018/2019/2020): é um terceiro marcador de nulo; o `na_values` padrão do pandas também o converteria.
  - `idade`, `ano_fabricacao_veiculo`, `br`, `pesid`, `id_veiculo`, contagens e `km`/lat/long: 0 valores não parseáveis (fora `NA`/`N/A`). As métricas `idade_nonnum`/`ano_fab_nonnum` do E-1 estão erradas (o regex foi escapado dentro do f-string; o valor é igual ao total de não nulos).
  - Nenhum `id` se repete entre anos.
- **Limite:** o script não prova que `1e+05` é exatamente 100000 (só mostra o primeiro exemplo por coluna).
