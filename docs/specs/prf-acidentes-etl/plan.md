# Plan — ETL de acidentes da PRF (dados abertos)

## Plan — #1

Issue: https://github.com/ebenezer-dorneles/etl-prf-data/issues/1

Spec revision: 6

### Context

- Repositório sem código: só `README.md`, `.gitignore`, os 10 ZIPs, o PDF do dicionário e `docs/`. Nenhum padrão a seguir; a convenção nasce aqui (greenfield).
- `.gitignore` já cobre `*.zip`, `data/`, `*.sqlite`, `__pycache__/`, `.pytest_cache/` (`.gitignore:1-8`) — atende Security & privacy sem mudança.
- Ambiente (verificado): Python 3.14.7, pytest 9.0.3 (`~/.local/bin/pytest`), pandas 3.0.5, requests, bs4, psutil importáveis. **Não há** ruff, mypy, uv nem pre-commit instalados.
- Evidência usada: E-1 (37 colunas, contagens por ano, cp1252, `;`), E-2 (página, 10 IDs), E-3 (cabeçalhos do Drive, `zauaUg==`), E-4 (decimais), A-1 (nulos, `1e+05`), A-2 (crc32c Python puro, 2,7 s para 7,7 MB). `analysis/` só é referenciado; nada é copiado nem escrito lá.
- Dados de teste: os ZIPs reais (2017–2026) na raiz servem para os testes `real` (contagens do AC-1, crc32c do AC-36). Os demais testes usam CSVs/ZIPs sintéticos pequenos montados em `tmp_path` (cp1252, `;`, 37 colunas) e um `FakeSession` no lugar de `requests` — nenhum teste automatizado acessa a rede.

### Strategy

Pacote `etl_prf/` na raiz; a lógica de I/O recebe dependências por parâmetro (sessão HTTP, caminho do banco, pasta dos ZIPs, relógio) para os testes não tocarem rede nem o `data/` real.

| Módulo | Responsabilidade | FR/D |
|---|---|---|
| `schema.py` | as 37 colunas em ordem, tipo por coluna (D-15), DDL de `acidentes` (+ `ano`, índices) e `etl_log` | FR-2, D-6 |
| `crc32c.py` | `crc32c(bytes/stream) -> int` puro Python; `parse_goog_hash(header) -> int \| None` | D-25, D-28 |
| `transform.py` | um chunk pandas (`dtype=str`, `keep_default_na=False`) → tipos/NULL, contagem de falhas por coluna | FR-3, D-13..15 |
| `zipcsv.py` | valida nome/1 CSV/cabeçalho, itera chunks de 100 mil em stream, sem extrair | FR-1, FR-8, D-21 |
| `db.py` | conexão, criação de tabelas, `carregar_ano` (transação DELETE+INSERT), leitura da referência e de `fechado` em `etl_log` | FR-4, D-10, D-16, D-26, D-27 |
| `crawler.py` | página → `{ano: id}`, mescla com IDs do README (`config.py`), valida ID | FR-5, D-5, D-18 |
| `drive.py` | `probe_headers`, `download_validated` (tmp → valida → `os.replace`) | FR-6, FR-7, D-17, D-19, D-28, D-29 |
| `pipeline.py` | orquestra por ano, decide local/download/pulado/recarga, isola falhas, monta o resumo | FR-4/7/8, D-22, D-24 |
| `__main__.py` / `cli.py` | `argparse` com `--force`, código de saída | FR-9, D-23 |

Não muda: os ZIPs, o README, o `.gitignore`. O aviso de nulos por coluna (AC-6) vai para `etl_log.mensagem` e para o resumo, só como contagens (Security & privacy).
Decisões de plano (não alteram "o quê"): `pyproject.toml` só com `[tool.pytest.ini_options]` (`testpaths`, marcador `real`); pico de memória medido com `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` em subprocesso.

### Tooling & commands

| Check | Command | Scope | Why |
|---|---|---|---|
| Baseline (antes da 1ª mudança) | `cd /mnt/storage/projects/python/etl-prf-data && git status --short && python3 -m pytest -q` | repositório | esperado: árvore limpa e "no tests ran"; task registra o resultado |
| Suíte completa (sem dados reais) | `python3 -m pytest -q -m "not real"` | `tests/` | rápida, sem rede e sem ZIPs |
| Suíte completa + reais | `python3 -m pytest -q` | `tests/` | inclui AC-1 (contagens), AC-36 e a carga completa; usa os ZIPs da raiz |
| Testes por fase | `python3 -m pytest -q tests/test_<módulo>.py` | um arquivo | ciclo Red/Green |
| Sintaxe/análise estática | `python3 -m compileall -q etl_prf tests` | arquivos alterados | não há ruff/mypy/pyright instalados; não instalar sem decisão do usuário |
| Lint / formatação | — (nenhuma ferramenta no projeto) | — | ver Deferred |
| Memória (NFR-1) | `python3 -c "import resource,subprocess,sys; subprocess.run([sys.executable,'-m','etl_prf'],check=False); print(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024,'MiB')"` com `data/` vazio e sem rede (Drive) | carga completa dos 10 anos | falha se > 1024 MiB |
| Artefato visível | `python3 -m etl_prf` e `sqlite3 data/prf.sqlite "select ano,count(*) from acidentes group by ano"` | banco local | o revisor confere contagens e o resumo impresso (NFR-2) |

