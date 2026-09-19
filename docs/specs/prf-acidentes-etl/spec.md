---
issues: []
status: in-progress
phase: approved
spec-revision: 6
tier: M
---

# ETL de acidentes da PRF (dados abertos)

## Context & problem

Resumo do [Problem framing](exploration.md#problem-framing), confirmado por ebenezerdorneles em 2026-09-19. Os dados abertos de acidentes da PRF (2017–2026) ficam em 10 ZIPs/CSVs publicados no Google Drive e atualizados todo mês. Não existe base única e consultável de todas as BRs e UFs. Hoje não há código, banco nem configuração: só README, report, 2 PDFs de dicionário e os 10 ZIPs locais (E-1). Relatórios e análises estão fora de escopo; o projeto é só ETL.

## Goals & success

- Um banco SQLite com a tabela `acidentes` com o histórico 2017–2026, sem filtro por BR/UF e sem descartar linhas com valores ausentes — contagem de linhas da tabela por ano = linhas do CSV do ano (E-1).
- Reexecutar não duplica linhas — duas execuções seguidas dão as mesmas contagens.
- A falha em um arquivo não impede os outros e fica registrada — AC-16, AC-17.
- O ano mais recente publicado (hoje 2026) é mantido atualizado sem baixar de novo quando não mudou — AC-13, AC-33 (D-22).

---

## Scope

### MVP

- Carga dos ZIPs locais dos anos fechados (hoje 2017–2025) e do ano mais recente (hoje 2026) na tabela `acidentes` (UC-1).
- Interface de linha de comando `python -m etl_prf [--force]` (UC-1, UC-2; D-23).
- Atualização do ano mais recente por comando manual, com detecção de mudança; anos novos entram sozinhos (UC-2; D-22).
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
| UC-1 | MVP | FR-1, FR-2, FR-3, FR-9 | confirmado pelo usuário |
| UC-2 | MVP | FR-6, FR-7, FR-9 | confirmado pelo usuário |
| UC-3 | MVP | FR-5 | decisão do usuário (D-8), 2026-09-19 |
| UC-4 | MVP | FR-8 | decisão do usuário (D-9), 2026-09-19 |
| UC-5 | MVP | FR-4 | decisão do usuário (D-10), 2026-09-19 |

---

## Requirements

### FR-1 — Carregar os ZIPs locais na tabela `acidentes`

Para cada ano fechado (todo ano descoberto exceto o mais recente, D-22; hoje 2017–2025) cujo ZIP `acidentes<ano>_todas_causas_tipos.zip` esteja na raiz do projeto, ler o CSV do ZIP em stream, sem extraí-lo para disco, e inserir todas as suas linhas em `acidentes`, um ano por vez. O ano vem do nome do ZIP; ZIP com outro nome é ignorado com aviso. (UC-1, D-21)

- **AC-1** — Given os ZIPs de 2017–2025 na raiz do projeto e um banco vazio, when o ETL roda, then `acidentes` contém, para cada ano, tantas linhas quanto o CSV do ano (ex.: 2017 → 342 497; 2018 → 316 638; 2024 → 603 215) e nenhuma linha é descartada por ter valor ausente.
- **AC-2** — Given um ZIP com o CSV em cp1252 e separador `;`, when é lido, then os textos acentuados chegam ao banco sem caracteres corrompidos (ex.: valores com `ã`, `ç`).

### FR-2 — Schema com os 37 campos do CSV

`acidentes` tem as 37 colunas do CSV, com os nomes originais (inclusive `condicao_metereologica`), na ordem do cabeçalho, mais a coluna técnica `ano` (D-6); o dicionário de 2017 é só referência de significado. Há índices em `ano`, `id` e `data_inversa` e nenhuma chave única (D-15, D-10). (UC-1, D-2)

- **AC-3** — Given o banco carregado, when se consulta `PRAGMA table_info(acidentes)`, then as colunas de dados são exatamente as 37 do cabeçalho dos CSVs (E-1), nos mesmos nomes; colunas técnicas adicionais (D-6) são as únicas extras.
- **AC-23** — Given o banco criado, when se consulta `PRAGMA index_list(acidentes)`, then existem índices cobrindo `ano`, `id` e `data_inversa`.

### FR-3 — Tipagem e nulos

Marcadores de nulo: `NA`, `N/A` e string vazia viram NULL; nenhum outro texto vira NULL (D-14). Tipos (D-15): `data_inversa` vira data ISO `aaaa-mm-dd`; `horario` fica texto `hh:mm:ss`; `km`, `latitude` e `longitude` viram REAL aceitando vírgula ou ponto como decimal; `id`, `pesid`, `id_veiculo`, `br`, `idade`, `ano_fabricacao_veiculo`, `ordem_tipo_acidente`, `ilesos`, `feridos_leves`, `feridos_graves` e `mortos` viram inteiros; as demais colunas ficam texto. Inteiro em notação científica (`1e+05`) vira o inteiro exato e só vira NULL se o valor não for inteiro exato (D-13). O valor bruto não é guardado. (UC-1, D-3)

- **AC-4** — Given uma linha 2017 com `km='123,4'` e `br='NA'`, when é carregada, then `km = 123.4` (REAL) e `br IS NULL`.
- **AC-5** — Given o CSV de 2024 com latitude/longitude com ponto decimal e os demais anos com vírgula, when são carregados, then em todos os anos latitude/longitude são REAL com o valor numérico correto (ex.: `-9,123` e `-9.123` → `-9.123`).
- **AC-6** — Given um valor que não converte para o tipo da coluna (ex.: `idade='abc'`), when é carregado, then a linha é carregada com NULL nessa coluna e a ocorrência é registrada no log do ano (contagem por coluna).
- **AC-20** — Given uma linha 2021 com `id='4e+05'`, when é carregada, then `id = 400000` (inteiro).
- **AC-21** — Given um `id='1.5e+00'` (não é inteiro exato), when é carregado, then `id IS NULL` e a ocorrência entra na contagem do log (AC-6).
- **AC-22** — Given uma linha 2018 com `tipo_acidente=''` e outra com `tipo_acidente='NULL'`, when são carregadas, then a primeira tem `tipo_acidente IS NULL` e a segunda mantém o texto `NULL`.

### FR-4 — Reexecução sem duplicar

Cada ano é carregado numa única transação: apaga as linhas do ano e insere as novas. "Ano inalterado" significa que o ZIP tem o mesmo tamanho e o mesmo sha256 do ZIP da linha de referência em `etl_log` (a mais recente com status `ok` ou `pulado`, D-26); nesse caso o ano é pulado e a execução grava uma linha `pulado`. (UC-5, D-10, D-16, D-26)

- **AC-7** — Given o banco já carregado, when o ETL roda de novo sem mudanças, then as contagens por ano são idênticas, nenhum ZIP é reprocessado e cada ano pulado ganha em `etl_log` uma linha `pulado` que repete tamanho, sha256 e cabeçalhos da referência.
- **AC-8** — Given uma carga que falha no meio de um ano, when a transação é desfeita, then o banco mantém as linhas anteriores desse ano intactas (nem parcial nem duplicado).
- **AC-24** — Given o ZIP local de 2019 substituído por uma versão com sha256 diferente da referência (`ok` ou `pulado`), when o ETL roda, then o ano 2019 é recarregado (apaga e reinsere) e os demais são pulados.

### FR-5 — Descobrir os links na página da PRF

O crawler acessa a página de dados abertos da PRF, filtra as linhas `Documento CSV de Acidentes <ano>` (agrupados por pessoa) e extrai o ano da linha (`<tr>`) e o ID do Drive de cada link. O resultado é mesclado por ano com os 10 IDs do README (D-18): o link da página vence, o README preenche anos ausentes, e divergências são registradas. IDs que não casem `^[A-Za-z0-9_-]{20,}$` são descartados com aviso antes de entrar na URL (D-21). Os anos descobertos definem o ano mais recente (D-22). (UC-3, D-8, D-5)

- **AC-9** — Given a página atual (E-2), when o crawler roda, then devolve 10 pares (ano 2017–2026, ID do Drive) iguais aos IDs do README, ignorando os outros ~70 links do Drive da página.
- **AC-10** — Given a página responde erro HTTP ou HTML sem links de acidentes, when o crawler roda, then registra o motivo e usa os 10 IDs do README, e o resumo final indica que o fallback foi usado.
- **AC-27** — Given uma página com links de 9 anos (sem 2019), when o crawler roda, then 2019 vem do README, os outros 9 vêm da página, e o resumo indica o ano preenchido pelo fallback.
- **AC-28** — Given uma página cujo ID de 2021 difere do README, when o crawler roda, then o ID da página é usado e a divergência é registrada.
- **AC-29** — Given um link cujo ID contém `&` ou tem menos de 20 caracteres, when o crawler roda, then o link é descartado com aviso e o ano usa o ID do README.

### FR-6 — Baixar só o que falta

O ETL baixa do Drive apenas os anos fechados cujo ZIP não esteja na raiz do projeto, e anos novos ainda sem ZIP (D-22). O ano mais recente segue FR-7. O download vai para um arquivo temporário e só substitui o ZIP local depois de validado: `content-length` recebido igual ao anunciado, `crc32c` igual ao de `x-goog-hash` e conteúdo ZIP (D-17). O `crc32c` é calculado em Python puro, sem nova dependência (D-25). Do cabeçalho `x-goog-hash` extrai-se o item `crc32c=`, decodifica-se de base64 (4 bytes big-endian) e compara-se com o valor calculado como inteiro de 32 bits; cabeçalho sem `crc32c=` falha o download, salvo com `--force`, que valida só `content-length` e conteúdo ZIP e registra um aviso no log e no resumo (D-28, D-29). (UC-1, UC-3, D-7, D-25, D-28, D-29)

- **AC-11** — Given o ZIP de 2019 ausente da pasta e os demais presentes, when o ETL roda, then só o de 2019 é baixado (1 download) e carregado.
- **AC-12** — Given todos os ZIPs de 2017–2025 presentes, when o ETL roda, then não faz download desses anos.
- **AC-25** — Given um download de 2019 que termina com menos bytes que o `content-length`, when o ETL valida, then falha o ano 2019 com mensagem de tamanho divergente e nenhum ZIP local é criado ou alterado.
- **AC-36** — Given o valor de teste `crc32c(b"123456789")`, when a função de checksum roda, then devolve `0xE3069283` (vetor padrão do CRC-32C), e o valor calculado sobre o ZIP de 2026 (7 716 046 bytes) é igual ao de `x-goog-hash` (A-2).
- **AC-38** — Given `x-goog-hash: crc32c=zauaUg==,md5=abc` e o ZIP de 2026 (7 716 046 bytes), when o ETL valida, then extrai `crc32c=zauaUg==`, decodifica para `0xCDAB9A52` e o compara com o `crc32c` calculado, que é igual; e given um `x-goog-hash` sem `crc32c=` (só `md5=abc`), then, sem `--force`, falha o download com mensagem "x-goog-hash sem crc32c" (dica: `--force`) e nenhum ZIP local é criado ou alterado.
- **AC-40** — Given o mesmo `x-goog-hash` sem `crc32c=` e `--force`, com `content-length` recebido igual ao anunciado e conteúdo ZIP, when o ETL valida, then o ZIP é aceito e carregado, e o log e o resumo trazem o aviso "crc32c ausente, validado só por tamanho e formato"; com `content-length` divergente falha como no AC-25.
- **AC-26** — Given um download com `crc32c` diferente do de `x-goog-hash`, when o ETL valida, then falha o ano com mensagem de checksum divergente e o ZIP local anterior (se existir) permanece intacto.

### FR-7 — Manter o ano mais recente atualizado

Ao rodar, o ETL consulta os cabeçalhos do ZIP do ano mais recente (hoje 2026) por GET em stream lendo só os cabeçalhos e fechando sem baixar o corpo (D-19). Considera mudado se `content-length` ou o `crc32c` de `x-goog-hash` (lido como em FR-6, D-28) diferem dos da linha de referência (`ok` ou `pulado`, D-26); se o cabeçalho não traz `crc32c=`, compara só o `content-length` e registra um aviso (D-29); `last-modified` só é registrado. Sem linha de referência e com ZIP local presente, carrega o ZIP local se o `content-length` do Drive for igual ao tamanho local, senão baixa (D-24). Uma linha `erro` em `etl_log` nunca substitui essa referência (D-16, D-26). Quando um ano mais novo aparece, o ano anterior recebe uma última verificação de cabeçalhos, registrada com `fechado` = 1 na linha desse ano em `etl_log` só se os cabeçalhos foram lidos com sucesso. Um ano é fechado se existe qualquer linha `ok` ou `pulado` dele com `fechado` = 1, e as linhas seguintes do ano repetem a marca (D-27); a partir daí não é mais consultado no Drive. Se a leitura falhar, `fechado` não é gravado e a verificação se repete na próxima execução (D-22, D-26, D-27). `--force` recarrega o ano mais recente sem comparar e aceita downloads sem `crc32c=` (FR-6, D-29). Não há agendador. (UC-2, D-4)

- **AC-13** — Given o 2026 já carregado e o Drive com os mesmos `content-length` e `x-goog-hash`, when o ETL roda, then não baixa o ZIP e o banco fica igual.
- **AC-14** — Given o Drive com `x-goog-hash` diferente do registrado, when o ETL roda, then baixa o ZIP e recarrega o ano 2026 (FR-4), registrando os novos cabeçalhos.
- **AC-15** — Given `--force`, when o ETL roda, then recarrega o 2026 mesmo com cabeçalhos iguais.
- **AC-30** — Given nenhuma carga `ok` de 2026 e o ZIP local de 7 716 046 bytes, when o Drive anuncia `content-length` 7 716 046, then carrega o ZIP local sem baixar; e quando anuncia outro valor, então baixa e carrega o do Drive.
- **AC-31** — Given uma execução em que o 2026 falhou (linha `erro` com cabeçalhos novos), when o ETL roda de novo, then compara com os cabeçalhos da última linha `ok` ou `pulado` (não com os da linha `erro`) e tenta recarregar.
- **AC-32** — Given só o `last-modified` diferente (`content-length` e `crc32c` iguais), when o ETL roda, then não baixa o ZIP e registra o novo `last-modified`.
- **AC-33** — Given 2026 carregado e a página listando também 2027, when o ETL roda, then baixa e carrega o 2027 (FR-6), consulta uma última vez os cabeçalhos do 2026 (recarrega se mudaram), grava `fechado` = 1 na linha do 2026 em `etl_log` e nas execuções seguintes 2026 não é mais consultado no Drive.
- **AC-39** — Given 2026 com uma linha `ok` com `fechado` = 1 e, depois, uma execução que gravou `pulado` para 2026, when o ETL roda de novo, then a linha `pulado` repete `fechado` = 1 e o 2026 continua sem consulta ao Drive.
- **AC-41** — Given o Drive respondendo o 2026 sem `crc32c=` em `x-goog-hash`, o `content-length` igual ao da referência e sem `--force`, when o ETL roda, then não baixa o ZIP, registra o aviso de crc32c ausente e o banco fica igual; e com `content-length` diferente tenta baixar e falha com a mensagem do AC-38, sem alterar o ZIP local nem as linhas do ano.
- **AC-37** — Given 2027 listado na página e a leitura dos cabeçalhos do 2026 falhando por rede, when o ETL roda, then `fechado` do 2026 não é gravado, a falha é registrada, e na execução seguinte (rede ok) os cabeçalhos do 2026 são consultados de novo e `fechado` = 1 é gravado.

### FR-8 — Tolerar falha por arquivo e registrar

Erro de rede, cota, resposta HTML em vez de ZIP, ZIP inválido, ZIP sem exatamente um CSV ou CSV com cabeçalho diferente dos 37 campos em um ano é registrado com mensagem clara e não impede os outros anos. Cada execução deixa um registro por ano na tabela `etl_log` (ano, origem, status ∈ {`ok`, `pulado`, `erro`}, linhas, tamanho e sha256 do ZIP, cabeçalhos do Drive, `fechado` (D-27), mensagem, timestamp; D-26). O processo termina com código ≠ 0 se algum ano falhou. (UC-4, D-6, D-9, D-16, D-21, D-26)

- **AC-16** — Given o download de 2019 falha (HTTP 429) e os demais ok, when o ETL roda, then 2019 aparece em `etl_log` com status `erro` e a mensagem, os demais anos carregam, e o código de saída é ≠ 0.
- **AC-17** — Given um arquivo baixado que é HTML de confirmação/cota e não ZIP, when o ETL o valida, then falha o ano com mensagem "resposta não é ZIP" e não toca nas linhas já carregadas desse ano.
- **AC-18** — Given um CSV cujo cabeçalho difere dos 37 campos, when é lido, then falha o ano com a lista de colunas divergentes e não carrega nada desse ano.
- **AC-19** — Given um ZIP de 2020 com 0 CSVs e outro de 2021 com 2 CSVs, when o ETL roda, then os dois anos falham com mensagem "esperado 1 CSV, encontrado N" e as linhas já carregadas deles ficam intactas.

### FR-9 — Interface de linha de comando

O ETL roda por `python -m etl_prf`, com a opção `--force` (FR-7, FR-6, D-29). O banco é `data/prf.sqlite` (a pasta `data/` é criada se faltar) e os ZIPs baixados ficam na raiz do projeto. (UC-1, UC-2, D-23)

- **AC-34** — Given um checkout sem `data/`, when se roda `python -m etl_prf`, then cria `data/prf.sqlite` com `acidentes` e `etl_log`, e os ZIPs baixados (se houver) ficam na raiz.
- **AC-35** — Given todos os anos ok, when o ETL termina, then o código de saída é 0 e o resumo por ano é impresso (NFR-2).

### Non-functional requirements

| ID | Category | Requirement | How it is checked |
|---|---|---|---|
| NFR-1 | performance | Leitura em chunks de 100 mil linhas: pico de memória ≤ 1 GiB na carga completa dos 10 anos (~4,4 milhões de linhas) em execução local única; o tempo total só é reportado (D-20) | medição de pico de memória (RSS) na carga completa; falha se > 1 GiB |
| NFR-2 | observability | Cada execução imprime resumo por ano (linhas, status, origem: local/download/pulado) e usa `etl_log` | AC-16 e inspeção do log |
| NFR-3 | rede | Poucas requisições externas: 1 GET da página + 1 GET em stream (só cabeçalhos) do ano mais recente + downloads só do que falta | AC-12, AC-13 com contagem de requisições em teste |

---

## Constraints & dependencies

| Item | Kind | Owner | Impact if unmet |
|---|---|---|---|
| Página gov.br da PRF (HTML pode mudar) | dependency | PRF | crawler não acha links → fallback (AC-10) |
| Google Drive (`uc?export=download`, cota/confirmação de vírus) | dependency | Google | download falha → FR-8; cota só se observa em uso real (Q-6) |
| Python 3.14, pandas 3.0.5, requests, bs4 já instalados | constraint | usuário | ver D-1 |
| `crc32c` em Python puro (nenhuma lib instalada o calcula; ~2,7 s para 7,7 MB, A-2) | constraint | agente | sem nova dependência (D-25); ZIPs de 13 MB levam ~5 s, aceitável (NFR-1 só limita memória) |
| Citar a PRF como fonte; não atribuir à PRF dados alterados | constraint | usuário | risco de licença (CC BY-ND do portal, `reported`) |
| Execução local, sem orquestrador | constraint | usuário | — |

## Data sources

| Data source | Where it's defined | Relevant fields | Provenance | Evidence | Notes |
|---|---|---|---|---|---|
| ZIPs `acidentes<ano>_todas_causas_tipos.zip` (2017–2026) | raiz do projeto | 37 colunas iguais | confirmed | E-1 | 1 CSV por ZIP, cp1252, `;`; 4 423 078 linhas no total |
| Nulos | CSVs | `pesid`, `id_veiculo`, `br`, `km`, `idade`, `tipo_acidente`… | confirmed | E-1, A-1 | `NA`, `N/A` e string vazia (96 linhas em `tipo_acidente`, 2018–2020); nulos de pessoa/veículo são estruturais (~3–9%) |
| `id` em notação científica | CSVs 2018–2021, 2024 | `id` | confirmed | A-1 | 43 linhas como `1e+05`; só o primeiro exemplo por coluna foi visto (ver Risks) |
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
| Cabeçalhos do Drive | in | `content-length`, `last-modified`, `x-goog-hash: crc32c` (sem `ETag`); lidos por GET em stream sem baixar o corpo (HEAD não foi testado) | — | confirmed (GET em stream) | E-3 |
| `robots.txt` gov.br | out | sem regra para `/prf` | — | confirmed | E-5 |

## Impacts

- Página gov.br da PRF — só leitura, 1 requisição por execução (E-2).
- Google Drive — cabeçalhos do 2026 por execução; downloads só do que falta (E-3).
- ZIPs locais dos anos fechados (2017–2025) — só leitura, são a entrada padrão (E-1); um ZIP só é criado ou substituído por download validado (D-17).
- SQLite `data/prf.sqlite` (`acidentes` e `etl_log`) e os ZIPs baixados na raiz do projeto — únicos artefatos gravados (D-23).
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
- **D-7 — Anos 2017–2025 vêm dos ZIPs locais; baixa do Drive só o que faltar; só o 2026 é re-baixado quando muda (ano fechado × mais recente: ver D-22)** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, Q-5 e correção 2 do framing) · evidence: E-1, E-3
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

