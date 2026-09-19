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

- [x] Phase 6 — Red: `tests/test_latest.py` (AC-13, AC-14, AC-15, AC-30, AC-31, AC-32, AC-33, AC-37, AC-39, AC-41, NFR-3; `probe_headers`; tabela de `decidir_acao`)
- [x] Phase 6 — Green: `drive.probe_headers`, `pipeline.decidir_acao`/`atualizar_ano`; `db.carregar_ano(fechar, avisos)` e `db.registrar_pulado(drive, mensagem)`
- [x] Phase 6 — Refactor: `decidir_acao` pura; `_cabecalhos` compartilhado entre sonda e download
- [x] Phase 6 — Done when: testes verdes; sonda = 1 GET (NFR-3, contado em AC-13)

## State Handover

- Done: Phase 6 completa e verificada (106 testes `not real` verdes; `test_latest.py` 19 passed). Fases 1–5 seguem verdes.
- Next: Phase 7 (isolamento de falhas, CLI e resumo) — rodar `/ssd-workflow:ssd-task` de novo; decompor só a Phase 7. Inclui o item aberto da Phase 5 (AC-11/AC-12, contagem de GETs em `test_pipeline.py`).
- Blockers / open decisions: nenhum; sem CR aberto.
- Watch out: (1) `pipeline.atualizar_ano(conn, session, ano, id_, pasta, *, force=False, fechar=False) -> Resultado(ano, status, mensagem, avisos)`; status `ok`/`pulado`/`erro`/`fechado` (este último = já fechado, sem GET nem gravação; a Phase 7 deve tratar ano fechado pelo caminho geral com `registrar_pulado`, AC-39). Só captura `EtlError` (grava linha `erro`); outras exceções (OSError, sqlite) sobem — a Phase 7 isola. (2) Chamar `atualizar_ano` só para o ano mais recente e, com `fechar=True`, para o ano anterior quando um mais novo aparece na página; anos fechados não passam por aqui. (3) `--force` ainda faz a sonda (2 GETs); a Phase 7 propaga `force` só ao ano mais recente. (4) Avisos (`crc32c ausente…`) vão em `Resultado.avisos` e em `etl_log.mensagem`; o resumo os lê de `Resultado`. (5) Os 4 fakes de sessão (`test_drive.Resp/FakeSession`, `test_crawler`, `test_latest.Sessao`) coexistem; `test_latest` importa `Resp`, `goog`, `resp_ok` de `test_drive` — consolidar em `conftest.py` na Phase 7 se o pipeline completo precisar. (6) Herdados: RSS 717 MB em 2017 (medir 2024 na Phase 8), usar `-m "not real"` no ciclo.

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

- 2026-09-19 — `probe_headers` mora em `drive.py` e a decisão/orquestração do ano mais recente em `pipeline.py` (`decidir_acao`, `atualizar_ano`, `Resultado`), como a tabela de módulos do plan; `db.carregar_ano` ganhou `fechar` e `avisos`, `db.registrar_pulado` ganhou `drive` e `mensagem` (AC-32, AC-33, AC-41) · class: local · action: continuado
- 2026-09-19 — Referência sem cabeçalhos do Drive (`drive_content_length` nulo) compara o `content-length` com o tamanho registrado, e o crc32c só é comparado quando os dois lados o têm; a spec não descreve esses casos · class: local · action: continuado
- 2026-09-19 — `atualizar_ano` sempre sonda, mesmo com `--force` (a spec não diz se `--force` dispensa a sonda); os cabeçalhos ficam registrados e a contagem de GETs é 2 · class: local · action: continuado; Handover avisa a Phase 7

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

### 2026-09-19 — Phase 6: ano mais recente (sondagem, fechamento, `--force`)

- Gate conferido: plan #1 na rev 6, aprovação da rev 6, sem CR aberto; `phase: implementing` já gravada.
- Red: `tests/test_latest.py` escrito antes do código; coleta falhou com `ImportError: cannot import name 'probe_headers'`.
- Green: `probe_headers`, `pipeline.py`, extensões em `db.py`; 19 testes passaram; três testes (AC-14, AC-31, AC-41) reescritos depois para ficarem legíveis, sem mudar o que verificam.
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

### Pass — Phase 6 — 2026-09-19

- [x] Red confirmed — `python3 -m pytest -q tests/test_latest.py` — `1 error de coleta: ImportError probe_headers (19 testes ainda não coletados)`
- [x] Full test suite — `python3 -m pytest -q -m "not real"` — `106 passed, 11 deselected, 0 failures` (`tests/test_latest.py`: 19 passed); `-m real` não reexecutado (Phase 6 não toca transform/zipcsv; `carregar_ano` só ganhou parâmetros opcionais, coberto por `test_db.py`)
- [x] Static analysis scoped to changed files — `python3 -m compileall -q etl_prf tests` — `0 errors (baseline: n/a)`
- [x] Lint / formatting — não há ferramenta no projeto (plan, Deferred) — n/a
- [x] Any artifact the change is expected to (re)produce — nenhum; contagem de requisições (NFR-3) conferida em `test_ac13…` (1 GET) e `ls *.part`: nenhum arquivo sobrando

## Wrap up

- [ ] PR opened (`<branch>` → `main`)
- [ ] Spec linked from the issue (#1)
- [ ] Follow-up issues created and listed here (spec/plan reference them on their next revision)
