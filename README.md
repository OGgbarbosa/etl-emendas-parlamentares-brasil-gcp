# Projeto de Análise de Emendas Parlamentares (ETL no GCP)

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow?style=for-the-badge&logo=git)
![Python](https://img.shields.io/badge/python-3.12-blue?style=for-the-badge&logo=python)
![GCP](https://img.shields.io/badge/Google%20Cloud-BigQuery%20%7C%20GCS-red?style=for-the-badge&logo=google-cloud)
![Polars](https://img.shields.io/badge/Polars-2.0-blueviolet?style=for-the-badge&logo=polars)

Pipeline de Engenharia de Dados de alta performance para extração, tratamento, enriquecimento e carga analítica dos dados abertos de **Emendas Parlamentares do Brasil**, utilizando a plataforma **Google Cloud Platform (GCP)** com processamento vetorizado em memória via **Polars**.

---

## 🎯 Objetivo

Construir um pipeline ETL/ELT robusto e resiliente seguindo o padrão **Medallion Architecture**:
1. **Raw (0_raw)**: Ingestão de dados brutos tabulares em formato CSV (`ISO-8859-1` / `UTF-8`).
2. **Bronze (1_bronze)**: Conversão para formato colunar Parquet em memória, sanitização de cabeçalhos (`snake_case`), injeção de metadados de auditoria (`_ingestion_timestamp` e `_source_file`) e arquivamento seguro no **Google Cloud Storage (GCS)**.
3. **Silver (2_silver)**: Modelagem dimensional analítica em padrão **Star Schema**, garantindo integridade referencial, tratamento de sentinelas, engenharia de atributos geográficos e temporais, e carga direta em **tabelas nativas gerenciadas no BigQuery**:
   - `fato_emendas`: Fato orçamentária consolidando dotações das emendas com 6 métricas monetárias (empenhado, liquidado, pago, restos a pagar inscritos/cancelados/pagos), autor, ano, classificação funcional e localização.
   - `fato_convenios`: Fato analítica tratando a relação $N:N$ entre emendas e instrumentos contratuais com valores alocados.
   - `fato_favorecidos`: Fato periódica mensal acumulada de transferências e pagamentos diretos por favorecido (CNPJ/CPF/Órgão).
4. **Gold (3_gold)**: Data Marts analíticos em SQL materializados no **Google BigQuery** e camada de **Views Semânticas** preparadas para consumo analítico e inteligência artificial.
5. **Web Scraping & Contexto Não-Estruturado**: Ingestão de artigos, notícias e observatórios cívicos para enriquecimento qualitativo das análises.
6. **Consumo Inteligente & Visualização**: Agente conversacional Gemini com RAG Híbrido no **Google Cloud Vertex AI** e portal analítico interativo em **Streamlit**.

---

## 🏗️ Arquitetura de Dados

```mermaid
flowchart TD
    subgraph RawZone ["0_raw (Local / Landing)"]
        CSV_E["EmendasParlamentares.csv"]
        CSV_C["EmendasParlamentares_Convenios.csv"]
        CSV_F["EmendasParlamentares_PorFavorecido.csv"]
    end

    subgraph BronzeZone ["1_bronze (GCS Lake)"]
        B_E["EmendasParlamentares.parquet"]
        B_C["EmendasParlamentares_Convenios.parquet"]
        B_F["EmendasParlamentares_PorFavorecido.parquet"]
    end

    subgraph Processing ["Processamento Polars (In-Memory)"]
        Proc_E["silver_emendas.py"]
        Proc_C["silver_convenios.py"]
        Proc_F["silver_favorecidos.py"]
    end

    subgraph DWH_Silver ["2_silver (BigQuery Managed Tables)"]
        S_EMENDA["fato_emendas (Orçamento Macro)"]
        S_CONV["fato_convenios (Instrumentos N:N)"]
        S_FAV["fato_favorecidos (Execução Favorecidos)"]
    end

    subgraph DWH_Gold ["3_gold (BigQuery Data Marts & Views)"]
        G_PARL["gold_execucao_parlamentar"]
        G_GEO["gold_distribuicao_geografica"]
        G_POL["gold_politicas_publicas"]
        G_FAV["gold_ranking_favorecidos"]
        G_VIEW["view_ai_* (Views Semânticas)"]
    end

    subgraph Web_Scraping ["Web Scraping & Contexto (GCS)"]
        W_NEWS["Artigos & Notícias (Folha, EBC, Senado, Transparência)"]
        W_DASH["Central das Emendas (##DASHBOARD)"]
    end

    subgraph Intelligence ["Google Cloud Vertex AI (RAG Híbrido)"]
        V_AGENT["Agente Gemini (Orquestrador)"]
        V_STORE_BQ["Data Store 1: BigQuery Views"]
        V_STORE_GCS["Data Store 2: Notícias GCS"]
    end

    subgraph Frontend ["Visualização Analítica"]
        APP["App Streamlit (Portal Multi-Páginas)"]
    end

    CSV_E --> B_E
    CSV_C --> B_C
    CSV_F --> B_F

    B_E --> Proc_E --> S_EMENDA
    B_C --> Proc_C --> S_CONV
    B_F --> Proc_F --> S_FAV

    S_EMENDA & S_CONV & S_FAV --> G_PARL & G_GEO & G_POL & G_FAV --> G_VIEW

    G_VIEW --> V_STORE_BQ --> V_AGENT
    W_NEWS & W_DASH --> V_STORE_GCS --> V_AGENT

    G_PARL & G_GEO & G_POL & G_FAV --> APP
    V_AGENT --> APP
```

---

## ⚙️ Stack Tecnológica

- **Linguagem & Processamento:** Python 3.12, [Polars](https://pola.rs/) (processamento colunar vetorizado em memória), `pandas`.
- **Nuvem & Armazenamento (GCP):**
  - **Google Cloud Storage (GCS):** Data Lake Bronze (arquivos brutos otimizados em Parquet Snappy).
  - **Google BigQuery:** Data Warehouse analítico (tabelas nativas gerenciadas na camada Silver).
- **Gerenciador de Ambientes & Pacotes:** [uv](https://docs.astral.sh/uv/) (execução rápida com lockfile reproduzível).
- **Linter & Formatador:** [Ruff](https://docs.astral.sh/ruff/) (padronização de código com limite de 120 caracteres).
- **Testes Automatizados:** [Pytest](https://pytest.org/) com mocks completos para APIs de nuvem (GCS e BigQuery).

---

## 📂 Estrutura do Projeto

```text
projeto_emendas/
├── .github/workflows/
│   └── ci_cd.yml                      # Pipeline de CI/CD (Ruff + Pytest)
├── pyproject.toml                     # Metadados, dependências, ruff e pytest configs
├── uv.lock                            # Lockfile reproduzível do uv
├── .env                               # Variáveis de ambiente (ignorado no git)
├── app/                               # Aplicação Web Streamlit (Multi-páginas)
│   ├── Home.py                        # Ponto de entrada e visão geral do portal
│   └── pages/
│       ├── 1_📊_Visao_Geral.py        # KPIs macro e métricas orçamentárias
│       ├── 2_🏛️_Parlamentares.py       # Raio-X por deputado e senador
│       ├── 3_🗺️_Mapa_Brasil.py         # Distribuição geográfica e municipal
│       ├── 4_🏢_Beneficiarios.py       # Maiores recebedores e fornecedores
│       └── 5_🤖_Assistente_IA.py       # Chatbot interativo com Gemini (Vertex AI)
├── database/                          # Dados brutos CSV locais (Portal da Transparência)
├── database_sample/                   # Amostras reduzidas para execução de testes em CI
├── data/
│   ├── bronze/                        # Parquets intermediários gerados da camada Bronze
│   ├── silver/                        # Parquets gerados da Silver (fato_emendas, fato_convenios, fato_favorecidos)
│   └── gold/                          # Diretório reservado para artefatos compilados da Gold
├── sql/
│   └── gold/                          # Scripts SQL dos Data Marts materializados no BigQuery
│       ├── gold_execucao_parlamentar.sql
│       ├── gold_distribuicao_geografica.sql
│       ├── gold_politicas_publicas.sql
│       ├── gold_ranking_favorecidos.sql
│       └── gold_painel_convenios.sql
├── notebooks/
│   └── projeto_inicial.ipynb          # Explorações interativas e prototipação de regras
├── src/
│   └── etl_emendas_parlamentares/
│       ├── __init__.py
│       ├── pipeline.py                # Orquestração do pipeline ponta a ponta
│       ├── config/
│       │   └── config.py              # Definições de caminhos, datasets e prefixos
│       ├── conexao/
│       │   └── big_query.py           # Conexão autenticada ao BigQuery e Storage via Service Account
│       ├── ingestao/
│       │   ├── upload_bronze.py       # Ingestão de arquivos Parquet no GCS
│       │   └── upload_silver.py       # Carga direta em tabelas nativas gerenciadas no BigQuery
│       ├── processamento/
│       │   ├── csv_parquet.py         # Conversão de CSV para Parquet com injeção de auditoria
│       │   ├── normalizar.py          # Normalização de nomes de colunas (snake_case)
│       │   ├── silver_emendas.py      # Modelagem da fato_emendas com métricas orçamentárias
│       │   ├── silver_convenios.py    # Modelagem N:N da fato_convenios com tipagem monetária
│       │   └── silver_favorecidos.py  # Modelagem periódica da fato_favorecidos com datas mensais
│       └── scraping/
│           ├── __init__.py
│           └── fontes.py              # Mapeamento das fontes de notícias e observatórios
└── tests/
    ├── conftest.py                    # Fixtures e configurações globais do Pytest
    ├── test_csv_parquet.py            # Testes de conversão CSV -> Parquet
    ├── test_normalizar.py             # Testes de sanitização de strings e colunas
    ├── test_pipeline.py               # Testes de orquestração do pipeline
    ├── test_silver_emendas.py         # Testes de regras de negócio, métricas e fallback de fato_emendas
    ├── test_silver_convenios.py       # Testes de regras N:N e tipagens de fato_convenios
    ├── test_silver_favorecidos.py     # Testes de regras temporais e métricas de fato_favorecidos
    ├── test_upload_bronze.py          # Testes de envio para o Cloud Storage
    └── test_upload_silver.py          # Testes de carga nativa no BigQuery
```

---

## 🔑 Variáveis de Ambiente (`.env`)

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```dotenv
GCP_PROJECT_ID="seu-projeto-gcp-id"
GCS_BUCKET_NAME="gs://seu-bucket-landing"
GOOGLE_APPLICATION_CREDENTIALS="gcp-credentials.json"
```

> [!IMPORTANT]
> O arquivo `gcp-credentials.json` e o `.env` contêm credenciais confidenciais e estão configurados no `.gitignore` para nunca serem versionados.

---

## 🚀 Como Executar

### 1. Preparação do Ambiente Local com `uv`

1. Instale o [uv](https://docs.astral.sh/uv/):
   ```bash
   pip install uv
   # ou via winget (Windows): winget install astral-sh.uv
   ```
2. Instale as dependências e crie o ambiente virtual automaticamente:
   ```bash
   uv sync
   ```

### 2. Execução dos Testes e Validação de Código

- Rodar suíte completa de testes unitários (35 testes):
  ```bash
  uv run pytest
  ```
- Rodar o linter:
  ```bash
  uv run ruff check .
  ```
- Verificar a formatação:
  ```bash
  uv run ruff format --check .
  ```

### 3. Execução do Pipeline

- **Executar Pipeline Completo (Raw -> Bronze -> Silver)**:
  ```bash
  uv run python src/etl_emendas_parlamentares/pipeline.py
  ```

- **Executar Módulos Individualmente**:
  - *Processar CSVs brutos para Parquet (Raw)*:
    ```bash
    uv run python src/etl_emendas_parlamentares/processamento/csv_parquet.py
    ```
  - *Enviar Parquets para a camada Bronze no Cloud Storage*:
    ```bash
    uv run python src/etl_emendas_parlamentares/ingestao/upload_bronze.py
    ```
  - *Processar fato de emendas orçamentárias (`fato_emendas`)*:
    ```bash
    uv run python src/etl_emendas_parlamentares/processamento/silver_emendas.py
    ```
  - *Processar fato de convênios (`fato_convenios`)*:
    ```bash
    uv run python src/etl_emendas_parlamentares/processamento/silver_convenios.py
    ```
  - *Processar fato de favorecidos (`fato_favorecidos`)*:
    ```bash
    uv run python src/etl_emendas_parlamentares/processamento/silver_favorecidos.py
    ```
  - *Carregar todas as tabelas da Silver no BigQuery nativo*:
    ```bash
    uv run python src/etl_emendas_parlamentares/ingestao/upload_silver.py
    ```

---

## 🗺️ Roadmap de Evolução

O projeto segue um plano de evolução estruturado para expandir a maturidade analítica e incorporar capacidades avançadas de Inteligência Artificial:

- [x] **Camada Bronze (1_bronze):** Ingestão, auditoria e arquivamento colunar Parquet no Google Cloud Storage (GCS).
- [x] **Camada Silver (2_silver):** Modelagem dimensional Star Schema completa (`fato_emendas`, `fato_convenios` e `fato_favorecidos`) com carga direta em tabelas nativas gerenciadas no BigQuery.
- [ ] **Camada Gold (3_gold - Em Andamento):**
  - [x] Definição arquitetural dos Data Marts via SQL padronizado no BigQuery.
  - [ ] Implementação e validação dos scripts analíticos em `sql/gold/`:
    - `gold_execucao_parlamentar.sql` (visão parlamentar e taxas de execução)
    - `gold_distribuicao_geografica.sql` (visão territorial por UF e municípios)
    - `gold_politicas_publicas.sql` (visão setorial por função e subfunção)
    - `gold_ranking_favorecidos.sql` (maiores fornecedores, ONGs e entidades)
    - `gold_painel_convenios.sql` (descentralização e instrumentos federais)
  - [ ] Camada de Views Semânticas de Consumo com metadados para IA (`view_ai_*`).
- [ ] **Camada de Web Scraping & Contexto Não-Estruturado:**
  - [x] Mapeamento das 6 fontes (Folha de S.Paulo, Agência Brasil/EBC, Agência Senado, Central das Emendas `##DASHBOARD`, Portal da Transparência, Transparência Brasil).
  - [ ] Esteira de scraping para captura de notícias e armazenamento em `gs://.../raw/scraping/`.
- [ ] **Camada de Consumo Inteligente (Google Cloud Vertex AI):**
  - [ ] RAG Híbrido no **Vertex AI Agent Builder** integrando BigQuery (dados oficiais auditáveis) e Cloud Storage (artigos e notícias de contexto).
  - [ ] **Agente Gemini:** Interface conversacional em linguagem natural com raciocínio analítico e citações auditáveis de fontes.
- [ ] **Visualização Analítica Interativa (Streamlit Web App):**
  - [x] Estrutura base multi-páginas configurada em `app/`.
  - [ ] Desenvolvimento dos dashboards interativos (Visão Geral, Parlamentares, Mapa Brasil, Beneficiários).
  - [ ] Integração do chat interativo com o Agente do Vertex AI (`app/pages/5_🤖_Assistente_IA.py`).
