# Exploration — ETL de acidentes da PRF (dados abertos)

Phase: ready <!-- framing | exploring | ready — updated by the explore skill -->

<!--
No frontmatter — spec.md is the source of truth for status/issues.
Owned by the explore skill. Every finding cites evidence: a code citation
(path:line@sha) or an E-n folder under analysis/explore/.
Raw imported reports go in analysis/explore/ unchanged.
Tier S (lite mode): fill Problem framing, Current behavior & architecture, Impact surface,
Use cases, Open questions, Readiness; mark the rest "N/A (lite)".
-->

## Problem framing

<!-- Phase A. No solution in "Problem". Stop for the user's confirmation before Phase B. -->

- **Problem:** Os dados abertos de acidentes da PRF (2017–2026) ficam em 10 arquivos CSV/ZIP separados, publicados em links do Google Drive e atualizados todo mês. Não existe uma base única, consultável e sempre atualizada de todas as BRs e UFs, então gerar relatórios mensais de acidentes exige tratar os arquivos à mão.
- **Who is affected / stakeholders:** Quem produz e consome os relatórios mensais de acidentes (o usuário, ebenezerdorneles). Decisor: o usuário. Tocados: a PRF como fonte (cccom@prf.gov.br) e o Google Drive como hospedagem. *(a confirmar)*
- **Current behavior (as described):** O README lista 10 links do Drive e 10 ZIPs já estão na pasta do projeto. Ainda não há processo automatizado de extração, tratamento ou carga. O `report.md` descreve granularidade por pessoa/veículo/causa, CSV `;` com decimais em vírgula e nulos como `(null)`/`NA`.
- **Desired outcome & success:** Um banco SQLite com a tabela `acidentes` com o histórico 2017–2026, sem filtro por BR ou UF, sem descartar linhas com valores ausentes, com campos conforme o Dicionário de Variáveis. Sucesso: (relatórios mensais fora de escopo) reexecutar não duplica linhas, a falha em um arquivo não impede os outros e é registrada,.
- **Constraints:** README exige crawler da página da PRF (ou download manual dos CSVs) e validação de erro nos links. Fonte hospedada no Google Drive, com cota e bloqueio possíveis (report §2.1). Execução local, Python (versão da máquina: 3.14). Citar a PRF como fonte. Anos 2017–2025 vêm dos ZIPs locais (default); só 2026 é re-baixado para manter atualizado.
- **Non-goals:** *(proposto, a confirmar)* Contornar limites do Drive (proxies, rotação de IP). Orquestradores como Airflow. Republicar dados alterados como se fossem da PRF. Relatórios e análise dos dados. Outras fontes da PRF (multas/infrações) além de acidentes.
- **Suggested solution (hypothesis):** `requests` + `BeautifulSoup` para descobrir links, `pandas`/`polars` em chunks, SQLite com `etl_log`, cron/systemd timer mensal (report §4–5). Não é requisito.
- **Tier:** M (proposto) — múltiplas integrações (página gov.br + Drive), decisão de modelo de dados (granularidade), comportamento operacional (idempotência, agendamento) e dados pessoais anonimizados. *Confirmar contra a tabela de tiers da ssd-spec.*
- **Goal questions:**
  1. O que existe hoje no repositório além de README, report e ZIPs (código, banco, config)?
  2. Os 10 ZIPs locais têm mesmo esquema (37 colunas), encoding, separador e tratamento de nulos em todos os anos?
  3. Quais são os volumes reais por ano e as chaves de unicidade (`id`, `pesid`, `id_veiculo`, `causa_acidente`, `ordem_tipo_acidente`)? Há duplicatas?
  4. A página da PRF ainda expõe os links do Drive de forma parseável e o ano é identificável pelo texto do link?
  5. O download do Drive funciona de forma programática, e como responde a cota/confirmação?
  6. Quais campos do dicionário divergem do que está nos CSVs (tipos, domínios, `condicao_metereologica`)?
  7. (encerrada: relatórios mensais fora de escopo)
  8. Qual granularidade da tabela `acidentes`: linha original, agregada por `id` ou ambas?
