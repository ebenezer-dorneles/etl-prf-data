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

- [x] Phase 4 — Red: `tests/test_crawler.py` + `tests/fixtures/pagina_prf.html` sintética (AC-9, AC-10, AC-27, AC-28, AC-29)
- [x] Phase 4 — Green: `etl_prf/config.py` (10 IDs do README) e `etl_prf/crawler.py` (`parse_pagina`, `mesclar`, `descobrir`)
- [x] Phase 4 — Refactor: `parse_pagina(html)` pura, separada de `descobrir(session)`
- [x] Phase 4 — Done when: testes verdes; `python3 -c` manual contra a página real devolve 10 pares (1 requisição, fora da suíte)

- [x] Phase 5 — Red: `tests/test_drive.py` com `FakeSession` em stream (AC-17, AC-25, AC-26, AC-38, AC-40; erro HTTP e de rede)
- [x] Phase 5 — Green: `etl_prf/drive.py` (`download_validated`, `Validacao`) + `URL_DOWNLOAD` em `config.py`
- [x] Phase 5 — Refactor: `Validacao` (dataclass) carrega cabeçalhos e avisos; `_gravar` e `_validar` separados
- [x] Phase 5 — Done when: testes verdes; nenhum `.part` sobra após falha (testado em cada falha)
- [ ] Phase 5 — AC-11/AC-12 (contagem de GETs) ficam em `test_pipeline.py` na Phase 7, conforme a Coverage do plan

## State Handover

- Done: Phase 5 completa e verificada (87 testes `not real` verdes; `test_drive.py` 15 passed). Fases 1–4 seguem verdes.
- Next: Phase 6 (ano mais recente: `probe_headers`, `decidir_acao`, fechamento, `--force`) — rodar `/ssd-workflow:ssd-task` de novo; decompor só a Phase 6.
- Blockers / open decisions: nenhum; sem CR aberto.
- Watch out: (1) `drive.download_validated(session, id_, destino, ano, force=False) -> Validacao(content_length, x_goog_hash, last_modified, avisos)`; levanta `EtlError`; a sessão precisa de `get(url, stream=True, timeout=)` com `.headers`, `.iter_content`, `.close`. Os `Validacao` alimentam as colunas `drive_*` de `etl_log` e o aviso do resumo (AC-40). (2) Ordem das validações: tamanho → é ZIP → crc32c (HTML de confirmação dá "resposta não é ZIP", não "sem crc32c"). (3) `probe_headers` (Phase 6) deve reaproveitar a leitura de cabeçalhos e `parse_goog_hash`; AC-41 usa a mesma mensagem "x-goog-hash sem crc32c". (4) `FakeSession`/`Resp` de streaming estão em `tests/test_drive.py`, os do crawler em `tests/test_crawler.py`; consolidar em `conftest.py` se a Phase 6/7 precisar de ambos. (5) Herdados: API de `db.py`/`crawler.descobrir` (Phase 3/4), RSS 717 MB em 2017 (medir 2024 na Phase 8), usar `-m "not real"` no ciclo.

## Deviations

- 2026-09-19 — `parse_goog_hash` trata base64 inválido e valor de tamanho ≠ 4 bytes como ausente (`None`), caso que a spec não descreve (D-28 só cobre ausência) · class: local · action: continuado; mesma consequência da ausência (falha de download, ou aviso com `--force`)

- 2026-09-19 — `EtlError` ficou em `etl_prf/errors.py` (plan a citava sem dizer o módulo) e `listar_zips` foi acrescentada a `zipcsv.py` para o aviso de ZIP fora do padrão (FR-1) · class: local · action: continuado
- 2026-09-19 — DDL de `etl_log` (listada em `schema.py` na tabela de módulos do plan) fica para a Phase 3, onde é primeiro usada · class: local · action: continuado; registrado no Handover
- 2026-09-19 — `test_real_counts.py` também roda `transformar` sobre cada chunk real (o plan pedia só a contagem de linhas); 2026 pula se a contagem mudar desde o E-1 · class: local · action: continuado

- 2026-09-19 — Colunas de `etl_log` nomeadas por este passo (`drive_content_length`, `drive_x_goog_hash`, `drive_last_modified`, `tamanho`, `sha256`, `linhas`, `fechado`, `mensagem`, `timestamp`) e `db.py` ganhou `impressao`, `ano_inalterado`, `registrar_pulado`, `registrar_erro` além das funções do plan; a linha `ok` é gravada na mesma transação da carga · class: local · action: continuado