- **D-13 — `id` em notação científica (`1e+05`) é convertido para inteiro exato; só vira NULL se não for inteiro exato** · type: technical · decided-by: agent · evidence: A-1
  - Why: 43 linhas de 2018–2021 e 2024 trazem o `id` assim; `int()` direto falha e AC-6 zeraria o identificador da ocorrência.
  - Ruled out: `int(float(x))` — perde dígitos se a mantissa tiver mais de 15; deixar `id` como texto — o valor bruto `1e+05` não serve como chave.
- **D-14 — Marcadores de nulo: `NA`, `N/A` e string vazia; nenhum outro texto vira NULL** · type: technical · decided-by: agent · evidence: A-1, E-1
  - Why: `tipo_acidente` vem vazio em 96 linhas (2018–2020); o `na_values` padrão do pandas também trataria `NULL`, `nan`, `None` como nulos e alteraria texto legítimo.
  - Ruled out: `na_values` padrão do pandas — conjunto amplo e implícito; só `NA`/`N/A` — deixa `''` como texto.
- **D-15 — Tipos das 37 colunas e índices** · type: technical · decided-by: agent · evidence: A-1, E-1
  - Why: FR-3 tipa 6 colunas; `id`, `pesid`, `id_veiculo`, `ordem_tipo_acidente`, `ilesos`, `feridos_leves`, `feridos_graves` e `mortos` também parseiam como inteiro em todos os anos (A-1), o resto é texto. Índices em `ano`, `id` e `data_inversa` porque são 4,4 milhões de linhas e não há chave única (D-10).
  - Ruled out: tudo texto além das 6 colunas — empurra a conversão para as consultas; chave primária composta — as colunas da chave candidata aceitam NULL.
