---
issues: []
status: in-progress
phase: specifying
spec-revision: 1
tier: M
---

# ETL de acidentes da PRF (dados abertos)

## Context & problem

Resumo do [Problem framing](exploration.md#problem-framing), confirmado por ebenezerdorneles em 2026-09-19. Os dados abertos de acidentes da PRF (2017–2026) ficam em 10 ZIPs/CSVs publicados no Google Drive e atualizados todo mês. Não existe base única e consultável de todas as BRs e UFs. Hoje não há código, banco nem configuração: só README, report, 2 PDFs de dicionário e os 10 ZIPs locais (E-1). Relatórios e análises estão fora de escopo; o projeto é só ETL.

## Goals & success

- Um banco SQLite com a tabela `acidentes` com o histórico 2017–2026, sem filtro por BR/UF e sem descartar linhas com valores ausentes — contagem de linhas da tabela por ano = linhas do CSV do ano (E-1).
- Reexecutar não duplica linhas — duas execuções seguidas dão as mesmas contagens.
- A falha em um arquivo não impede os outros e fica registrada — AC-16, AC-17.
- O 2026 é mantido atualizado sem baixar de novo quando não mudou — AC-13.

---

## Scope

### MVP

- Carga dos ZIPs locais 2017–2025 e do 2026 na tabela `acidentes` (UC-1).
- Atualização do 2026 por comando manual, com detecção de mudança (UC-2).
- Crawler da página da PRF, com IDs do README como fallback (UC-3).
- Registro de falhas por ano sem interromper os demais (UC-4).
- Reexecução idempotente (UC-5).

### Non-goals / later phases

- Relatórios mensais e análise dos dados — o projeto é só ETL (usuário, 2026-09-19).
- Agendamento (cron/systemd) — Q-4: fica fora do escopo.
- Agregação por `id` ou tabela por ocorrência — Q-1: fora do ETL.
- Contornar limites do Drive (proxies, rotação de IP); orquestradores como Airflow.
- Republicar dados alterados como se fossem da PRF.
- Outras fontes da PRF (multas/infrações).

### Use case coverage

| UC | Outcome | FR | Reason |
|---|---|---|---|
| UC-1 | MVP | FR-1, FR-2, FR-3 | confirmado pelo usuário |
| UC-2 | MVP | FR-6, FR-7 | confirmado pelo usuário |
| UC-3 | MVP | FR-5 | decisão do usuário (D-8), 2026-09-19 |
| UC-4 | MVP | FR-8 | decisão do usuário (D-9), 2026-09-19 |
| UC-5 | MVP | FR-4 | decisão do usuário (D-10), 2026-09-19 |

---

## Requirements

### FR-1 — Carregar os ZIPs locais na tabela `acidentes`

Para cada ano 2017–2025 cujo ZIP esteja na pasta do projeto, extrair o CSV, lê-lo e inserir todas as suas linhas em `acidentes`, um ano por vez. (UC-1)

- **AC-1** — Given os ZIPs de 2017–2025 na raiz do projeto e um banco vazio, when o ETL roda, then `acidentes` contém, para cada ano, tantas linhas quanto o CSV do ano (ex.: 2017 → 342 497; 2018 → 316 638; 2024 → 603 215) e nenhuma linha é descartada por ter valor ausente.
- **AC-2** — Given um ZIP com o CSV em cp1252 e separador `;`, when é lido, then os textos acentuados chegam ao banco sem caracteres corrompidos (ex.: valores com `ã`, `ç`).

### FR-2 — Schema com os 37 campos do CSV

`acidentes` tem as 37 colunas do CSV, com os nomes originais (inclusive `condicao_metereologica`), na ordem do cabeçalho; o dicionário de 2017 é só referência de significado. (UC-1, D-2)

- **AC-3** — Given o banco carregado, when se consulta `PRAGMA table_info(acidentes)`, then as colunas de dados são exatamente as 37 do cabeçalho dos CSVs (E-1), nos mesmos nomes; colunas técnicas adicionais (D-6) são as únicas extras.

### FR-3 — Tipagem e nulos

`NA` e `N/A` viram NULL. `data_inversa` vira data ISO `aaaa-mm-dd`; `horario` fica `hh:mm:ss`; `km`, `latitude` e `longitude` viram REAL aceitando vírgula ou ponto como decimal; `br`, `idade` e `ano_fabricacao_veiculo` viram inteiros. O valor bruto não é guardado. (UC-1, D-3)

- **AC-4** — Given uma linha 2017 com `km='123,4'` e `br='NA'`, when é carregada, then `km = 123.4` (REAL) e `br IS NULL`.
- **AC-5** — Given o CSV de 2024 com latitude/longitude com ponto decimal e os demais anos com vírgula, when são carregados, then em todos os anos latitude/longitude são REAL com o valor numérico correto (ex.: `-9,123` e `-9.123` → `-9.123`).
- **AC-6** — Given um valor que não converte para o tipo da coluna (ex.: `idade='abc'`), when é carregado, then a linha é carregada com NULL nessa coluna e a ocorrência é registrada no log do ano (contagem por coluna).

### FR-4 — Reexecução sem duplicar

Cada ano é carregado numa única transação: apaga as linhas do ano e insere as novas; um ano já carregado e inalterado é pulado. (UC-5, D-10)

- **AC-7** — Given o banco já carregado, when o ETL roda de novo sem mudanças, then as contagens por ano são idênticas e nenhum ZIP é reprocessado.
- **AC-8** — Given uma carga que falha no meio de um ano, when a transação é desfeita, then o banco mantém as linhas anteriores desse ano intactas (nem parcial nem duplicado).

### FR-5 — Descobrir os links na página da PRF

O crawler acessa a página de dados abertos da PRF, filtra as linhas `Documento CSV de Acidentes <ano>` (agrupados por pessoa) e extrai o ano da linha (`<tr>`) e o ID do Drive de cada link. Se a página falhar ou mudar de forma que nenhum link seja achado, usa os 10 IDs do README como fallback. (UC-3, D-8, D-5)

- **AC-9** — Given a página atual (E-2), when o crawler roda, then devolve 10 pares (ano 2017–2026, ID do Drive) iguais aos IDs do README, ignorando os outros ~70 links do Drive da página.
- **AC-10** — Given a página responde erro HTTP ou HTML sem links de acidentes, when o crawler roda, then registra o motivo e usa os IDs do README como fallback, e o resumo final indica que o fallback foi usado.

### FR-6 — Baixar só o que falta

O ETL baixa do Drive apenas os anos 2017–2025 cujo ZIP não esteja na pasta. O 2026 segue FR-7. (UC-1, UC-3, D-7)

- **AC-11** — Given o ZIP de 2019 ausente da pasta e os demais presentes, when o ETL roda, then só o de 2019 é baixado (1 download) e carregado.
- **AC-12** — Given todos os ZIPs de 2017–2025 presentes, when o ETL roda, then não faz download desses anos.

### FR-7 — Manter o 2026 atualizado

Ao rodar, o ETL consulta os cabeçalhos do ZIP 2026 no Drive (`content-length`, `last-modified`, `x-goog-hash` crc32c) sem baixá-lo. Se diferem do que foi carregado, baixa e recarrega só 2026. O comando `--force` recarrega o 2026 sem comparar. Não há agendador. (UC-2, D-4)

- **AC-13** — Given o 2026 já carregado e o Drive com os mesmos `content-length` e `x-goog-hash`, when o ETL roda, then não baixa o ZIP e o banco fica igual.
- **AC-14** — Given o Drive com `x-goog-hash` diferente do registrado, when o ETL roda, then baixa o ZIP e recarrega o ano 2026 (FR-4), registrando os novos cabeçalhos.
- **AC-15** — Given `--force`, when o ETL roda, then recarrega o 2026 mesmo com cabeçalhos iguais.

### FR-8 — Tolerar falha por arquivo e registrar

Erro de rede, cota, resposta HTML em vez de ZIP, ZIP inválido ou CSV com cabeçalho diferente dos 37 campos em um ano é registrado com mensagem clara e não impede os outros anos. Cada execução deixa um registro por ano na tabela `etl_log` (ano, origem, status, linhas, cabeçalhos do Drive, mensagem, timestamp). O processo termina com código ≠ 0 se algum ano falhou. (UC-4, D-6, D-9)

- **AC-16** — Given o download de 2019 falha (HTTP 429) e os demais ok, when o ETL roda, then 2019 aparece em `etl_log` com status `erro` e a mensagem, os demais anos carregam, e o código de saída é ≠ 0.
- **AC-17** — Given um arquivo baixado que é HTML de confirmação/cota e não ZIP, when o ETL o valida, then falha o ano com mensagem "resposta não é ZIP" e não toca nas linhas já carregadas desse ano.
- **AC-18** — Given um CSV cujo cabeçalho difere dos 37 campos, when é lido, then falha o ano com a lista de colunas divergentes e não carrega nada desse ano.

### Non-functional requirements

| ID | Category | Requirement | How it is checked |
|---|---|---|---|
| NFR-1 | performance | Leitura em blocos (chunks): não carrega os ~600 mil linhas de um ano inteiro de uma vez como objetos Python; carga completa dos 10 anos (~4,4 milhões de linhas) em execução local única | medição de pico de memória e tempo na carga completa; reportar no verify |
| NFR-2 | observability | Cada execução imprime resumo por ano (linhas, status, origem: local/download/pulado) e usa `etl_log` | AC-16 e inspeção do log |
| NFR-3 | rede | Poucas requisições externas: 1 GET da página + 1 HEAD/GET de cabeçalhos do 2026 + downloads só do que falta | AC-12, AC-13 com contagem de requisições em teste |

---

## Constraints & dependencies

| Item | Kind | Owner | Impact if unmet |
|---|---|---|---|
| Página gov.br da PRF (HTML pode mudar) | dependency | PRF | crawler não acha links → fallback (AC-10) |
| Google Drive (`uc?export=download`, cota/confirmação de vírus) | dependency | Google | download falha → FR-8; cota só se observa em uso real (Q-6) |
| Python 3.14, pandas 3.0.5, requests, bs4 já instalados | constraint | usuário | ver D-1 |
| Citar a PRF como fonte; não atribuir à PRF dados alterados | constraint | usuário | risco de licença (CC BY-ND do portal, `reported`) |
| Execução local, sem orquestrador | constraint | usuário | — |

## Data sources

| Data source | Where it's defined | Relevant fields | Provenance | Evidence | Notes |
|---|---|---|---|---|---|
| ZIPs `acidentes<ano>_todas_causas_tipos.zip` (2017–2026) | raiz do projeto | 37 colunas iguais | confirmed | E-1 | 1 CSV por ZIP, cp1252, `;`; 4 423 078 linhas no total |
| Nulos | CSVs | `pesid`, `id_veiculo`, `br`, `km`, `idade`… | confirmed | E-1 | `NA` e `N/A`; nulos de pessoa/veículo são estruturais (~3–9%) |
| Decimais | CSVs | `km`, `latitude`, `longitude` | confirmed | E-1, E-4 | vírgula; lat/long de 2024 com ponto |
| Datas | CSVs | `data_inversa`, `horario` | confirmed | E-1 | ISO `aaaa-mm-dd`, `hh:mm:ss` (o dicionário diz `dd/mm/aaaa`) |
| Chave candidata | CSVs | `(id, pesid, id_veiculo, causa_acidente, ordem_tipo_acidente)` | confirmed | E-1 | 0 duplicatas em todos os anos; contém colunas que podem ser NULL |
| Cobertura de 2026 | CSV 2026 | `data_inversa` | confirmed | E-1 | 2026-01-01 a 2026-07-31 em 2026-09-19 |
| Dicionário 2017 (PDF) | raiz do projeto | 30 variáveis por ocorrência | confirmed | exploration F-1 | só referência de significado (D-2) |
| SQLite (saída) | a criar | `acidentes`, `etl_log` | — | — | único entregável |

## Interfaces / requests

| Interface | Direction | Shape (in/out) | Errors / limits | Provenance | Evidence |
|---|---|---|---|---|---|
| GET página PRF | out | HTML ~466 KB, ~80 links do Drive; ano na `<tr>` | nenhum erro observado (1 req) | confirmed | E-2 |
| GET Drive `uc?export=download&id=<ID>` | out | 303 → `drive.usercontent.google.com/download` → ZIP | cota/429/confirmação de vírus não observados | confirmed (só 2026, 7,7 MB) | E-3 |
| Cabeçalhos do Drive | in | `content-length`, `last-modified`, `x-goog-hash: crc32c` (sem `ETag`) | — | confirmed | E-3 |
| `robots.txt` gov.br | out | sem regra para `/prf` | — | confirmed | E-5 |

## Impacts

- Página gov.br da PRF — só leitura, 1 requisição por execução (E-2).
- Google Drive — cabeçalhos do 2026 por execução; downloads só do que falta (E-3).
- ZIPs locais 2017–2025 — só leitura, são a entrada padrão (E-1).
- SQLite `acidentes` e `etl_log` — únicos artefatos gravados.
- Dados pessoais anonimizados (`pesid`, `idade`, `sexo`) passam a ficar num banco local (E-1) — ver Security & privacy.

---

## Decisions

- **D-1 — Python com pandas (`read_csv` em chunks), requests, bs4 e o `sqlite3` da biblioteca padrão** · type: technical · decided-by: agent · evidence: exploration "Tools & integrations"
  - Why: já instalados na máquina; a carga é de ~4,4 milhões de linhas em lote único, sem exigência de velocidade; menos dependências.
  - Ruled out: polars — mais rápido, mas não instalado e sem necessidade; duckdb — dispensa o SQLite pedido no README; pandera — validação por schema é excessiva, o cabeçalho é checado em FR-8.
- **D-2 — Fonte de verdade das colunas: os 37 campos do CSV com os nomes originais, inclusive `condicao_metereologica`** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, Q-2) · evidence: E-1, F-1
  - Why: o dicionário de 2017 é por ocorrência (30 variáveis) e não descreve o CSV por pessoa.
  - Ruled out: renomear para o dicionário ou corrigir a grafia — quebra a rastreabilidade com a fonte.
