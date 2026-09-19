# Tasks — ETL de acidentes da PRF (dados abertos)

## Checklist

- [x] Phase 1 — `tests/test_crc32c.py`: vetor padrão, vazio, arquivo × bytes, parse com md5 e ordem invertida, sem `crc32c=`, real 2026 (Red)
- [x] Phase 1 — `etl_prf/crc32c.py`: `crc32c` (tabela, polinômio `0x82F63B78`, blocos de 1 MiB) e `parse_goog_hash` (Green)
- [x] Phase 1 — `pyproject.toml` com testpaths, pythonpath e marcador `real`
- [x] Phase 1 — Refactor: mesma função para `bytes` e arquivo aberto; nada mais a extrair
- [x] Phase 1 — Done when: testes passam e tempo do crc32c real medido (2,2 s para 7 716 046 bytes)

- [x] Phase 2 — Red: `tests/test_schema.py`, `test_transform.py`, `test_zipcsv.py`, `test_real_counts.py` (+ `tests/conftest.py` com ZIPs sintéticos cp1252)
- [x] Phase 2 — Green: `etl_prf/errors.py`, `schema.py` (`COLUNAS`, DDL de `acidentes` + índices), `transform.py`, `zipcsv.py`
- [x] Phase 2 — Refactor: `COLUNAS` é a fonte única de DDL e transformação
- [x] Phase 2 — Done when: `not real` verde; AC-1 confere as 10 contagens; nenhuma linha descartada

- [x] Phase 3 — Red: `tests/test_db.py` (AC-7, AC-8, AC-24, referência ignora `erro`, `fechado` repetido em `pulado`/AC-39, cabeçalhos do Drive, mensagem de falhas)
- [x] Phase 3 — Green: `etl_prf/db.py` (`conectar`, `impressao`, `referencia`, `esta_fechado`, `ano_inalterado`, `carregar_ano`, `registrar_pulado`, `registrar_erro`) + DDL de `etl_log` em `schema.py`
- [x] Phase 3 — Refactor: DDL e SQL em constantes nomeadas (`DDL_ETL_LOG`, `SQL_*`)
- [x] Phase 3 — Done when: testes passam e `sqlite3` de banco temporário mostra `ok` + `pulado` esperados (2017 real)

## State Handover

- Done: Phase 3 completa e verificada (59 testes `not real` verdes; `test_db.py` 12 passed). Fases 1–2 seguem verdes.
- Next: Phase 4 (crawler e mesclagem com o README) — rodar `/ssd-workflow:ssd-task` de novo; decompor só a Phase 4.
- Blockers / open decisions: nenhum; sem CR aberto.
- Watch out: (1) API de `db.py` para o pipeline: `carregar_ano(conn, ano, zip, origem, drive=dict(content_length, x_goog_hash, last_modified))` só faz commit no sucesso e repassa a exceção — quem chama deve chamar `registrar_erro` (com `drive` se leu cabeçalhos). `registrar_pulado(conn, ano, origem, fechado=False)` exige referência e repete `fechado` (D-27); `fechado=True` grava a marca da verificação final (Phase 6). `ano_inalterado(conn, ano, impressao(zip))` decide pulo. (2) A conexão usa `isolation_level=None` (BEGIN explícito); `registrar_*` são autocommit. (3) Memória: carga real de 2017 em `carregar_ano` teve pico de RSS 717 MB (NFR-1: 1 GiB); anos maiores (2024: 603 mil linhas) ainda não medidos com o banco — medir na Phase 8 e reduzir `CHUNKSIZE` se preciso. (4) Suíte completa com `real` ~147 s; usar `-m "not real"` (~5 s) no ciclo Red/Green.

## Deviations

- 2026-09-19 — `parse_goog_hash` trata base64 inválido e valor de tamanho ≠ 4 bytes como ausente (`None`), caso que a spec não descreve (D-28 só cobre ausência) · class: local · action: continuado; mesma consequência da ausência (falha de download, ou aviso com `--force`)

- 2026-09-19 — `EtlError` ficou em `etl_prf/errors.py` (plan a citava sem dizer o módulo) e `listar_zips` foi acrescentada a `zipcsv.py` para o aviso de ZIP fora do padrão (FR-1) · class: local · action: continuado
- 2026-09-19 — DDL de `etl_log` (listada em `schema.py` na tabela de módulos do plan) fica para a Phase 3, onde é primeiro usada · class: local · action: continuado; registrado no Handover
- 2026-09-19 — `test_real_counts.py` também roda `transformar` sobre cada chunk real (o plan pedia só a contagem de linhas); 2026 pula se a contagem mudar desde o E-1 · class: local · action: continuado

- 2026-09-19 — Colunas de `etl_log` nomeadas por este passo (`drive_content_length`, `drive_x_goog_hash`, `drive_last_modified`, `tamanho`, `sha256`, `linhas`, `fechado`, `mensagem`, `timestamp`) e `db.py` ganhou `impressao`, `ano_inalterado`, `registrar_pulado`, `registrar_erro` além das funções do plan; a linha `ok` é gravada na mesma transação da carga · class: local · action: continuado

## Execution Log

### 2026-09-19 — Phase 1: crc32c e x-goog-hash