- **Confirmed by:** ebenezerdorneles, 2026-09-19 — Correções: (1) "relatórios mensais" do README estão fora do escopo; o projeto é só ETL, não análise (a PRF atualiza os dados mensalmente). (2) Anos 2017–2025 usam os ZIPs locais como padrão; só o de 2026 é mantido atualizado (re-download). (3) Non-goals e Tier M aceitos. (4) Scripts de Fase B: somente leitura e poucas requisições externas.

## Sources

<!-- Imported reports and other inputs. Path under analysis/explore/, date, author. -->

| Source | Path | Date | Notes |
|---|---|---|---|
| Relatório de automatização (raw, imutável) | analysis/explore/report.md | 2026-09-19 | Autor: assistente. Fatos são `reported` até verificação. |
| README do projeto | README.md | — | Objetivo, processo e requisitos obrigatórios |

---

## Current behavior & architecture

- O repositório não tem código de ETL, banco nem configuração: só `README.md`, `report.md`, 2 PDFs de dicionário e 10 ZIPs (2017–2026). Projeto sem VCS, então não há sha. — listagem de `/mnt/storage/projects/python/etl-prf-data` em 2026-09-19 (`ls`), `git status` retornou "not a git repository"
- O README define objetivo, fluxo por arquivo e o requisito obrigatório do crawler com validação de erro. — `README.md:1-53`
- É um projeto novo (greenfield). Não há convenções de código a seguir; Python 3.14.7 com pandas 3.0.5, requests e bs4 já instalados. — comando `python3 -c "import pandas,requests,bs4"` em 2026-09-19

## Impact surface

| Area | Why it is affected | Evidence |
|---|---|---|
| Página gov.br da PRF | Fonte dos links; o HTML pode mudar | E-2 |
| Google Drive | Hospeda os ZIPs; só o de 2026 é re-baixado | E-3 |
| ZIPs locais 2017–2025 | Entrada padrão da carga; anos fechados | E-1 |
| SQLite (`acidentes`) | Único entregável; modelo e chave em aberto | Q-1 |
| Agendamento e log de execução | "Manter 2026 atualizado" implica reexecução periódica | Q-4 |
| Dados pessoais anonimizados (`pesid`, `idade`, `sexo`) | O banco contém dados por pessoa | E-1 |
| PDFs de dicionário | Fonte dos nomes/tipos dos campos, divergente dos CSVs | F-1 |

---

## Use cases

| ID | Actor | Goal | Trigger | Expected outcome | Source | Requirement confirmation |
|---|---|---|---|---|---|---|
| UC-1 | Usuário | Carga inicial do histórico | Execução manual | Anos 2017–2025 dos ZIPs locais carregados na tabela `acidentes`, sem descartar linhas | user 2026-09-19 (resposta 5), README | confirmed-by ebenezerdorneles, 2026-09-19 |
| UC-2 | Usuário / agendador | Manter 2026 atualizado | Nova publicação mensal da PRF | Verificar no Drive se o ZIP 2026 mudou; se mudou, baixar e recarregar só 2026 | user 2026-09-19 (resposta 5) | confirmed-by ebenezerdorneles, 2026-09-19 |
| UC-3 | Processo ETL | Descobrir os links de download | Início da execução | Extrair da página da PRF ano e ID do Drive de cada arquivo de acidentes | README "Obrigatório", report §4 | pending-confirmation |
| UC-4 | Processo ETL | Tolerar falha de um arquivo | Erro de rede/cota/ZIP inválido | Registrar o erro e seguir com os outros; mensagem clara | README "validação de erro", report §2.1 | pending-confirmation |
| UC-5 | Usuário | Reexecutar sem duplicar | Segunda execução | Mesmo resultado, sem linhas repetidas | report §5 | pending-confirmation |

---

## Tools & integrations