- 2026-09-19 — O filtro do crawler exige "Agrupados por pessoa - Todas as causas e tipos de acidentes" na linha, não só `Documento CSV de Acidentes <ano>`: a página real tem 3 linhas por ano (por ocorrência, por pessoa, por pessoa todas as causas) e só a última bate com os IDs do README/AC-9 · class: local · action: continuado; FR-5 já cita o texto completo entre parênteses
- 2026-09-19 — `config.py` criado antes do Red (só dados, sem comportamento); Red confirmado pela falta de `etl_prf.crawler` · class: local · action: continuado

- 2026-09-19 — Validações em ordem tamanho → ZIP → crc32c (a spec lista tamanho, crc32c, ZIP): assim uma página HTML do Drive, que não traz `x-goog-hash`, falha como "resposta não é ZIP" (AC-17) e não como "sem crc32c" · class: local · action: continuado; nenhum AC depende da ordem
- 2026-09-19 — `content-length` ausente na resposta falha com "content-length ausente" e falha de rede/HTTP vira `EtlError("download falhou: …")`; a spec não descreve esses casos · class: local · action: continuado
- 2026-09-19 — `drive.py` importa `_atualizar` (privado) de `crc32c.py` para calcular o crc32c em stream durante a gravação, sem reler o arquivo · class: local · action: continuado
- 2026-09-19 — AC-11/AC-12 não são testados aqui: o plan os põe em `test_pipeline.py` (Phase 7), pois dependem do pipeline decidir baixar ou não · class: local · action: continuado; item aberto no Checklist

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

### 2026-09-19 — Phase 4: crawler e mesclagem com o README

- Gate conferido: plan #1 na rev 6, aprovação da rev 6, sem CR aberto; `phase: implementing` já gravada.
- Red: `tests/test_crawler.py` + `tests/fixtures/pagina_prf.html` (sintética: 3 linhas por ano 2007–2026 e 30 links de ruído); coleta falhou com `ModuleNotFoundError: etl_prf.crawler`.
- Green: `config.py`, `crawler.py` (`parse_pagina`, `mesclar`, `descobrir`); 13 testes passaram de primeira.
- Página real (1 GET): 10 pares iguais ao README, sem fallback nem divergência.
- Desvios locais registrados acima.

### 2026-09-19 — Phase 5: download validado

- Gate conferido: plan #1 na rev 6, aprovação da rev 6, sem CR aberto; `phase: implementing` já gravada.
- Red: `tests/test_drive.py` (15 testes) escrito antes do código; coleta falhou com `ModuleNotFoundError: etl_prf.drive`.
- Green: `drive.py` e `URL_DOWNLOAD`; 15 testes passaram de primeira.
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

### Pass — Phase 4 — 2026-09-19

- [x] Red confirmed — `python3 -m pytest -q tests/test_crawler.py` — `1 error de coleta: ModuleNotFoundError etl_prf.crawler (13 testes ainda não coletados)`
- [x] Full test suite — `python3 -m pytest -q -m "not real"` — `72 passed, 11 deselected, 0 failures` (`tests/test_crawler.py`: 13 passed); `-m real` não reexecutado (Phase 4 não toca transform/zipcsv/db)
- [x] Static analysis scoped to changed files — `python3 -m compileall -q etl_prf tests` — `0 errors (baseline: n/a)`
- [x] Lint / formatting — não há ferramenta no projeto (plan, Deferred) — n/a
- [x] Any artifact the change is expected to (re)produce — `python3 -c "…descobrir(requests.Session())…"` contra a página real (1 requisição): `10 True False [] [] []` (10 pares, iguais ao README, sem fallback, sem divergências, sem avisos)

### Pass — Phase 5 — 2026-09-19

- [x] Red confirmed — `python3 -m pytest -q tests/test_drive.py` — `1 error de coleta: ModuleNotFoundError etl_prf.drive (15 testes ainda não coletados)`
- [x] Full test suite — `python3 -m pytest -q -m "not real"` — `87 passed, 11 deselected, 0 failures` (`tests/test_drive.py`: 15 passed); `-m real` não reexecutado (Phase 5 não toca transform/zipcsv/db)
- [x] Static analysis scoped to changed files — `python3 -m compileall -q etl_prf tests` — `0 errors (baseline: n/a)`
- [x] Lint / formatting — não há ferramenta no projeto (plan, Deferred) — n/a
- [x] Any artifact the change is expected to (re)produce — nenhum; `ls *.part` na raiz: nenhum arquivo sobrando

## Wrap up

- [ ] PR opened (`<branch>` → `main`)
- [ ] Spec linked from the issue (#1)
- [ ] Follow-up issues created and listed here (spec/plan reference them on their next revision)