- **D-16 — "Ano inalterado" = impressão digital (tamanho + sha256) do ZIP da última carga `ok` em `etl_log`; o 2026 na primeira execução carrega o ZIP local sem baixar; os cabeçalhos do Drive de referência vêm da última linha `ok`, nunca de uma linha `erro`** · type: technical · decided-by: agent · evidence: E-3
  - Why: FR-4/AC-7 não definem o critério; sem isso uma falha grava cabeçalhos novos e o 2026 nunca recarrega. Refinado por D-26: a referência inclui as linhas `pulado`.
  - Ruled out: mtime — muda ao copiar o arquivo; contagem de linhas — não detecta correção de valores.
- **D-17 — Download vai para arquivo temporário, é validado (`content-length` e `crc32c` de `x-goog-hash`, além de ser ZIP) e só então substitui o ZIP local** · type: technical · decided-by: agent · evidence: E-3
  - Why: AC-17 só verifica se é ZIP; um download truncado ou interrompido corromperia o ZIP local existente.
  - Ruled out: gravar direto no destino — apaga o bom se falhar; validar só o formato ZIP — não pega truncamento com diretório central válido.
- **D-18 — Crawler mescla por ano: o link da página vence o ID do README; anos ausentes na página vêm do README; divergências são registradas** · type: technical · decided-by: agent · evidence: E-2
  - Why: AC-10 só cobre "nenhum link"; a PRF pode republicar um ano com ID novo ou a página vir incompleta.
  - Ruled out: fallback só com zero links — 9 de 10 links deixaria um ano sem fonte; README sempre vence — ignora ID novo.