- **D-3 — Tipagem: datas ISO, `km`/lat/long REAL, `br`/`idade`/`ano_fabricacao_veiculo` inteiros; `NA`/`N/A` viram NULL; bruto não é guardado** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, Q-3) · evidence: E-1, E-4
  - Why: consultas por data e número sem conversão; os nulos são estruturais.
  - Ruled out: tudo texto original — empurra a conversão para cada consulta; tipado + coluna bruta — dobra o tamanho sem necessidade.
- **D-4 — Atualização do 2026: comando manual com `--force`, detecção de mudança por `content-length`/`x-goog-hash`; agendamento fora do escopo** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, Q-4) · evidence: E-3
  - Why: os cabeçalhos permitem saber se mudou sem baixar (F-10).
  - Ruled out: timer mensal cron/systemd — fora do escopo; recarregar sempre — baixa 7,7 MB sem necessidade.
- **D-5 — Crawler: filtra `Documento CSV de Acidentes <ano>` e lê o ano da `<tr>`; IDs do README em configuração como fallback** · type: technical · decided-by: agent · evidence: E-2, F-7, F-8
  - Why: o texto dos links é "Baixar planilha"; o ano só está na linha; os 10 IDs do README existem na página.
  - Ruled out: só IDs fixos — quebra o requisito "crawler" do README; só crawler sem fallback — o ETL para se a página mudar.
