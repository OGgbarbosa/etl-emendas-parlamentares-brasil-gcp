# Projeto de Análise de Emendas Parlamentares (ETL no GCP)

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow?style=for-the-badge&logo=git)
![Python](https://img.shields.io/badge/python-3.12-blue?style=for-the-badge&logo=python)
![GCP](https://img.shields.io/badge/Google%20Cloud-BigQuery%20%7C%20GCS-red?style=for-the-badge&logo=google-cloud)
![Polars](https://img.shields.io/badge/Polars-2.0.0-blueviolet?style=for-the-badge&logo=polars)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B?style=for-the-badge&logo=streamlit)
![Ruff](https://img.shields.io/badge/code%20style-ruff-000000?style=for-the-badge&logo=ruff)

Pipeline de Engenharia de Dados e Inteligência Analítica para extração, tratamento, modelagem e visualização dos dados abertos de **Emendas Parlamentares do Brasil**, utilizando a plataforma **Google Cloud Platform (GCP)** com processamento colunar em memória via **Polars** e portal analítico interativo em **Streamlit**.

> **Status atual:** camadas **Raw**, **Bronze**, **Silver** (fatos com sentinelas para preservação integral de R$ 345,74 Bi e reconciliação automática), **Gold** (5 Data Marts físicos + 5 Views Semânticas com metadados para IA), **Guardrails de Segurança para IA** e **Portal Analítico Streamlit (Design System Dark & Blue com 5 Dashboards)** implementados e validados com **87 testes automatizados**. A esteira de Web Scraping para enriquecimento não estruturado na camada Silver está documentada e pronta para implementação (veja o [Roadmap](#️-roadmap-de-evolução) e a tabela de [Decisões de Projeto](#-decisões-de-projeto-e-status)).

---

## 🎯 Objetivo

Construir um pipeline ETL/ELT e produto de dados de ponta a ponta seguindo o padrão **Medallion Architecture**:
1. **Raw (0_raw)**: Ingestão de dados brutos tabulares em formato CSV (`ISO-8859-1` / `UTF-8`).
2. **Bronze (1_bronze)**: Conversão para formato colunar Parquet em memória, sanitização de cabeçalhos (`snake_case`), injeção de metadados de auditoria (`_ingestion_timestamp` e `_source_file`) e arquivamento no **Google Cloud Storage (GCS)**.
3. **Silver (2_silver)**: Modelagem analítica em tabelas fato, preservação total de registros históricos e especiais via código sentinela (`-1`), engenharia de atributos geográficos e temporais, reconciliação automatizada e carga direta em **tabelas nativas gerenciadas no BigQuery**:
   - `fato_emendas`: Fato orçamentária consolidando dotações das emendas com 6 métricas monetárias (empenhado, liquidado, pago, restos a pagar inscritos/cancelados/pagos), autor, ano, classificação funcional e localização.
   - `fato_convenios`: Fato analítica tratando a relação $N:N$ entre emendas e instrumentos contratuais com valores alocados.
   - `fato_favorecidos`: Fato periódica mensal de transferências e pagamentos diretos por favorecido (CNPJ/CPF/Órgão).
4. **Gold (3_gold)**: Data Marts analíticos em SQL materializados no **Google BigQuery** e camada de **Views Semânticas** preparadas para consumo humano e agentes de Inteligência Artificial:
   - 5 Data Marts físicos: `tbl_execucao_parlamentar`, `tbl_distribuicao_geografica`, `tbl_politicas_publicas`, `tbl_ranking_favorecidos` e `tbl_painel_convenios`.
   - 5 Views Semânticas: `view_ai_*` providas de colunas pré-formatadas (`*_BRL`, `*_PCT`), metadados `OPTIONS(description=...)` e resumos em linguagem natural para RAG (`DS_RESUMO_SEMANTICO`).
5. **Segurança & Guardrails para IA**: Módulos defensivos de validação de prompts (anti-prompt injection e anti-jailbreak), restrição de execução SQL exclusiva a consultas `SELECT` nas views semânticas autorizadas e sanitização de dados sensíveis na saída (PII e credenciais de nuvem).
6. **Web Scraping & Contexto na Silver** *(especificado)*: Esteira para captura de notícias e contexto cívico das 6 principais fontes públicas, armazenando as respostas brutas particionadas (`raw_scraping_*`) e uma tabela unificada para consumo (`fato_noticias_contexto`).
7. **Portal Analítico Streamlit**: Aplicação web multi-páginas com Design System Dark/Blue moderno (`#0A0E17`, `#151C2C`, `#38BDF8`), cards de métricas uniformes, gráficos interativos Plotly e assistente conversacional inteligente.

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
        Proc_E["silver_emendas.py (c/ Sentinela)"]
        Proc_C["silver_convenios.py (c/ Sentinela)"]
        Proc_F["silver_favorecidos.py (c/ Sentinela)"]
        Reconc["reconciliacao.py (Auditoria Automática)"]
    end

    subgraph DWH_Silver ["2_silver (BigQuery Managed Tables)"]
        S_EMENDA["fato_emendas (R$ 345,7 Bi preservados)"]
        S_CONV["fato_convenios (Instrumentos N:N)"]
        S_FAV["fato_favorecidos (Execução Favorecidos)"]
    end

    subgraph DWH_Gold ["3_gold (BigQuery Data Marts & Views)"]
        G_PARL["tbl_execucao_parlamentar"]
        G_GEO["tbl_distribuicao_geografica"]
        G_POL["tbl_politicas_publicas"]
        G_FAV["tbl_ranking_favorecidos"]
        G_CONV["tbl_painel_convenios"]
        G_VIEW["view_ai_* (Views Semânticas c/ Narrativa RAG)"]
    end

    subgraph SecurityZone ["Camada de Guardrails & Segurança (IA)"]
        GUARD_IN["Input Guards (Anti-Injection & Jailbreak)"]
        GUARD_SQL["SQL Guards (Somente SELECT em view_ai_*)"]
        GUARD_OUT["Output Guards (Sanitização PII / Redaction)"]
    end

    subgraph Web_Scraping ["Web Scraping na Silver (Especificado)"]
        W_RAW["2_silver.raw_scraping_* (6 Fontes Públicas)"]
        W_FATO["2_silver.fato_noticias_contexto"]
    end

    subgraph Frontend ["Portal Analítico Streamlit (Dark & Blue)"]
        APP_HOME["Home (Hero Banner & KPIs Globais)"]
        APP_P1["1_📊_Visao_Geral (Orçamento & Setores)"]
        APP_P2["2_🏛️_Parlamentares (Raio-X Congressistas)"]
        APP_P3["3_🗺️_Mapa_Brasil (Choropleth & Cidades)"]
        APP_P4["4_🏢_Beneficiarios (Top Favorecidos & Convênios)"]
        APP_P5["5_🤖_Assistente_IA (Chat com Guardrails)"]
    end

    CSV_E --> B_E
    CSV_C --> B_C
    CSV_F --> B_F

    B_E --> Proc_E --> S_EMENDA
    B_C --> Proc_C --> S_CONV
    B_F --> Proc_F --> S_FAV

    Proc_E & Proc_C & Proc_F --> Reconc

    S_EMENDA & S_CONV & S_FAV --> G_PARL & G_GEO & G_POL & G_FAV & G_CONV --> G_VIEW

    G_VIEW --> GUARD_SQL --> APP_P5
    APP_P5 --> GUARD_IN
    APP_P5 --> GUARD_OUT

    G_PARL & G_GEO & G_POL & G_FAV & G_CONV --> APP_HOME & APP_P1 & APP_P2 & APP_P3 & APP_P4
    W_RAW --> W_FATO
```

---

## 🧭 Decisões de Projeto e Status

| Tema | Decisão | Status |
|---|---|---|
| **Processamento** | Polars, pelo processamento colunar ultra-rápido e baixo uso de memória nas transformações analíticas. | Implementado |
| **Volume e tempo** | Conversão para Parquet de ~20 MB em média; pipeline completo executado em ~2 minutos com zero spill em disco. | Medido |
| **Bronze** | Parquet (Snappy) arquivado no GCS com isolamento de dados brutos e auditoria temporal. | Implementado |
| **Silver** | Tabelas nativas gerenciadas no BigQuery com ingestão direta e tipagem estrita de colunas monetárias e datas. | Implementado |
| **Sentinelas & Qualidade** | Substituição do descarte de registros sem código por código sentinela (`-1`) e indicador booleano (`codigo_emenda_informado`), recuperando **100% dos empenhos (R$ 345,74 Bi)** na Silver. | Implementado |
| **Reconciliação** | Módulo automático (`reconciliacao.py`) que audita a consistência volumétrica e financeira entre Bronze e Silver a cada execução. | Implementado |
| **Convênios (N:N)** | Grão da fato_convenios definido como `[numero_convenio × codigo_emenda]`. Na Gold, a agregação prévia deduplica o instrumento para prevenir sobreposição contábil. | Implementado |
| **Favorecidos** | Granularidade mensal, acompanhando a evolução dos repasses ao longo do exercício fiscal. | Implementado |
| **Gold (Data Marts)** | 5 tabelas analíticas materializadas no BigQuery para alta performance em consultas de dashboard. | Implementado |
| **Views Semânticas para IA** | 5 views semânticas (`view_ai_*`) enriquecidas com `OPTIONS(description=...)`, campos pré-formatados e texto narrativo para RAG (`DS_RESUMO_SEMANTICO`). | Implementado |
| **Guardrails de Segurança** | Proteção tripla do assistente de IA contra prompt injection, vazamento de PII e execução de SQL destrutivo. | Implementado |
| **Portal Streamlit** | 5 dashboards interativos e assistente com design system Dark/Blue moderno (`#0A0E17`, `#151C2C`, `#38BDF8`) e cartões padronizados. | Implementado |
| **Web Scraping** | Especificação técnica completa para coleta das 6 fontes públicas com gravação bruta na Silver (`raw_scraping_*`) e fato unificada (`fato_noticias_contexto`). | Especificado |
| **Testes** | **87 testes automatizados** com mocks de GCS/BigQuery cobrindo pipeline, transformações, camada Gold, views de IA, guardrails e helpers do app. | Implementado (Green) |

---

### 📊 Reconciliação de Integridade entre Camadas (Bronze ➔ Silver com Sentinelas)

> [!IMPORTANT]
> **Data de Referência dos Dados:** Arquivos brutos extraídos do Portal da Transparência em **28/08/2026**.  
> **Garantia de Integridade:** Com a implementação das regras sentinelas, **nenhum valor financeiro é expurgado** da `fato_emendas`, mantendo a conciliação total de **R$ 345,74 Bilhões** com o Portal da Transparência.

| Entidade | Linhas Bronze (Bruto) | Linhas Silver (Fato) | Código Sentinela (`-1`) | % Linhas Sentinela | Valor Financeiro Bronze | Valor Financeiro Silver | % Valor Preservado |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Emendas** (`fato_emendas`) | 94.463 | 94.463 | 17.810 | 18,85% | R$ 345,74 Bi (Empenhado) | R$ 345,74 Bi (Empenhado) | **100,00%** |
| **Convênios** (`fato_convenios`) | 85.104 | 85.057* | 9.190 | 10,80% | R$ 121,41 Bi (Conveniado) | R$ 121,37 Bi (Conveniado) | **99,96%** |
| **Favorecidos** (`fato_favorecidos`) | 820.690 | 820.690 | 67.039 | 8,17% | R$ 280,38 Bi (Pago) | R$ 280,38 Bi (Pago) | **100,00%** |

*\* A discreta diferença em convênios refere-se a apenas 47 linhas duplicadas estritas na chave composta `[numero_convenio, codigo_emenda]` tratadas sem qualquer prejuízo à granularidade do instrumento.*

---

## ⚙️ Stack Tecnológica

- **Linguagem & Processamento:** Python 3.12, [Polars](https://pola.rs/) (processamento colunar vetorizado).
- **Nuvem & Armazenamento (GCP):**
  - **Google Cloud Storage (GCS):** Data Lake Bronze (arquivos colunares Parquet Snappy).
  - **Google BigQuery:** Data Warehouse corporativo (camadas Silver e Gold nativas).
- **Frontend & Visualização:** [Streamlit](https://streamlit.io/) com tema Dark & Blue customizado e [Plotly](https://plotly.com/python/).
- **Gerenciador de Ambientes & Pacotes:** [uv](https://docs.astral.sh/uv/) (execução veloz e lockfile reproduzível).
- **Linter & Formatador:** [Ruff](https://docs.astral.sh/ruff/) (regras de estilo e limite de 120 caracteres).
- **Testes Automatizados:** [Pytest](https://pytest.org/) com mocks completos de APIs GCP e fixtures determinísticas.

---

## 📂 Estrutura do Projeto

```text
projeto_emendas/
├── .github/workflows/
│   └── ci_cd.yml                              # Pipeline de CI/CD (Ruff + Pytest)
├── pyproject.toml                             # Metadados, dependências, ruff e pytest configs
├── uv.lock                                    # Lockfile reproduzível do uv
├── .env                                       # Variáveis de ambiente (ignorado no git)
├── .streamlit/
│   └── config.toml                            # Configuração de tema Dark & Blue
├── docs/                                      # Especificações técnicas e planos arquiteturais
│   ├── plano_implementacao_streamlit.md       # Diretrizes de UI/UX, paleta Dark & Blue e telas
│   └── plano_implementacao_scraping.md        # Arquitetura das 6 fontes de scraping na Silver
├── app/                                       # Aplicação Web Streamlit (Multi-páginas)
│   ├── Home.py                                # Ponto de entrada, Hero Banner e KPIs macro
│   ├── guardrails/                            # Bridge para validação e segurança da interface IA
│   ├── utils/                                 # Utilitários de apoio do frontend
│   │   ├── db.py                              # Conexão e cache BigQuery (@st.cache_data)
│   │   ├── formatters.py                      # Formatação monetária (BRL), percentuais e documentos
│   │   └── styles.py                          # Design System Dark/Blue, métricas uniformes e CSS
│   └── pages/
│       ├── 1_📊_Visao_Geral.py                # Macro-orçamento, tendências temporais e funções
│       ├── 2_🏛️_Parlamentares.py               # Raio-X por congressista, taxas de execução e RAP
│       ├── 3_🗺️_Mapa_Brasil.py                 # Distribuição regional/estadual e mapa coroplético
│       ├── 4_🏢_Beneficiarios.py               # Maiores recebedores, CNPJs e convênios federais
│       └── 5_🤖_Assistente_IA.py               # Chat inteligente com guardrails e views semânticas
├── database/                                  # Dados brutos CSV locais (Portal da Transparência)
├── database_sample/                           # Amostras reduzidas para execução de testes em CI
├── data/
│   ├── bronze/                                # Parquets intermediários gerados da camada Bronze
│   ├── silver/                                # Parquets gerados da Silver (fato_emendas, convenios, favorecidos)
│   └── gold/                                  # Diretório reservado para artefatos da Gold
├── sql/
│   └── gold/                                  # Scripts SQL dos Data Marts e Views Semânticas de Consumo
│       ├── gold_execucao_parlamentar.sql      # Data Mart físico de parlamentares
│       ├── gold_distribuicao_geografica.sql   # Data Mart físico de geografia
│       ├── gold_politicas_publicas.sql        # Data Mart físico de funções orçamentárias
│       ├── gold_ranking_favorecidos.sql       # Data Mart físico de favorecidos
│       ├── gold_painel_convenios.sql          # Data Mart físico de convênios
│       ├── view_ai_execucao_parlamentar.sql   # View Semântica IA c/ campos BRL e narrativa RAG
│       ├── view_ai_distribuicao_geografica.sql# View Semântica IA c/ campos BRL e narrativa RAG
│       ├── view_ai_politicas_publicas.sql     # View Semântica IA c/ campos BRL e narrativa RAG
│       ├── view_ai_ranking_favorecidos.sql    # View Semântica IA c/ campos BRL e narrativa RAG
│       └── view_ai_painel_convenios.sql       # View Semântica IA c/ campos BRL e narrativa RAG
├── notebooks/
│   └── projeto_inicial.ipynb                  # Explorações analíticas preliminares
├── src/
│   └── etl_emendas_parlamentares/
│       ├── __init__.py
│       ├── pipeline.py                        # Orquestração do pipeline ponta a ponta
│       ├── config/
│       │   └── config.py                      # Definições de caminhos, datasets e prefixos
│       ├── conexao/
│       │   └── big_query.py                   # Conexão autenticada ao BigQuery e Storage via Service Account
│       ├── guardrails/                        # Módulos de segurança e validação do agente
│       │   ├── __init__.py
│       │   ├── input_guards.py                # Filtros contra prompt injection e jailbreak
│       │   ├── sql_guards.py                  # Restrição a SELECT nas views semânticas autorizadas
│       │   ├── output_guards.py               # Mascaramento de PII (CPF/CNPJ) e chaves de API
│       │   └── README.md                      # Documentação dos guardrails
│       ├── ingestao/
│       │   ├── upload_bronze.py               # Ingestão de arquivos Parquet no GCS
│       │   ├── upload_silver.py               # Carga direta em tabelas nativas gerenciadas no BigQuery
│       │   └── upload_gold.py                 # Orquestração e materialização dos Data Marts Gold
│       └── processamento/
│           ├── csv_parquet.py                 # Conversão de CSV para Parquet com injeção de auditoria
│           ├── normalizar.py                  # Normalização de nomes de colunas (snake_case)
│           ├── reconciliacao.py               # Relatórios automatizados de auditoria entre camadas
│           ├── silver_emendas.py              # Modelagem da fato_emendas com sentinelas
│           ├── silver_convenios.py            # Modelagem N:N da fato_convenios com sentinelas
│           └── silver_favorecidos.py          # Modelagem periódica da fato_favorecidos com sentinelas
└── tests/
    ├── conftest.py                            # Fixtures e configurações globais do Pytest
    ├── test_app_utils.py                      # Testes dos utilitários de formatação e cache do Streamlit
    ├── test_csv_parquet.py                    # Testes de conversão CSV -> Parquet
    ├── test_guardrails.py                     # Testes dos guardrails de entrada, SQL e saída
    ├── test_normalizar.py                     # Testes de sanitização de strings e colunas
    ├── test_pipeline.py                       # Testes de orquestração do pipeline
    ├── test_reconciliacao.py                  # Testes do gerador de auditoria e métricas
    ├── test_silver_convenios.py               # Testes da transformação de fato_convenios
    ├── test_silver_emendas.py                 # Testes da transformação de fato_emendas
    ├── test_silver_favorecidos.py             # Testes da transformação de fato_favorecidos
    ├── test_upload_bronze.py                  # Testes de envio para o Cloud Storage
    ├── test_upload_silver.py                  # Testes de carga nativa no BigQuery
    ├── test_upload_gold.py                    # Testes de orquestração e execução da Gold
    └── test_views_semanticas.py               # Testes de integridade, DDL e metadados das views de IA
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
> O arquivo `gcp-credentials.json` e o `.env` contêm credenciais confidenciais e estão protegidos pelo `.gitignore` para nunca serem versionados.

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

- Rodar suíte completa de testes automatizados (**87 testes**):
  ```bash
  uv run --no-sync pytest
  ```
- Rodar o linter:
  ```bash
  uv run --no-sync ruff check .
  ```
- Verificar a formatação do código:
  ```bash
  uv run --no-sync ruff format --check .
  ```

### 3. Execução do Pipeline de Dados

- **Executar Pipeline Completo (Raw -> Bronze -> Silver -> Gold + Auditoria)**:
  ```bash
  uv run python src/etl_emendas_parlamentares/pipeline.py
  ```

- **Gerar Relatório de Reconciliação e Auditoria**:
  ```bash
  uv run python src/etl_emendas_parlamentares/processamento/reconciliacao.py
  ```

- **Executar Módulos Individualmente**:
  - *Converter CSVs para Parquet (Raw)*: `uv run python src/etl_emendas_parlamentares/processamento/csv_parquet.py`
  - *Enviar Parquets para a Bronze (GCS)*: `uv run python src/etl_emendas_parlamentares/ingestao/upload_bronze.py`
  - *Processar fatos Silver*: `uv run python src/etl_emendas_parlamentares/processamento/silver_emendas.py`
  - *Carregar Silver no BigQuery*: `uv run python src/etl_emendas_parlamentares/ingestao/upload_silver.py`
  - *Materializar Data Marts Gold*: `uv run python src/etl_emendas_parlamentares/ingestao/upload_gold.py`

### 4. Execução do Portal Streamlit

Para iniciar o portal interativo multi-páginas:

```bash
uv run streamlit run app/Home.py
```

O aplicativo estará acessível localmente em `http://localhost:8501`.

---

## 🗺️ Roadmap de Evolução

- [x] **Camada Bronze (1_bronze):** Ingestão, auditoria e arquivamento colunar Parquet no Google Cloud Storage (GCS).
- [x] **Camada Silver (2_silver) - fatos:** `fato_emendas`, `fato_convenios` e `fato_favorecidos` carregadas como tabelas nativas no BigQuery.
  - [x] **Preservação Integral via Sentinelas:** Atribuição de sentinela (`codigo_da_emenda = -1`, `codigo_emenda_informado = false`), assegurando 100% dos empenhos (R$ 345,74 Bi) e dados históricos.
  - [x] **Automatização da Reconciliação:** Módulo `reconciliacao.py` que gera auditorias tabulares automáticas a cada ciclo.
  - [ ] Carga incremental com MERGE (para viradas semestrais com validação de alterações em dados passados).
- [x] **Camada Gold (3_gold):**
  - [x] Definição arquitetural dos 5 Data Marts analíticos via SQL no BigQuery.
  - [x] Scripts analíticos compilados e testados (`tbl_execucao_parlamentar`, `tbl_distribuicao_geografica`, `tbl_politicas_publicas`, `tbl_ranking_favorecidos`, `tbl_painel_convenios`).
  - [x] Módulo runner de orquestração (`upload_gold.py`) integrado ao `pipeline.py`.
  - [x] **Views Semânticas para IA (`view_ai_*`):** Metadados descritivos em `OPTIONS`, colunas formatadas em BRL/percentual e resumos sintéticos para RAG (`DS_RESUMO_SEMANTICO`).
  - [x] Suíte de testes automatizados para integridade das views de IA (`test_views_semanticas.py`).
- [x] **Segurança & Guardrails do Agente:**
  - [x] Filtros heurísticos de entrada (anti-prompt injection, detecção de jailbreak, limitação de payload).
  - [x] Guardrails de SQL (validação restrita de `SELECT` exclusivo nas views `view_ai_*`).
  - [x] Anonimização e mascaramento de saída (redação de CPFs, CNPJs, e-mails, telefones e credenciais GCP/GitHub).
- [ ] **Camada de Web Scraping & Contexto na Silver:**
  - [x] Especificação e arquitetura detalhadas em [`docs/plano_implementacao_scraping.md`](docs/plano_implementacao_scraping.md).
  - [ ] Implementação da esteira de scraping das 6 fontes públicas em `2_silver.raw_scraping_*`.
  - [ ] Construção da tabela consolidada para RAG `2_silver.fato_noticias_contexto`.
- [x] **Visualização Analítica Interativa (Portal Streamlit):**
  - [x] Design System Dark & Blue com paleta moderna e responsiva (`app/utils/styles.py`).
  - [x] 5 Dashboards analíticos completos (Visão Geral, Parlamentares, Mapa Brasil, Beneficiários e Assistente IA).
  - [x] Cards de métricas com altura fixa, layout protegido e formatação monetária brasileira.
  - [x] Integração do chat conversacional com os guardrails de segurança.
- [ ] **Camada de Consumo Inteligente (Google Cloud Vertex AI):**
  - [ ] Configuração do Vertex AI Agent Builder com RAG híbrido (Views BigQuery + Notícias Silver).
  - [ ] Agente conversacional Gemini com streaming de respostas e citações de fontes.
- [ ] **Empacotamento:** Imagem Docker do pipeline para execução híbrida (local ou GCP Cloud Run).