- **D-19 — Sondagem do 2026: GET em stream lendo só cabeçalhos (como no E-3), fechando sem baixar o corpo; muda se `content-length` ou `crc32c` diferem; `last-modified` só é registrado** · type: technical · decided-by: agent · evidence: E-3
  - Why: só GET em stream foi testado; HEAD no Drive não foi verificado. `last-modified` pode mudar sem mudar o conteúdo.
  - Ruled out: HEAD — sem evidência; qualquer diferença de cabeçalho dispara — recarga sem necessidade.
- **D-20 — NFR-1: pico de memória ≤ 1 GiB com chunks de 100 mil linhas; tempo total só reportado** · type: technical · decided-by: agent · evidence: E-1
  - Why: NFR-1 não tinha limite verificável.
  - Ruled out: sem limite — não é checável; limite de tempo — depende da máquina.
- **D-21 — Validação de entrada: o ZIP deve ter exatamente 1 CSV, lido em stream sem extrair para disco; o ano vem do nome do ZIP; o ID do Drive extraído da página deve casar `^[A-Za-z0-9_-]{20,}$` antes de entrar na URL** · type: technical · decided-by: agent · evidence: E-2
  - Why: FR-8 não cobre ZIP com 0 ou vários CSVs; o ID vem de HTML externo e vai para uma URL.
  - Ruled out: extrair para disco — zip-slip e sobra de arquivo; confiar no ID da página — injeção de parâmetros na URL.