### Review & code standards

- Revisão: o usuário (ebenezerdorneles) no PR da issue #1; antes de abrir, rodar a skill **auditoria-de-impacto** no diff (ela cobre estados de entrada não testados) e `/code-review`.
- Padrões: nomes de colunas e de `etl_log` em português como a spec; funções puras em `transform.py`/`crc32c.py`/`crawler.py` (parse) e I/O só em `db.py`, `drive.py`, `zipcsv.py`; uma exceção `EtlError(ano, mensagem)` capturada só em `pipeline.py` (isolamento de FR-8); type hints em todas as assinaturas; sem dependência nova (D-1, D-25); nunca logar valores de linhas (só contagens).
- Sem convenção existente a citar; estas ficam registradas aqui e o task as repete em `task.md` se mudar.

### Phases

**Phase 1 — crc32c e `x-goog-hash` (spike barato, valida A-2)** · covers: FR-6, D-25, D-28, AC-36, AC-38 (parte de parsing)

- **Red:** `tests/test_crc32c.py`: `crc32c(b"123456789") == 0xE3069283`; `parse_goog_hash("crc32c=zauaUg==,md5=abc") == 0xCDAB9A52`; `"md5=abc"` → `None`; espaços e ordem invertida; teste `real` com o ZIP 2026 (pula se o tamanho ≠ 7 716 046) igual a `0xCDAB9A52`. Falha: `ModuleNotFoundError`.
- **Green:** tabela de 256 entradas, polinômio refletido `0x82F63B78`, leitura em blocos de 1 MiB; parser por vírgula/`strip`, base64 → `int.from_bytes(..., "big")`.
- **Refactor:** aceitar `bytes` e arquivo aberto com a mesma função.
- **Done when:** os testes passam e o crc32c real do 2026 é medido (registrar o tempo).

**Phase 2 — Schema, transformação e leitura do ZIP em stream (a fase de maior incerteza: dados reais e memória)** · covers: UC-1, FR-1, FR-2, FR-3, D-2, D-6, D-13, D-14, D-15, D-21, AC-1..AC-6, AC-18, AC-19, AC-20..AC-23

- **Red:** `tests/test_schema.py` (AC-3, AC-23 via `PRAGMA` em banco em memória); `tests/test_transform.py` (AC-4, AC-5 vírgula/ponto, AC-6 contagem por coluna, AC-20, AC-21, AC-22 com `''` × `'NULL'`, `NA`/`N/A`); `tests/test_zipcsv.py` (AC-2 `ã`/`ç` em cp1252, AC-18 lista de colunas divergentes, AC-19 0 e 2 CSVs, nome de ZIP fora do padrão ignorado com aviso). `tests/test_real_counts.py` (marcador `real`): AC-1 lê os 9 ZIPs fechados e o 2026 e compara contagem de linhas com o CSV (2017 → 342 497; 2018 → 316 638; 2024 → 603 215). Falha: módulos ausentes.
- **Green:** `pd.read_csv(..., sep=";", encoding="cp1252", dtype=str, keep_default_na=False, chunksize=100_000)` sobre o stream do `zipfile`; conversão por coluna (`to_numeric`, `Decimal`/`int` exato para científico, `to_datetime(format="%Y-%m-%d")`); falha de conversão → NULL + contador.
- **Refactor:** tabela `COLUNAS: list[tuple[nome, tipo]]` única para DDL e transformação.
- **Done when:** suíte de `not real` verde; AC-1 confere as 10 contagens; nenhuma linha descartada.

**Phase 3 — Recarga transacional, idempotência e `etl_log`** · covers: UC-5, FR-4, D-10, D-16, D-26, D-27, AC-7, AC-8, AC-24

