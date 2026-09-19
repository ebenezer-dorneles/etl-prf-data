# Validation — ETL de acidentes da PRF (dados abertos)

<!--
No frontmatter — spec.md is the source of truth.
Owned by the verify skill. One section per validation run, append-only.
Commands are re-run by verify, never copied from task.md.
-->

## Validation — #1 — rev 6 — 2026-09-19

Comandos re-executados nesta sessão: `python -m pytest -q` (todos os testes, incluindo `real`) → `135 passed in 169.81s`; carga completa em raiz temporária (ZIPs por symlink, `data/` vazio) com `/usr/bin/time -v` → `10 anos, 0 com erro`, RSS máx. 794 056 kB, 4:18. Os testes foram lidos para conferir que asseveram o *Then*.

### Acceptance criteria

| AC | Test / check | Command | Result | Asserts the "Then"? |
|---|---|---|---|---|
| AC-1 | `test_real_counts.py::test_ac1_*`; carga completa real | pytest; carga completa | 135 passed; contagens por ano = CSV (342497, 316638, 324192, 384640, 436523, 507204, 571052, 603215, 584010, 353107; total 4 423 078) | yes |
| AC-2 | `test_zipcsv.py::test_ac2_cp1252_preserva_acentos`; `test_transform.py::test_acentos_preservados` | pytest | passed | yes |
| AC-3 | `test_schema.py::test_ac3_table_info_*` | pytest | passed | yes |
| AC-4, AC-5, AC-6 | `test_transform.py::test_ac4_*`, `test_ac5_*`, `test_ac6_*` | pytest | passed | yes |
| AC-7 | `test_db.py::test_ac7_*`; `test_pipeline.py::test_segunda_execucao_pula_tudo_*` | pytest | passed | yes |
| AC-8 | `test_db.py::test_ac8_falha_no_segundo_chunk_*` | pytest | passed | yes |
| AC-9, AC-10, AC-27, AC-28, AC-29 | `test_crawler.py::test_ac9_*`, `test_ac10_*`, `test_ac27_*`, `test_ac28_*`, `test_ac29_*` | pytest | passed | yes |
| AC-11, AC-12 | `test_pipeline.py::test_ac11_*`, `test_ac12_*` (contagem de GETs) | pytest | passed | yes |
| AC-13, AC-14, AC-15 | `test_latest.py::test_ac13_*`, `test_ac14_*`, `test_ac15_*` | pytest | passed | yes |
| AC-16 | `test_pipeline.py::test_ac16_*`; `test_cli.py::test_ac16_*` | pytest | passed | yes |
| AC-17 | `test_drive.py::test_html_no_lugar_de_zip_falha_ac17` | pytest | passed | yes |
| AC-18, AC-19 | `test_zipcsv.py::test_ac18_*`, `test_ac19_*`; `test_pipeline.py::test_zip_com_dois_csvs_*_ac19` | pytest | passed | yes |
| AC-20, AC-21, AC-22 | `test_transform.py::test_ac20_*`, `test_ac21_*`, `test_ac22_*` | pytest | passed | yes |
| AC-23 | `test_schema.py::test_ac23_*` | pytest | passed | yes |
| AC-24 | `test_db.py::test_ac24_*` | pytest | passed | yes |
| AC-25, AC-26 | `test_drive.py::test_truncado_*_ac25`, `test_crc32c_errado_*_ac26` | pytest | passed | yes (ZIP anterior preservado) |
| AC-30, AC-31, AC-32 | `test_latest.py::test_ac30_*`, `test_ac31_*`, `test_ac32_*`; AC-30 também na carga real (2026 `ok/local`) | pytest; carga completa | passed | yes |
| AC-33 | `test_latest.py::test_ac33_*`; `test_pipeline.py::test_ano_anterior_recebe_a_ultima_verificacao_*` | pytest | passed | yes |
| AC-34 | `test_cli.py::test_ac34_*`; carga real criou `data/prf.sqlite` do zero | pytest; carga completa | passed | yes |
| AC-35 | `test_cli.py::test_ac35_*`; carga real: exit 0 + resumo | pytest; carga completa | passed | yes |
| AC-36 | `test_crc32c.py::test_vetor_padrao`, `test_crc32c_zip_2026_real` | pytest | passed | yes |
| AC-37 | `test_latest.py::test_ac37_*`; `test_pipeline.py::test_falha_na_sonda_do_ano_anterior_*` | pytest | passed | yes |
| AC-38, AC-40 | `test_crc32c.py::test_parse_*`; `test_drive.py::test_sem_crc32c_*_ac38`, `test_force_aceita_*_ac40`, `test_force_com_tamanho_divergente_*` | pytest | passed | yes |
| AC-39 | `test_db.py::test_fechado_e_repetido_em_pulado_ac39`; `test_latest.py::test_ac39_*`; `test_pipeline.py::test_ano_fechado_repete_marca_*` | pytest | passed | yes |
| AC-41 | `test_latest.py::test_ac41_*` (2 testes) | pytest | passed | yes |

### Use cases (MVP)

| UC | FRs | Delivered? | Notes |
|---|---|---|---|
| UC-1 carga dos ZIPs | FR-1..FR-3 | yes | carga real: 10 anos, 4 423 078 linhas |
| UC-2 atualização do ano mais recente | FR-6, FR-7 | yes | sonda + `--force` (`pipeline.py:atualizar_ano`) |
| UC-3 crawler + fallback | FR-5 | yes | `crawler.py` |
| UC-4 falha isolada com registro | FR-8 | yes | `pipeline.py:run` (try por ano) |
| UC-5 idempotência | FR-4 | yes | `db.carregar_ano` (DELETE+INSERT em transação); 2ª execução `pulado` (testes) |