- **D-22 — O ano mais recente descoberto pelo crawler é o atualizável (detecção de mudança como o D-19); anos novos entram sozinhos; ao surgir um ano mais novo, o anterior recebe uma última verificação e passa a ser tratado como fechado** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, AU-5) · evidence: E-2, E-3
  - Why: o ETL não precisa de edição a cada janeiro.
  - Ruled out: 2026 fixo na configuração — exige mexer todo ano; conferir os dois últimos anos por mudança — mais requisições ao Drive.
- **D-23 — Interface: `python -m etl_prf`, SQLite em `data/prf.sqlite`, ZIPs baixados na raiz do projeto, opção `--force`** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, AU-11) · evidence: .gitignore
  - Why: `data/` já está no `.gitignore` e os ZIPs já ficam na raiz.
  - Ruled out: ZIPs em `data/` — muda o layout atual sem ganho.
- **D-24 — Sem carga `ok` do ano mais recente e com ZIP local: carrega o local se o `content-length` do Drive for igual ao tamanho local; senão baixa** · type: technical · decided-by: agent · evidence: E-3
  - Why: refina D-16 — evita baixar 7,7 MB à toa na primeira execução, sem esconder um ZIP local defasado.
  - Ruled out: confiar sempre no ZIP local — esconde defasagem; baixar sempre na primeira execução — requisição desnecessária.
- **D-25 — `crc32c` calculado em Python puro (implementação própria), sem nova dependência** · type: technical · decided-by: agent · evidence: A-2
  - Why: nenhuma lib instalada calcula crc32c; a versão em Python puro deu o mesmo valor do `x-goog-hash` do E-3 em 2,7 s para 7,7 MB.
  - Ruled out: adicionar `google-crc32c` — nova dependência para ganho pequeno; validar só tamanho e formato ZIP — não detecta corrupção com o mesmo tamanho.
- **D-26 — `etl_log`: `status` ∈ {`ok`, `pulado`, `erro`}; a referência de comparação (D-16) é a linha mais recente com status `ok` ou `pulado`, que repete o tamanho, o sha256 e os cabeçalhos da carga; a verificação final de um ano que virou fechado (D-22) é registrada na coluna `fechado` da linha e só quando os cabeçalhos foram lidos com sucesso; se falhar, é repetida na próxima execução** · type: technical · decided-by: agent · evidence: E-3
  - Why: a spec não define o vocabulário de `status` nem como AC-33 sabe que a última consulta do ano já ocorreu.
  - Ruled out: só `ok`/`erro` — uma execução que pulou o ano perderia a referência; inferir "fechado" do ano do arquivo — repetiria a consulta ao Drive sem fim.

- **D-27 — Um ano é fechado se existe qualquer linha `ok` ou `pulado` dele em `etl_log` com `fechado` = 1; as linhas seguintes do ano repetem a marca** · type: technical · decided-by: agent · evidence: —
  - Why: a referência é "a mais recente" (D-26) e o FR-4 grava uma linha `pulado` por execução; sem a regra, uma linha posterior perderia a marca e o ano voltaria a ser consultado no Drive (AC-33).
  - Ruled out: ler `fechado` só da linha mais recente — a marca se perde; tabela separada de anos fechados — complexidade sem ganho.
- **D-28 — `crc32c` de `x-goog-hash`: extrair o item `crc32c=`, decodificar de base64 (4 bytes big-endian) e comparar com o valor calculado como inteiro de 32 bits; cabeçalho sem `crc32c=` falha o download com mensagem clara** · type: technical · decided-by: agent · evidence: A-2, E-3
  - Why: E-3 mostra `zauaUg==`; o cabeçalho pode listar mais de um hash.
  - Refinado por D-29: `--force` aceita a ausência.
  - Ruled out: comparar a string inteira do cabeçalho — quebra com `md5=` extra; ignorar a ausência do `crc32c` — o download ficaria sem validação de conteúdo.