- **Red:** `tests/test_db.py`: 2ª execução mantém contagens e grava `pulado` repetindo tamanho, sha256 e cabeçalhos (AC-7); falha injetada no meio do ano (exceção no 2º chunk) deixa as linhas anteriores intactas (AC-8); ZIP com sha256 diferente recarrega só 2019 (AC-24); referência ignora linha `erro`; `fechado` repetido em `pulado` (AC-39, parte de banco).
- **Green:** `carregar_ano` com `BEGIN` / `DELETE WHERE ano=?` / `INSERT` por chunk / `COMMIT`, `ROLLBACK` no erro; `referencia(ano)` = linha `ok`/`pulado` mais recente; `esta_fechado(ano)` = `EXISTS fechado=1`.
- **Refactor:** DDL e consultas SQL em constantes nomeadas.
- **Done when:** os testes passam e o `sqlite3` do arquivo temporário mostra o `etl_log` esperado.

**Phase 4 — Crawler e mesclagem com o README** · covers: UC-3, FR-5, D-5, D-18, D-21, AC-9, AC-10, AC-27, AC-28, AC-29

- **Red:** `tests/test_crawler.py` com HTML sintético em `tests/fixtures/` (linha `<tr>` com `Documento CSV de Acidentes <ano>`, ~70 links de ruído): 10 pares iguais aos do README (AC-9); erro HTTP e HTML vazio → fallback + flag no resumo (AC-10); página sem 2019 (AC-27); ID divergente (AC-28); ID com `&` ou curto (AC-29).
- **Green:** bs4 (`lxml` ou `html.parser`), regex `^[A-Za-z0-9_-]{20,}$` no ID extraído de `/file/d/<ID>/`; `config.py` com os 10 IDs do README.
- **Refactor:** função pura `parse_pagina(html)` separada de `descobrir(session)`.
- **Done when:** testes verdes; um `python3 -c` manual contra a página real devolve 10 pares (uma requisição; não roda em CI).

**Phase 5 — Download validado (`drive.download_validated`)** · covers: FR-6, D-17, D-25, D-28, D-29, AC-11, AC-12, AC-25, AC-26, AC-38, AC-40

- **Red:** `tests/test_drive.py` com `FakeSession` (corpo em chunks, cabeçalhos configuráveis): truncado → "tamanho divergente" e nenhum ZIP criado/alterado (AC-25); `crc32c` errado → mensagem de checksum e ZIP anterior intacto (AC-26); sem `crc32c=` falha com "x-goog-hash sem crc32c" (AC-38); com `--force` aceita e avisa (AC-40), divergência de tamanho ainda falha; HTML no lugar de ZIP → "resposta não é ZIP" (AC-17); AC-11/AC-12 no nível do pipeline (contagem de GETs).
- **Green:** grava em `<zip>.part` no mesmo diretório, valida `content-length`, `crc32c`, `zipfile.is_zipfile`, então `os.replace`; apaga o `.part` no erro.
- **Refactor:** `Validacao` (dataclass) com avisos para log/resumo.
- **Done when:** testes verdes; nenhum `.part` sobra após falha.

**Phase 6 — Ano mais recente: sondagem, fechamento e `--force`** · covers: UC-2, FR-7, D-19, D-22, D-24, D-26, D-27, D-29, AC-13, AC-14, AC-15, AC-30, AC-31, AC-32, AC-33, AC-37, AC-39, AC-41, NFR-3

- **Red:** `tests/test_latest.py` (pipeline com `FakeSession` e banco temporário): mesmos cabeçalhos → sem download (AC-13, NFR-3 conta GETs = 1 página + 1 sondagem); `x-goog-hash` diferente → recarrega (AC-14); `--force` (AC-15); sem carga `ok` + ZIP local com `content-length` igual/diferente (AC-30); referência ignora `erro` (AC-31); só `last-modified` mudou (AC-32); 2027 na página → baixa 2027, sonda 2026 uma última vez, grava `fechado=1`, depois não sonda mais (AC-33, AC-39); falha de rede na sonda → `fechado` não gravado e repete (AC-37); sem `crc32c=`: compara só tamanho + aviso; tamanho diferente falha (AC-41).
- **Green:** `probe_headers` via `session.get(url, stream=True)` fechando sem ler o corpo; regra de mudança e de `fechado` conforme FR-7.
- **Refactor:** `decidir_acao(ano, ...) -> Acao` pura e tabelada, testada em separado.
- **Done when:** testes verdes; contagem de requisições confere NFR-3.

**Phase 7 — Isolamento de falhas, CLI e resumo** · covers: UC-4, FR-8, FR-9, D-9, D-23, NFR-2, AC-16, AC-17, AC-34, AC-35