### Non-functional requirements

| NFR | How checked | Result |
|---|---|---|
| NFR-1 | carga completa real com `/usr/bin/time -v` | RSS máx. 794 056 kB (~775 MiB) ≤ 1 GiB — ok; tempo 4:18 (só reportado) |
| NFR-2 | `test_pipeline.py::test_resumo_*`; resumo da carga real (ano, status, origem, linhas) | ok |
| NFR-3 | `test_latest.py::test_ac13_*` (1 requisição), `test_descobrir_faz_uma_requisicao`, `test_ac12_*` | ok |

### Decisions honored

| D | Where in code | Honored? |
|---|---|---|
| D-1 | `transform.py`, `zipcsv.py:54` (pandas chunks), `drive.py` (requests), `crawler.py` (bs4), `db.py` (sqlite3) | yes |
| D-2, D-3, D-15 | `schema.py:8-21` (37 colunas originais, tipos), `schema.py:46-50` (índices) | yes |
| D-5, D-18, D-21 | `crawler.py:12-13,27-43,46-57`; `zipcsv.py:37-40` | yes |
| D-6, D-10 | `schema.py:26-46`; `db.py:carregar_ano` (DELETE do ano + INSERT numa transação) | yes |
| D-7, D-23 | `pipeline.py:_ano_fechado`; `cli.py:14-22`, `config.py` | yes |
| D-13, D-14 | `transform.py:11,15-20` | yes |
| D-16, D-26, D-27 | `db.py:22-26,67-77`; `pipeline.py:_pendente_de_fechamento` | yes |
| D-17, D-28, D-29 | `drive.py:download_validated`, `_validar`; `pipeline.py:decidir_acao` | yes |
| D-19, D-22, D-24 | `drive.py:probe_headers`; `pipeline.py:decidir_acao`, `_processar` | yes |
| D-20 | `zipcsv.py:14` (`CHUNKSIZE = 100_000`); RSS medido | yes |
| D-25 | `crc32c.py` Python puro; `pyproject.toml` sem nova dependência | yes |
| D-4, D-8, D-9, D-11 | escopo/produto, cobertos pelos ACs acima; sem agendamento nem agregação por `id` | yes |
| D-12 | `README.md:1-4` cita a PRF como fonte; nada republica os dados; `.gitignore` cobre banco e ZIPs | yes (documental; README não diz "banco interno", ver nota abaixo) |

### Audit items

| AU | Status in spec | Test / check | Result |
|---|---|---|---|
| AU-1, AU-2, AU-3, AU-4 | resolved | AC-20..AC-23 | ok |
| AU-5 | resolved | AC-33 | ok |
| AU-6 | resolved | AC-24, AC-30, AC-31 | ok |
| AU-7, AU-16 | resolved | AC-25, AC-26, AC-36 | ok |
| AU-8, AU-14 | resolved | AC-27, AC-28, AC-29 | ok |
| AU-9 | resolved | AC-32, `test_probe_le_so_cabecalhos_*` | ok |
| AU-10 | resolved | NFR-1 medido | ok |
| AU-11 | resolved | AC-34, AC-35 | ok |
| AU-13 | resolved | AC-19 | ok |
| AU-17, AU-18, AU-19 | resolved | AC-33, AC-37, AC-39 | ok |
| AU-20, AU-22 | resolved | AC-38 | ok |
| AU-23 | resolved | AC-40, AC-41 | ok |
| AU-24 | resolved | linha em Risks & assumptions (`spec.md:306`); aviso testado em AC-41 | ok |
| AU-12, AU-21 | accepted-risk | linhas em Risks & assumptions (`spec.md:307`, AU-21 na tabela de audit) | ok (registrado) |
| AU-15 | invalid | — | n/a |

### Impact of the diff

- Changed areas vs impact surface: nenhuma inesperada — só `etl_prf/`, `tests/`, `pyproject.toml` e `docs/` (greenfield); `README.md` e `.gitignore` intocados.
- Untested callers / consumers: nenhum; `cli.main` → `pipeline.run` → `db`/`drive`/`crawler` cobertos por `test_cli.py`/`test_pipeline.py`.
- Irreversible side effects touched: `DELETE FROM acidentes WHERE ano` (dentro de transação com rollback, AC-8) e substituição do ZIP local (`os.replace` só após validar, AC-25/26). Nada externo é escrito.
- Input states not covered: sem trava contra execuções simultâneas (AU-12, risco aceito); cota/confirmação de vírus do Drive para ZIPs grandes só observável em uso real (Risks). A rede real não foi exercitada por testes automatizados (por desenho, `FakeSession`); a carga real desta validação usou a página e o Drive só para o crawler e a sonda do 2026 (2026 carregado do ZIP local, AC-30).

### Artifacts & rollout

- `data/prf.sqlite` com `acidentes` e `etl_log` — criado do zero pela carga completa (raiz temporária) — ok
- Rollout & rollback pieces: ok (banco novo; reversão = apagar `data/prf.sqlite`; nada a migrar)

### Result

pass — todas as linhas ok. Observações não bloqueantes: (1) o README não registra explicitamente "banco interno / não atribuir dados alterados à PRF" (D-12; o plan o classificou como documental); (2) o frontmatter/tabela de aprovação cita AU-24 como risco aceito, enquanto a tabela de audit o marca `resolved` — inconsistência só de rótulo, a linha de risco existe. Próximo: **task** Wrap up (PR, vínculo com a issue #1, follow-ups: lint/tipagem, D-12 no README).

### Change requests

Nenhum.