- **D-29 — Sem `crc32c=` em `x-goog-hash`: o download falha por padrão; com `--force` valida só `content-length` e conteúdo ZIP, com aviso no log e no resumo; a sondagem do ano mais recente compara só o `content-length`, com aviso** · type: product · decided-by: user (ebenezerdorneles, 2026-09-19, AU-23, opção c) · evidence: E-3
  - Why: integridade por padrão, com saída explícita se o Drive parar de enviar o hash. A regra da sondagem sem `--force` é consequência técnica da escolha: sem hash só se compara o tamanho, e um download que daí resulte falha sem `--force`.
  - Ruled out: (a) falhar sempre — o ETL para de carregar downloads até alguém intervir; (b) aceitar sempre sem hash — perde a validação de conteúdo sem o usuário saber.

---

## Risks & assumptions

| Item | Kind | Consequence if wrong | Mitigation / how it gets verified |
|---|---|---|---|
| A página da PRF muda o HTML | risk | crawler não acha links | fallback com IDs do README (AC-10) |
| Drive aplica cota/confirmação em ZIPs maiores (13 MB; só o 2026, 7,7 MB foi testado) | risk | download de ano faltante falha | FR-8, AC-17; verificado só em uso real |
| Licença CC BY-ND do portal e termos do Google (`reported`, não verificados) | assumption | restrição ao uso/republicação | D-12: uso interno; não republicar |
| O ano do arquivo local é o do nome do ZIP (`acidentes<ano>_…`) | assumption | recarga do ano errado | AC-1 e validação do nome do ZIP |
| Mudança de esquema em anos futuros (colunas novas) | risk | cabeçalho diferente dos 37 campos | AC-18 falha o ano com a lista de divergências |
| `id` como `1e+05` representa exatamente 100000 (só o primeiro exemplo por coluna foi visto, A-1) | assumption | `id` errado nessas 43 linhas | D-13 converte só inteiros exatos; o verify confere os valores convertidos contra o CSV |
| `x-goog-hash` pode listar vários hashes (`crc32c=...,md5=...`); só `crc32c=` sozinho foi observado (E-3) | assumption | download validado errado ou falha com "sem crc32c" | D-28: o parser separa por vírgula e ignora espaços; AC-38; `--force` como saída (D-29) |
| Sem `crc32c=` em `x-goog-hash`, a sondagem compara só o `content-length` (D-29, AC-41) | risk (AU-24) | correção da PRF que mantém o mesmo tamanho passa despercebida e o banco do ano mais recente fica defasado | aviso no log e no resumo; `--force` recarrega o ano mais recente |
| Duas execuções simultâneas disputam o SQLite | risk (aceito, AU-12) | a segunda falha com o banco bloqueado, sem corromper (cada ano é uma transação, FR-4) | sem trava extra; usar uma execução por vez |
| `Last-Modified`/`x-goog-hash` reflete mudança do conteúdo | assumption | 2026 não é atualizado ou é recarregado sem necessidade | E-3 confirma que os cabeçalhos existem; `--force` como saída |

## Security & privacy

O banco contém dados por pessoa anonimizados (`pesid`, `idade`, `sexo`, veículo). Não há credenciais nem autenticação. O banco fica local, tratado como interno (D-12); o repositório não deve receber o `.sqlite` nem os ZIPs (ignorar via `.gitignore`); logs e `etl_log` não gravam valores de linhas, só contagens e mensagens.

## Migration & rollout

Banco novo: sem migração de dados. A primeira execução cria `data/prf.sqlite` e as tabelas e carrega os 10 anos (D-23). Reversão: apagar `data/prf.sqlite` e reexecutar (nada externo é escrito; ZIPs baixados ficam na raiz).

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
| 6 | ebenezerdorneles | 2026-09-19 | Audit — rev 6 — 2026-09-19 | aprovação explícita da rev 6; riscos aceitos: AU-12, AU-21, AU-24 |

---

## Revisions

| Rev | Date | Issue | Trigger | Ids and sections changed |
|---|---|---|---|---|
| 1 | 2026-09-19 | — | initial; addendum 2026-09-19 (Q-1..Q-6, exploration `Affects spec: yes`) | todas as seções |
| 2 | 2026-09-19 | — | audit AU-1..AU-14 (D-13..D-23) | Goals, Scope/UC coverage; FR-1..FR-8 reescritos, novo FR-9; AC-19..AC-35 novos, AC-10 alterado; NFR-1, NFR-3; Data sources, Interfaces, Impacts, Risks, Migration; D-7 (nota), novo D-24 |
| 3 | 2026-09-19 | — | audit AU-16..AU-18 (D-25, D-26) | FR-4 (referência `ok`/`pulado`), AC-7, AC-24; FR-6, novo AC-36; FR-7, AC-31, AC-33, novo AC-37; FR-8 (vocabulário e coluna `fechado` de `etl_log`); Constraints & dependencies; D-16 (nota) |
| 4 | 2026-09-19 | — | audit AU-19, AU-20 (D-27, D-28) | FR-6 (formato de `x-goog-hash`), novos AC-38; FR-7 (regra de `fechado`, leitura do crc32c), novo AC-39; FR-8 (`fechado`) |
| 5 | 2026-09-19 | — | audit AU-22, AU-23 (D-29; AU-23 opção (c) decidida pelo usuário) | FR-6 (`--force` sem `crc32c=`), AC-38 (ajuste), novo AC-40; FR-7 (sondagem sem `crc32c=`, `--force`), novo AC-41; FR-9; Risks & assumptions (formato de `x-goog-hash`); D-28 (nota), novo D-29 |
| 6 | 2026-09-19 | — | audit AU-24 | Risks & assumptions (nova linha de risco); nenhuma FR/AC/D alterada |

---

## Feedback

<!-- Audit sections ("## Audit — rev <n> — YYYY-MM-DD") are appended below by the audit skill. -->

## Audit — rev 1 — 2026-09-19