- **D-6 — Tabelas: `acidentes` (37 colunas de dados + `ano` inteiro derivado do arquivo de origem, para a recarga por ano) e `etl_log`** · type: technical · decided-by: agent · evidence: E-1
  - Why: `ano` do arquivo permite `DELETE WHERE ano=?` sem depender de `data_inversa`, que pode estar NULL.
  - Ruled out: derivar o ano de `data_inversa` — pode ser NULL ou de fim de ano em outro arquivo; um banco por ano — contraria "uma tabela `acidentes`".
- **D-7 — Anos 2017–2025 vêm dos ZIPs locais; baixa do Drive só o que faltar; só o 2026 é re-baixado quando muda** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, Q-5 e correção 2 do framing) · evidence: E-1, E-3
  - Why: anos fechados não mudam; poucas requisições externas.
  - Ruled out: falhar se faltar ZIP — sem recuperação; re-baixar todos os anos sempre — cota do Drive.
- **D-8 — UC-3 (crawler) entra no MVP** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19) · evidence: README "Obrigatório"
  - Why: é requisito obrigatório do README.
  - Ruled out: só IDs do README — contraria o "Obrigatório".
- **D-9 — UC-4 (falha isolada por arquivo com registro) entra no MVP** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19) · evidence: README "validação de erro"
  - Why: a carga é em lote de 10 arquivos e o Drive pode falhar.
  - Ruled out: abortar no primeiro erro.