- **Red:** `tests/test_pipeline.py`: 429 em 2019 → `erro` em `etl_log`, demais carregam, código ≠ 0 (AC-16); `tests/test_cli.py` via `subprocess`/`main(argv)` com `data/` inexistente cria `data/prf.sqlite`, `acidentes`, `etl_log` (AC-34); tudo ok → código 0 e resumo por ano com linhas, status e origem `local/download/pulado` (AC-35, NFR-2); resumo/`etl_log` sem valores de linha (teste busca um valor sentinela).
- **Green:** `main(argv)` com `argparse`, `EtlError` capturada por ano em `pipeline.run`, `sys.exit(1 if falhas else 0)`.
- **Refactor:** formatação do resumo em uma função.
- **Done when:** todos os testes `not real` verdes; execução manual mostra o resumo.

**Phase 8 — Carga completa real e medições** · covers: NFR-1, AC-1, AC-12, AC-35, D-20, Risks (`id` científico)

- **Red/substituto:** não é test-first (medição de ponta a ponta com dados reais): script de verificação = comando de memória da tabela acima + `sqlite3` para contagens e para as 43 linhas de `id` científico (conferir contra o CSV, Risks). Sem rede além da página e da sonda do 2026.
- **Green:** ajustar `chunksize`/inserção (`executemany`) só se RSS > 1 GiB.
- **Done when:** pico ≤ 1024 MiB, contagens por ano = CSV, 2ª execução pula os 10 anos (AC-7), tempo total anotado (só reportado).

### Coverage

| Item | Fase | Teste / check |
|---|---|---|
| AC-1 | 2 (real), 8 | `test_real_counts.py`; contagens por ano na fase 8 |
| AC-2, AC-18, AC-19 | 2 | `test_zipcsv.py` |
| AC-3, AC-23 | 2 | `test_schema.py` (`PRAGMA`) |
| AC-4, AC-5, AC-6, AC-20, AC-21, AC-22 | 2 | `test_transform.py` |
| AC-7, AC-8, AC-24, AC-39 | 3 | `test_db.py` |
| AC-9, AC-10, AC-27, AC-28, AC-29 | 4 | `test_crawler.py` |
| AC-11, AC-12 | 5, 7 | contagem de GETs em `test_pipeline.py`; AC-12 também na fase 8 |
| AC-17, AC-25, AC-26, AC-38, AC-40 | 5 | `test_drive.py` |
| AC-36 | 1 | `test_crc32c.py` (vetor + real) |
| AC-13, AC-14, AC-15, AC-30, AC-31, AC-32, AC-33, AC-37, AC-41 | 6 | `test_latest.py` |
| AC-16, AC-34, AC-35 | 7 | `test_pipeline.py`, `test_cli.py` |
| NFR-1 | 8 | medição de RSS (falha se > 1 GiB) |
| NFR-2 | 7 | AC-16/AC-35 + inspeção do resumo |
| NFR-3 | 6 | contagem de requisições em `test_latest.py` |
| D-6, D-10, D-15 | 2, 3 | `test_schema.py`, `test_db.py` |
| D-13, D-14 | 2 | `test_transform.py` |
| D-16, D-26, D-27 | 3, 6 | `test_db.py`, `test_latest.py` |
| D-17, D-25, D-28, D-29 | 1, 5, 6 | `test_crc32c.py`, `test_drive.py`, `test_latest.py` |
| D-18, D-21 | 4, 2 | `test_crawler.py`, `test_zipcsv.py` |
| D-19, D-22, D-24 | 6 | `test_latest.py` |
| D-20 | 8 | medição de RSS |
| D-23 | 7 | `test_cli.py` |
| AU-12 (concorrência), AU-21, AU-24 | — | aceitos como risco (spec); AU-24 tem o aviso testado no AC-41 |
| Security (sem valores em log) | 7 | teste com valor sentinela |
| D-1, D-2, D-3, D-4, D-5, D-7..D-9, D-11, D-12 | — | decisões de escolha/escopo, cobertas pelos ACs acima; D-12 é só documental (README) |

### Rollout & rollback

Banco novo, sem migração (Migration & rollout). Ordem: mergear o pacote; o usuário roda `python3 -m etl_prf` (1ª execução cria `data/prf.sqlite` e carrega os 10 anos; 2026 usa o ZIP local se o tamanho do Drive coincidir, D-24). Reversão: apagar `data/prf.sqlite` e reexecutar; ZIPs baixados ficam na raiz. Observar: o resumo (nenhum `erro`), contagens por ano, RSS, aviso de `crc32c` ausente.

### Deferred

- Ferramentas de lint/tipagem (ruff/mypy) e pre-commit: não instalados; propor ao usuário depois, fora desta issue.
- Agendamento, relatórios, agregação por `id`, tabela por ocorrência, outras fontes da PRF (Non-goals da spec).
- Trava contra execuções simultâneas (AU-12, risco aceito).
- Cota/confirmação de vírus do Drive para ZIPs de 13 MB: só verificável em uso real (Risks).

### Spec gaps

Nenhum.