| ID | Item | Type | Severity | Resolution | Status | Decided by | Decision | Evidence |
|----|------|------|----------|------------|--------|------------|----------|----------|
| AU-1 | `id` vem em notação científica (`1e+05`) em 43 linhas de 2018–2021 e 2024; FR-3 não tipa `id` e AC-6 o deixaria NULL | data | high | technical | resolved | agent | D-13; FR-3, AC-20, AC-21 | A-1 |
| AU-2 | `tipo_acidente` vazio (96 linhas, 2018–2020) é um 3º marcador de nulo que FR-3 não cita; o `na_values` padrão do pandas (D-1) também converteria `NULL`/`nan` | data | high | technical | resolved | agent | D-14; FR-3, AC-22 | A-1, E-1 |
| AU-3 | Métricas `idade_nonnum`/`ano_fab_nonnum` do E-1 estão erradas (regex escapado no f-string: 342497−57577 = 284920); a tipagem de `idade`/`ano_fabricacao_veiculo` não estava verificada | coverage | medium | technical | resolved | agent | A-1 refez a checagem: 0 valores não parseáveis nessas colunas em todos os anos; nenhuma mudança de spec | A-1, E-1 |
| AU-4 | FR-3 tipa 6 das 37 colunas; `id`, `pesid`, `id_veiculo`, `ilesos`… ficam sem tipo (decisão implícita); não há índice nem chave em 4,4 milhões de linhas | decision | high | technical | resolved | agent | D-15; FR-2, FR-3, AC-23 | A-1 |
| AU-5 | Só o 2026 é atualizável e o intervalo 2017–2026 está fixo nos AC; quando a PRF publicar o 2027 (ou fechar o 2026) a spec não diz o que acontece | edge | high | product | resolved | user (ebenezerdorneles) | D-22; FR-1, FR-5, FR-6, FR-7, AC-33 (ver AU-17) | E-2, E-3 |
| AU-6 | "Ano inalterado" (FR-4/AC-7) não tem critério para ZIPs locais; na 1ª execução o 2026 não tem cabeçalhos registrados; uma linha `erro` pode sobrescrever a referência | edge | high | technical | resolved | agent | D-16, D-24; FR-4, FR-7, AC-24, AC-30, AC-31 (ver AU-17) | E-3 |
| AU-7 | Download só é validado como ZIP (AC-17); truncamento não é detectado e pode sobrescrever o ZIP local bom | contract | medium | technical | resolved | agent | D-17; FR-6, AC-25, AC-26 (ver AU-16) | E-3 |
| AU-8 | Crawler: AC-10 só cobre "nenhum link"; página com 9 de 10 anos ou ID diferente do README não tem regra | contract | medium | technical | resolved | agent | D-18; FR-5, AC-27, AC-28 | E-2 |
| AU-9 | FR-7 cita "HEAD/GET" mas só GET em stream foi testado (E-3); não diz qual cabeçalho dispara a recarga; ZIPs maiores que 7,7 MB nunca foram baixados | contract | medium | technical | resolved | agent | D-19; FR-7, NFR-3, AC-32 | E-3 |
| AU-10 | NFR-1 não tem limite verificável ("reportar no verify") | quality | medium | technical | resolved | agent | D-20; NFR-1 | E-1 |
| AU-11 | Interface do usuário não definida: nome do comando, caminho do SQLite, pasta dos ZIPs baixados, `--force` | quality | medium | product | resolved | user (ebenezerdorneles) | D-23; FR-9, AC-34, AC-35 | — |
| AU-12 | Duas execuções simultâneas disputam o mesmo SQLite (bloqueio do banco na recarga por ano) | edge | low | technical | accepted-risk | agent | linha em Risks & assumptions (rev 2); consequência: a segunda execução falha com o banco bloqueado, sem corromper | — |
| AU-13 | ZIP com 0 ou vários CSVs, ou nome fora do padrão, não tem tratamento em FR-8; FR-1 diz "extrair" o CSV (zip-slip, sobra em disco) | edge | low | technical | resolved | agent | D-21; FR-1, FR-8, AC-19 | E-1 |
| AU-14 | O ID do Drive vindo do HTML vai direto para a URL sem validação | contract | low | technical | resolved | agent | D-21; FR-5, AC-29 | E-2 |
| AU-15 | Exploração cita "agendador" como ator do UC-2, mas o agendamento está fora do escopo (D-4) | quality | low | technical | invalid | agent | só rótulo de ator; a spec já cobre o UC-2 com comando manual (FR-7) | — |

## Audit — rev 2 — 2026-09-19

Delta audit: FR-1..FR-9, AC-19..AC-35, D-13..D-24, NFR-1/NFR-3 e as seções tocadas pela rev 2. Os itens AU-1..AU-14 da rev 1 foram conferidos contra o texto novo (status atualizados acima).

| ID | Item | Type | Severity | Resolution | Status | Decided by | Decision | Evidence |
|----|------|------|----------|------------|--------|------------|----------|----------|
| AU-16 | D-17/FR-6/AC-26 exigem conferir o `crc32c`, mas nenhuma lib instalada nem a biblioteca padrão o calcula, e "Constraints" só lista pandas, requests e bs4 | contract | medium | technical | resolved | agent | D-25; FR-6, AC-36, Constraints & dependencies (rev 3; vetor `0xE3069283` conferido no delta audit) | A-2 |
| AU-17 | AC-33 diz que o ano fechado "não é mais consultado", mas não há onde registrar que a verificação final ocorreu; se ela falhar por rede o ano ficaria sem última verificação ou seria consultado para sempre | edge | medium | technical | resolved | agent | D-26; FR-7, AC-33, AC-37, FR-8 (rev 3; a regra de leitura de `fechado` foi refinada em AU-19) | E-3 |
| AU-18 | `etl_log` não define os valores de `status`; FR-4/FR-7 comparam com "a última carga `ok`", mas uma execução que pulou o ano (AC-7) não é `ok` nem `erro` | quality | medium | technical | resolved | agent | D-26; FR-4, FR-8, AC-7, AC-24, AC-31 (rev 3) | — |

## Audit — rev 3 — 2026-09-19