- Gate conferido: plan da issue #1 na rev 6, aprovação da rev 6, sem CR aberto; `phase: planning` já estava gravada, mantida a transição para `implementing`.
- Baseline registrado antes de qualquer código (árvore só com `spec.md` alterado e `plan.md` novo).
- Red: testes escritos antes do módulo; falharam com `ModuleNotFoundError: etl_prf.crc32c`.
- Green: `etl_prf/__init__.py`, `etl_prf/crc32c.py`, `pyproject.toml`.
- Desvio local registrado acima (base64 inválido).

### 2026-09-19 — Phase 2: schema, transformação e leitura do ZIP

- Gate conferido: plan #1 na rev 6, aprovação da rev 6, sem CR aberto; `phase: implementing` já gravada.
- Red: quatro módulos de teste escritos antes do código; coleta falhou com `ModuleNotFoundError: etl_prf.errors` (e schema/transform/zipcsv ausentes).
- Green: `errors.py`, `schema.py`, `transform.py`, `zipcsv.py`; os 47 testes `not real` passaram de primeira e os 10 reais confirmaram as contagens.
- Desvios locais registrados acima. Cabeçalho de referência dos 37 campos lido do ZIP 2017 (igual ao E-1) e replicado em `tests/conftest.py`.

### 2026-09-19 — Phase 3: recarga transacional, idempotência e `etl_log`

- Gate conferido: plan #1 na rev 6, aprovação da rev 6, sem CR aberto; `phase: implementing` já gravada.
- Red: `tests/test_db.py` escrito antes do código; coleta falhou com `ModuleNotFoundError: etl_prf.db`.
- Green: `db.py` e `DDL_ETL_LOG` em `schema.py`; 12 testes novos passaram de primeira.
- Carga real de 2017 em banco temporário: 342 497 linhas, `etl_log` com `ok` e `pulado` (tamanho 10 726 416, mesmo sha256), RSS 717 336 kB.
- Desvios locais registrados acima.

## Verification

### Baseline — #1 — 2026-09-19

- Full test suite — `python3 -m pytest -q` — `0 tests (no tests ran), 0 failures`
- Static analysis — `python3 -m compileall -q etl_prf tests` — não aplicável na baseline (pastas inexistentes); não há ruff/mypy instalados

### Pass — Phase 1 — 2026-09-19

- [x] Red confirmed — `python3 -m pytest -q` — `1 error de coleta: ModuleNotFoundError etl_prf.crc32c (7 testes ainda não coletados)`
- [x] Full test suite — `python3 -m pytest -q` — `7 passed, 0 failures` (`-m "not real"`: 6 passed, 1 deselected)
- [x] Static analysis scoped to changed files — `python3 -m compileall -q etl_prf tests` — `0 errors (baseline: n/a)`
- [x] Lint / formatting — não há ferramenta no projeto (plan, Deferred) — n/a
- [x] Any artifact the change is expected to (re)produce — nenhum nesta fase; crc32c real do 2026 medido em `pytest -m real --durations` (2,2 s)

### Pass — Phase 2 — 2026-09-19

- [x] Red confirmed — `python3 -m pytest -q` — `4 errors de coleta: ModuleNotFoundError etl_prf.errors/schema/transform/zipcsv (testes ainda não coletados)`
- [x] Full test suite — `python3 -m pytest -q` — `58 passed, 0 failures` em 147 s (`-m "not real"`: 47 passed, 11 deselected em 4 s; `-m real tests/test_real_counts.py`: 10 passed em 136 s)
- [x] Static analysis scoped to changed files — `python3 -m compileall -q etl_prf tests` — `0 errors (baseline: n/a)`
- [x] Lint / formatting — não há ferramenta no projeto (plan, Deferred) — n/a
- [x] Any artifact the change is expected to (re)produce — nenhum; contagens reais conferidas: 2017 342 497, 2018 316 638, 2019 324 192, 2020 384 640, 2021 436 523, 2022 507 204, 2023 571 052, 2024 603 215, 2025 584 010, 2026 353 107; pico de RSS do pytest real 858 892 kB (`/usr/bin/time -v`)

### Pass — Phase 3 — 2026-09-19

- [x] Red confirmed — `python3 -m pytest -q tests/test_db.py` — `1 error de coleta: ModuleNotFoundError etl_prf.db (12 testes ainda não coletados)`
- [x] Full test suite — `python3 -m pytest -q -m "not real"` — `59 passed, 11 deselected, 0 failures` (`tests/test_db.py`: 12 passed); `-m real` não reexecutado (Phase 3 não toca transform/zipcsv; Phase 2 seguia 10 passed)
- [x] Static analysis scoped to changed files — `python3 -m compileall -q etl_prf tests` — `0 errors (baseline: n/a)`
- [x] Lint / formatting — não há ferramenta no projeto (plan, Deferred) — n/a
- [x] Any artifact the change is expected to (re)produce — `sqlite3` em banco temporário após carga real de 2017 + `pulado`: `etl_log` = (2017, local, ok, 342497, 10726416, 2577824c, 0) e (2017, local, pulado, NULL, 10726416, 2577824c, 0); `COUNT(*) acidentes` = 342497; pico RSS 717 336 kB

## Wrap up

- [ ] PR opened (`<branch>` → `main`)
- [ ] Spec linked from the issue (#1)
- [ ] Follow-up issues created and listed here (spec/plan reference them on their next revision)