- **D-10 — UC-5: idempotência por recarga de ano (DELETE do ano + INSERT em uma transação); ano inalterado é pulado** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19) · evidence: E-1 (0 duplicatas), F-4
  - Why: reflete correções da PRF em linhas existentes; a chave candidata contém colunas nuláveis, e no SQLite `UNIQUE` não bloqueia linhas com NULL, então não serve como única salvaguarda.
  - Ruled out: `INSERT OR IGNORE` com chave única — não reflete correções e a chave com NULL não impede duplicatas.
- **D-11 — Granularidade: linha original por pessoa/veículo/causa; agregação por `id` fora do ETL** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, Q-1) · evidence: E-1
  - Why: preserva o dado da fonte; a agregação é análise.
  - Ruled out: agregar por `id` ou manter as duas — análise fora de escopo.
- **D-12 — Licença/atribuição: citar a PRF como fonte, não atribuir à PRF dados alterados, tratar o banco como interno; sem tratamento especial do Drive** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, Q-6) · evidence: report §2, §2.1 (`reported`)
  - Why: uso pretendido interno; cota do Drive só se observa em uso real.
  - Ruled out: análise jurídica dos termos agora — sem uso externo.

---

## Risks & assumptions

| Item | Kind | Consequence if wrong | Mitigation / how it gets verified |
|---|---|---|---|
| A página da PRF muda o HTML | risk | crawler não acha links | fallback com IDs do README (AC-10) |
| Drive aplica cota/confirmação em ZIPs maiores (13 MB; só o 2026, 7,7 MB foi testado) | risk | download de ano faltante falha | FR-8, AC-17; verificado só em uso real |
| Licença CC BY-ND do portal e termos do Google (`reported`, não verificados) | assumption | restrição ao uso/republicação | D-12: uso interno; não republicar |
| O ano do arquivo local é o do nome do ZIP (`acidentes<ano>_…`) | assumption | recarga do ano errado | AC-1 e validação do nome do ZIP |
| Mudança de esquema em anos futuros (colunas novas) | risk | cabeçalho diferente dos 37 campos | AC-18 falha o ano com a lista de divergências |
| `Last-Modified`/`x-goog-hash` reflete mudança do conteúdo | assumption | 2026 não é atualizado ou é recarregado sem necessidade | E-3 confirma que os cabeçalhos existem; `--force` como saída |