Delta audit: FR-4, FR-6, FR-7, FR-8, AC-7, AC-24, AC-31, AC-33, AC-36, AC-37, D-16 (nota), D-25, D-26 e a linha nova de Constraints. AU-16..AU-18 conferidos contra o texto novo (status atualizados acima). Conferido: o CRC-32C de `b"123456789"` em Python puro dá `0xe3069283`, igual ao AC-36; o ZIP 2026 local tem 7 716 046 bytes, igual ao AC-30/A-2.

| ID | Item | Type | Severity | Resolution | Status | Decided by | Decision | Evidence |
|----|------|------|----------|------------|--------|------------|----------|----------|
| AU-19 | FR-7/D-26 gravam `fechado` "na linha" do ano, mas não dizem como é lido: o FR-4 grava uma linha `pulado` por ano a cada execução e a referência é "a mais recente", então uma linha `pulado` posterior (sem `fechado`) ou uma recarga poderia apagar a marca e o ano fechado voltaria a ser consultado no Drive (contra AC-33) | edge | medium | technical | resolved | agent | D-27; FR-7, FR-8, AC-39 (rev 4) | — |
| AU-20 | FR-6/AC-36 comparam o `crc32c` com `x-goog-hash`, mas não dizem o formato: o cabeçalho traz o valor em base64 dos 4 bytes big-endian (`zauaUg==` no E-3) e pode listar mais de um hash (`crc32c=...,md5=...`); sem a regra, o teste do AC-26 e a implementação divergem | contract | low | technical | resolved | agent | D-28; FR-6, FR-7, AC-38 (rev 4; `0xCDAB9A52` conferido no delta audit; ver AU-22) | A-2, E-3 |
| AU-21 | Cada execução grava uma linha `pulado` por ano em `etl_log` (~10 linhas por execução, sem limpeza) | quality | low | technical | accepted-risk | agent | crescimento desprezível (poucas centenas de bytes por execução); sem rotação | — |

Pressure-test: as decisões D-25 e D-26 não mudam formato externo nem dado armazenado de forma irreversível (a coluna `fechado` é interna e o banco é descartável, ver Migration & rollout), então o eixo 8 não se aplica. A alternativa `google-crc32c` segue descartada (nenhuma edge nova a favorece); ~5 s de crc32c para um ZIP de 13 MB só ocorre em download.

## Audit — rev 4 — 2026-09-19

Delta audit: FR-6 (leitura de `x-goog-hash`), FR-7 (regra de `fechado`), FR-8, AC-38, AC-39, D-27, D-28. AU-19 e AU-20 conferidos contra o texto novo (status atualizados acima): AC-39 cobre a marca que se repete em `pulado`; a decodificação base64 de `zauaUg==` dá `cdab9a52`, igual ao AC-38.

| ID | Item | Type | Severity | Resolution | Status | Decided by | Decision | Evidence |
|----|------|------|----------|------------|--------|------------|----------|----------|
| AU-22 | D-28/AC-38 partem de que `x-goog-hash` pode listar vários hashes (`crc32c=...,md5=...`), mas o E-3 só observou `crc32c=zauaUg==` sozinho; o `md5=abc` do AC-38 é um exemplo inventado e o formato com vários itens (e o espaço após a vírgula quando o `requests` junta cabeçalhos repetidos) não está `confirmed` nem em Risks & assumptions | data | low | technical | resolved | agent | Risks & assumptions, linha do formato de `x-goog-hash` (rev 5); parser em D-28 e AC-38 | E-3 |
| AU-23 | FR-6/D-28 falham o download quando `x-goog-hash` não traz `crc32c=`, e o FR-7 não diz o que a sondagem do 2026 faz nesse caso; se o Drive parar de enviar o hash, o ano mais recente e qualquer ano novo nunca carregam (falha em todas as execuções, só `--force` também falharia na validação) | contract | medium | product | resolved | user (ebenezerdorneles, 2026-09-19) | D-29 (opção c); FR-6, FR-7, FR-9, AC-38, AC-40, AC-41 (rev 5) | E-3 |

Pressão de arquitetura (eixo 8): não se aplica, sem dado irreversível nem contrato novo. AC-38 e AC-39 são checáveis com valores concretos (cabeçalho e hex de teste, sequência `ok`/`pulado`).

## Audit — rev 5 — 2026-09-19

Delta audit: FR-6, FR-7, FR-9, AC-38, AC-40, AC-41, D-28 (nota), D-29 e a linha nova de Risks & assumptions. AU-22 e AU-23 conferidos contra o texto novo (status atualizados acima). D-29 é `product` e foi decidida pelo usuário; AC-40 e AC-41 são checáveis com valores concretos (cabeçalho sem `crc32c=`, `content-length` igual/divergente, com e sem `--force`).

| ID | Item | Type | Severity | Resolution | Status | Decided by | Decision | Evidence |
|----|------|------|----------|------------|--------|------------|----------|----------|
| AU-24 | Sem `crc32c=` a sondagem do 2026 compara só o `content-length` (D-29, AC-41): uma correção da PRF que mantenha o tamanho não é detectada e o banco fica defasado, apenas com o aviso no log; o risco não está em Risks & assumptions | edge | low | technical | resolved | agent | Risks & assumptions, linha `risk (AU-24)` (rev 6) | E-3 |

Pressão de arquitetura (eixo 8): não se aplica, sem dado irreversível nem contrato novo. Nada mais a apontar: `--force` só dispensa a *ausência* do `crc32c=`; um `crc32c` presente e divergente continua falhando (AC-26), e o AC-40 mantém a checagem de tamanho.

## Audit — rev 6 — 2026-09-19

Delta audit: só a linha nova de Risks & assumptions (AU-24); a rev 6 não alterou FR, AC nem D (conferido na linha de Revisions). A linha traz a consequência e a mitigação (aviso e `--force`) e cita D-29 e AC-41. AU-24 marcado `resolved`. Nenhum item novo.

Estado de saída: todos os itens AU-1..AU-24 estão `resolved`, `accepted-risk` (AU-12, AU-21) ou `invalid` (AU-15); zero `open`; Q-1..Q-6 resolvidas; sem CR aberto.