| Tool / system | Role | Provenance | Evidence | Notes |
|---|---|---|---|---|
| Página gov.br da PRF | Descoberta dos links | confirmed | E-2 | 200, HTML estático, ~80 links do Drive |
| Google Drive `uc?export=download` | Download dos ZIPs | confirmed (só 2026) | E-3 | 303 → usercontent; sem página de confirmação para 7,7 MB |
| `requests`, `bs4`, `pandas` | Rede, HTML, transformação | confirmed | E-1..E-4 | Já instalados; `lxml` importado por `bs4` sem erro |
| SQLite, `polars`, `pandera`, `duckdb` | Carga / alternativas | n/a (hipótese de solução, não fato) | — | Escolha é decisão do spec |
| Fallback de IDs em configuração | Se a página mudar | confirmed | E-2 | README já lista os 10 IDs e todos existem na página |
| `robots.txt` do gov.br | Permissão de rastreio | confirmed | E-5 | Sem regra para `/prf` |

---

## Data

| Data source | Where it lives | Relevant fields | Provenance | Evidence | Notes |
|---|---|---|---|---|---|
| ZIPs de acidentes por ano | Raiz do projeto, 7,7–13 MB cada (~105 MB total) | 37 colunas iguais nos 10 anos | confirmed | E-1 | 1 CSV por ZIP, cp1252, `;` |
| Linhas | 316 638 (2018) a 603 215 (2024); 2026: 353 107 | — | confirmed | E-1 | ~4,4 milhões (4 423 078) no total; muitas linhas por `id` |
| Nulos | `NA` e `N/A` (sem `(null)`) | `pesid`, `br`, `km`, `idade`, `id_veiculo`… | confirmed | E-1 | Nulos de pessoa/veículo são estruturais (acidente sem pessoa ou veículo) |
| Decimais | `km` com vírgula; lat/long com vírgula, exceto 2024 (ponto) | `km`, `latitude`, `longitude` | confirmed | E-1, E-4 | O parser precisa tratar por ano ou por valor |
| Datas | `aaaa-mm-dd`; horário `hh:mm:ss` | `data_inversa`, `horario` | confirmed | E-1 | Dicionário diz `dd/mm/aaaa` |
| Cobertura de 2026 | 2026-01-01 a 2026-07-31 | `data_inversa` | confirmed | E-1 | Agosto ainda não publicado em 2026-09-19 |
| Chave candidata | `(id, pesid, id_veiculo, causa_acidente, ordem_tipo_acidente)` | — | confirmed | E-1 | 0 duplicatas em todos os anos; linhas 100% únicas também |
| Dicionário `Dicionário de Variáveis_ocorrencia_2017.pdf` | Raiz do projeto | 30 variáveis por ocorrência | confirmed | pdftotext do PDF | Não é o dicionário do CSV por pessoa (F-1) |

---

## Requests / interfaces

| Interface | Direction | Shape (in/out) | Auth | Errors / limits | Provenance | Evidence |
|---|---|---|---|---|---|---|
| GET página PRF | out | HTML ~466 KB | nenhuma | Nenhum erro observado (1 req) | confirmed | E-2 |
| GET Drive `uc?export=download&id=<ID>` | out | 303 → `drive.usercontent.google.com/download` → ZIP | nenhuma | Cota/429/confirmação de vírus não observados; não testados | confirmed (só 2026) | E-3 |
| Cabeçalhos do Drive | in | `content-length`, `last-modified`, `x-goog-hash: crc32c` (sem `ETag`) | — | — | confirmed | E-3 |

---

## As-is vs expected