## Security & privacy

O banco contém dados por pessoa anonimizados (`pesid`, `idade`, `sexo`, veículo). Não há credenciais nem autenticação. O banco fica local, tratado como interno (D-12); o repositório não deve receber o `.sqlite` nem os ZIPs (ignorar via `.gitignore`); logs e `etl_log` não gravam valores de linhas, só contagens e mensagens.

## Migration & rollout

Banco novo: sem migração de dados. A primeira execução cria as tabelas e carrega os 10 anos. Reversão: apagar o arquivo SQLite e reexecutar (nada externo é escrito).

---

## Open questions

| ID | Question | Blocking | Owner | Blocks | Status |
|---|---|---|---|---|---|
| Q-1 | Granularidade da tabela | no | usuário | D-11 | resolved → D-11 |
| Q-2 | Fonte de verdade dos nomes/tipos das colunas | no | usuário | D-2 | resolved → D-2 |
| Q-3 | Tipagem e nulos | no | usuário | D-3 | resolved → D-3 |
| Q-4 | Como manter o 2026 atualizado | no | usuário | D-4 | resolved → D-4 |
| Q-5 | ZIP ausente de 2017–2025: baixar ou falhar | no | usuário | D-7 | resolved → D-7 |
| Q-6 | Licença/atribuição e termos do Drive | no | usuário | D-12 | resolved → D-12 |

---

## Approvals

| Revision | Approved by | Date | Audit section | Notes |
|---|---|---|---|---|

---

## Revisions

| Rev | Date | Issue | Trigger | Ids and sections changed |
|---|---|---|---|---|
| 1 | 2026-09-19 | — | initial; addendum 2026-09-19 (Q-1..Q-6, exploration `Affects spec: yes`) | todas as seções |

---

## Feedback

<!-- Audit sections ("## Audit — rev <n> — YYYY-MM-DD") are appended below by the audit skill. -->
