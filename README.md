# DADOS ABERTOS DA PRF

## Link da Pagina:
    - https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf

## Links dos arquivos CSV:
1 - Documento CSV de Acidentes 2026 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/1EsGox0UnBWSaM6mrkNSUlYUOecubLCsh/view?usp=sharing/download
2 - Documento CSV de Acidentes 2025 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/1-PJGRbfSe7PVjU37A3wTCls_NRXyVGRD/view?usp=sharing/download
3 - Documento CSV de Acidentes 2024 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/14qBOhrE1gioVtuXgxkCJ9kCA8YtUGXKA/view?usp=sharing/download
4 - Documento CSV de Acidentes 2023 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/1-caam_dahYOf2eorq4mez04Om6DD5d_3/view?usp=sharing/download
5 - Documento CSV de Acidentes 2022 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/1wskEgRC3ame7rncSDQ7qWhKsoKw1lohY/view?usp=sharing/download
6 - Documento CSV de Acidentes 2021 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/1Gk3U6cMOZIevsDZHLi6J503xoCRS_lnI/view?usp=drive_link/download
7 - Documento CSV de Acidentes 2020 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/1yQtVOsAlupPHQVVTmbJo0NR3XMzgHANO/view?usp=sharing/download
8 - Documento CSV de Acidentes 2019 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/1DAJYKVfkTcPhQodSmHp9rsG1Q8XJW-m3/view?usp=drive_link/download
9 - Documento CSV de Acidentes 2018 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/1J-012nSnIafOASNFvIYY_vDKKpM51w5_/view?usp=drive_link/download
10 - Documento CSV de Acidentes 2017 (Agrupados por pessoa - Todas as causas e tipos de acidentes)
    - https://drive.google.com/file/d/1Kv5mNgZvxtl0xwqsmDrxcaLY2KELxR-3/view?usp=drive_link/download

## OBJETIVO:
    - Criar um processo de ETL (Extract, Transform, Load) para processar os arquivos CSV e gerar relatórios mensais de acidentes de trânsito em todas as rodovias federais e estados do Brasil, entre os anos de 2017 e 2026 (sem filtro por BR ou UF).
    - Gerar um banco de dados SQLite com a tabela `acidentes` com o historico de acidentes de transito de todas as BRs e UFs do Brasil, entre os anos de 2017 e 2026 (sem filtro por BR ou UF).

## Processo:
    - O processo deve ser executado em lote, processando um arquivo CSV por vez.
    - Para cada arquivo Zip, deve-se:
        - Extrair o arquivo CSV.
        - Ler o arquivo CSV.
        - Identificar o tipo de cada coluna e os dados.
        - Tratar os dados (valores ausentes, formatos, etc).
        - Não omitir linhas que contenham valores ausentes nas colunas de interesse.
        - Transformar os dados no formato desejado.
        - Inserir os dados no banco de dados SQLite. 
        - O campos são os mesmos descritos em [[Dicionário de Variáveis_ocorrencia_2017.pdf]]

## Obrigatório:
    - Fazer a extração das tasbelas pelo site como um web crawler.
    - O crawler deve:
        - Acessar a pagina com o link: https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf
        - Identificar os links de download dos arquivos CSV.
        - Baixar os arquivos CSV.
        - Processar os arquivos CSV.
    - Ou baixar os arquivos CSV individualmente e processá-los.
    - validação de erro a acessar os links deve ser feita.
    