| # | Expected (source) | Actual | Evidence | Becomes |
|---|---|---|---|---|
| 1 | README: campos "são os mesmos do Dicionário 2017" | O dicionário descreve 30 variáveis por ocorrência (inclui `pessoas`, `veiculos`, `ignorados`, `feridos`); os CSVs têm 37 colunas por pessoa/veículo/causa (inclui `pesid`, `id_veiculo`, `marca`, `sexo`, `idade`…) e não têm essas agregadas | F-1, E-1 | Q-2 |
| 2 | Dicionário: `data_inversa` em `dd/mm/aaaa`; `km` com ponto | CSV: `aaaa-mm-dd`; `km` com vírgula | E-1 | Q-2 |
| 3 | Report §4: identificar o ano pelo texto do link | O texto dos links é "Baixar planilha"; o ano está na `<tr>` | E-2 | Decisão do spec (UC-3) |
| 4 | Report §3: nulos como `(null)` ou `NA` | Só `NA` e `N/A` aparecem | E-1 | Decisão do spec |
| 5 | Report §3: lat/long com vírgula | 2024 usa ponto | E-4 | Decisão do spec |
| 6 | README: "relatórios mensais" | Fora de escopo (usuário) | Confirmação do usuário | Non-goal registrado |
| 7 | README/report: "baixar do site" como crawler para todos os anos | Usuário: 2017–2025 dos ZIPs locais; só 2026 atualizado | Confirmação do usuário | Q-5 |

---

## Findings

1. O dicionário do repositório (`Dicionário de Variáveis_ocorrencia_2017.pdf`) descreve o dataset "desagregado por ocorrência", com 30 variáveis, e não os CSVs "agrupados por pessoa" com 37 colunas. — pdftotext do PDF; E-1
2. Os 10 ZIPs têm o mesmo cabeçalho de 37 colunas, encoding cp1252 e separador `;`. — E-1
3. ~4,4 milhões (4 423 078) de linhas no total; cada `id` aparece em várias linhas (2017: 342 497 linhas, 89 567 ids). — E-1
4. Não há duplicatas pela chave candidata nem linhas totalmente duplicadas em nenhum ano. — E-1
5. Decimais: `km` usa vírgula em todos os anos; latitude/longitude usam vírgula, exceto 2024 (ponto). — E-1, E-4
6. Nulos aparecem como `NA` e `N/A`; `pesid`, `id_veiculo` e afins são nulos de forma estrutural em ~3–9% das linhas; `br` e `km` são `NA` juntos (509 linhas em 2017). — E-1
7. A página da PRF responde 200 e contém os 10 IDs do README, mas o ano só aparece no texto da linha, não no do link. — E-2
8. A página lista ~80 links do Drive de vários conjuntos; filtrar por `Documento CSV de Acidentes <ano>` é necessário. — E-2
9. O download do 2026 pelo Drive funciona e o ZIP remoto é idêntico ao local (SHA-256 igual). — E-3
10. O Drive expõe `content-length`, `last-modified` e `x-goog-hash` (crc32c), o que permite saber se o 2026 mudou sem baixá-lo. — E-3
11. O 2026 local cobre 2026-01-01 a 2026-07-31 e o `Last-Modified` remoto é 2026-09-01. — E-1, E-3

12. O `robots.txt` do gov.br não tem regras para `/prf` e permite a página. — E-5
13. Licença (CC BY-ND 3.0 do portal), termos do Google e cotas do Drive são afirmações do report, ainda não verificadas (`reported`). — report §2, §2.1

---

## Evidence index

| ID | Question | Tier | Folder | Command | Conclusion |
|---|---|---|---|---|---|
| E-1 | Esquema, encoding, nulos, chaves dos 10 ZIPs | scripted | analysis/explore/E-1-zips-locais/ | `python3 inspect_zips.py` | F-2, F-3, F-4, F-6, F-11 |
| E-2 | Links na página da PRF e onde está o ano | scripted | analysis/explore/E-2-pagina-prf/ | `python3 list_links.py; python3 context_of_known_ids.py` | F-7, F-8 |
| E-3 | Download do Drive e metadados (2026) | scripted | analysis/explore/E-3-drive-2026/ | `python3 probe_drive.py; python3 download_and_compare.py <saida.zip>` | F-9, F-10 |
| E-4 | Formato decimal entre anos | scripted | analysis/explore/E-4-formatos-numericos/ | `python3 sample_formats.py` | F-5 |
| E-5 | robots.txt permite a página da PRF | scripted | analysis/explore/E-5-robots/ | `python3 check_robots.py` | F-12 |

---

## Open questions

| ID | Question | Blocking | Owner | Blocks |
|---|---|---|---|---|
| Q-1 | Granularidade da tabela `acidentes`: linha original (por pessoa/veículo/causa), agregada por `id`, ou ambas? **Respondida (ebenezerdorneles, 2026-09-19, opção recomendada):** Linha original por pessoa/veículo/causa, com a chave candidata; agregação por `id` fica fora do ETL. | no (resolvida) | usuário | Modelo de dados e DDL da spec |
| Q-2 | Qual é a fonte de verdade dos nomes/tipos das colunas: os 37 campos do CSV ou o dicionário 2017 (30 variáveis, formatos diferentes)? Devemos manter a grafia `condicao_metereologica` do CSV? **Respondida (ebenezerdorneles, 2026-09-19, opção recomendada):** Os 37 campos do CSV com os nomes originais, inclusive `condicao_metereologica`; o dicionário de 2017 é só referência de significado. | no (resolvida) | usuário | Schema e FRs de transformação |
| Q-3 | Guardar tipado (datas ISO, `km`/lat/long REAL, `br` inteiro) ou texto original? Onde vão o valor bruto e os `NA` que não convertem (ex.: `br`)? **Respondida (ebenezerdorneles, 2026-09-19, opção recomendada):** Tipado (datas ISO, `km`/lat/long REAL, `br`/`idade`/`ano_fabricacao_veiculo` inteiros); `NA`/`N/A` viram NULL, sem guardar o bruto. | no (resolvida) | usuário | Regras de transformação |
| Q-4 | Como o 2026 será mantido atualizado: comando manual, timer mensal (cron/systemd) ou outro? **Respondida (ebenezerdorneles, 2026-09-19, opção recomendada):** Comando manual (`--force`) com detecção de mudança por `content-length`/`x-goog-hash`; agendamento fica fora do escopo. | no (resolvida) | usuário | Escopo de agendamento |
| Q-5 | Se um ZIP de 2017–2025 não estiver na pasta, o processo deve baixá-lo do Drive (crawler) ou falhar? **Respondida (ebenezerdorneles, 2026-09-19, opção recomendada):** Baixar do Drive só os anos que faltarem (crawler). | no (resolvida) | usuário | Escopo do crawler (README "obrigatório") |
| Q-6 | Como tratar licença/atribuição (CC BY-ND do portal, citar a PRF) e os termos do Google Drive para uso do banco? Só o usuário pode confirmar o uso pretendido; a cota do Drive só se observa em uso real. **Respondida (ebenezerdorneles, 2026-09-19, opção recomendada):** Só registrar na spec: citar a PRF, não atribuir à PRF dados alterados, tratar o banco como interno; sem tratamento especial do Drive. | no (resolvida) | usuário | Seção de riscos/NFR da spec |

---

## Readiness

- [x] Problem framing confirmed by the user (who, when)
- [x] Every Goal question answered with evidence or recorded in Open questions
- [x] No open question is still answerable by investigation; each names its owner and whether it blocks
- [x] As-is described with code citations; Impact surface mapped
- [x] Every as-is vs expected conflict listed
- [x] Every use case has an id, source, expected outcome and requirement confirmation
- [x] Every `reported`/`assumed` fact is verified (now `confirmed`) or listed in Open questions
- [x] Every evidence folder has its README (and script); each command was re-run once and reproduced the conclusion
- [x] No secrets or personal data committed; runs against production / personal data approved

<!--
## Addenda — YYYY-MM-DD
Appended by later re-entries. Question · E-n · conclusion · Affects spec: yes (<ids>) | no
-->


## Addenda — 2026-09-19

Q-1 a Q-6 respondidas pelo usuário (todas na opção recomendada; ver Open questions). Nenhuma evidência nova.
Affects spec: yes (modelo de dados, schema, tipagem, atualização do 2026, escopo do crawler, riscos/licença). Carregam como decisões a registrar na spec, não como perguntas abertas.
