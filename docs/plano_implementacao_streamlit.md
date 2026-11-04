# 📘 Plano de Ação & Especificação de Design — Portal Streamlit
## Observatório de Emendas Parlamentares do Brasil

Este documento detalha o roteiro técnico de implementação do aplicativo **Streamlit**, definindo o **Design System (Tema Dark & Azul Moderno)**, a arquitetura de componentes, as fontes de dados em cada tela e a esteira do **Assistente de IA**.

---

## 🎨 1. Design System & Identidade Visual

O design do portal seguirá uma estética **moderna, cívica e de alta tecnologia (FinTech/Data Platform)**, inspirada em plataformas de análise avançada.

### Paleta de Cores (Dark Theme + Blue Accents)

| Elemento | Código Hex | Nome do Tom | Aplicação |
|---|:---:|:---:|---|
| **Background Principal** | `#0B0F19` | Deep Obsidian | Fundo geral da aplicação e páginas |
| **Background Secundário** | `#151C2C` | Navy Slate | Sidebar, containers e cards de métricas |
| **Bordas & Divisores** | `rgba(56, 189, 248, 0.15)` | Subtle Cyan Line | Bordas finas de 1px com leve transparência |
| **Azul Primário (Destaque)** | `#38BDF8` | Electric Sky Blue | Botões ativos, KPIs principais, links e títulos |
| **Azul Secundário** | `#2563EB` | Cobalt Blue | Barras de gráficos, cabeçalhos de tabelas |
| **Azul Noturno (Hover/Active)** | `#1E40AF` | Deep Royal | Estados de hover em botões e seletores |
| **Texto Principal** | `#F8FAFC` | Pure White / Slate 50 | Títulos, valores de métricas e textos principais |
| **Texto Muted / Secundário** | `#94A3B8` | Cool Gray / Slate 400 | Subtítulos, legendas de gráficos e notas de rodapé |

### Cores Semânticas de Apoio Orçamentário

* **Execução / Sucesso (Verde Neon):** `#10B981` (Valores pagos, altas taxas de execução orçamentária).
* **Restos a Pagar / Atenção (Âmbar / Laranja):** `#F59E0B` (Saldos pendentes de liquidação/pagamento).
* **Bloqueios / Alerta (Coral Vermelho):** `#EF4444` (Baixa execução, dotações canceladas).

---

## ⚙️ 2. Configuração de Tema do Streamlit (`.streamlit/config.toml`)

Configuração nativa para aplicar a identidade visual:

```toml
[theme]
base = "dark"
primaryColor = "#38BDF8"
backgroundColor = "#0B0F19"
secondaryBackgroundColor = "#151C2C"
textColor = "#F8FAFC"
font = "sans serif"

[server]
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

---

## 📂 3. Estrutura de Arquivos da Camada Frontend

```text
app/
├── .streamlit/
│   └── config.toml               # Configuração oficial do tema Dark + Blue
├── Home.py                       # Landing page com KPIs macro e guia de navegação
├── utils/
│   ├── __init__.py
│   ├── db.py                     # Conexão com BigQuery e cache inteligente (@st.cache_data)
│   ├── formatters.py             # Formatação monetária (R$ Bi, Mi), % e CNPJ/CPF
│   └── styles.py                 # CSS injetado (Glassmorphism, cards e badges)
└── pages/
    ├── 1_📊_Visao_Geral.py       # Macro-orçamento, execução e divisão setorial
    ├── 2_🏛️_Parlamentares.py      # Raio-X por deputado e senador
    ├── 3_🗺️_Mapa_Brasil.py        # Distribuição geográfica municipal e estadual
    ├── 4_🏢_Beneficiarios.py      # Maiores fornecedores, ONGs e convênios
    └── 5_🤖_Assistente_IA.py      # Chatbot inteligente com Gemini & RAG Híbrido
```

---

## 🧭 4. Especificação Detalhada por Dashboard

### 🏠 Home / Landing Page (`app/Home.py`)
* **Objetivo:** Introduzir o observatório, contextualizar a origem dos dados (Portal da Transparência / CGU) e destacar os números globais do orçamento.
* **Componentes:**
  * Banner Hero estilizado em gradiente azul escuro.
  * 4 Cards macro de métricas:
    1. Orçamento Total Empenhado (Histórico).
    2. Total Efetivamente Pago.
    3. Volume de Restos a Pagar Pendentes.
    4. Quantidade de Municípios Alcançados.
  * Guia rápido das 5 páginas analíticas com cards clicáveis.

---

### 📊 Dashboard 1: Visão Geral e Macro-Orçamento (`1_📊_Visao_Geral.py`)
* **Tabelas Gold de Origem:** `tbl_politicas_publicas` + `tbl_execucao_parlamentar`
* **Módulos & Gráficos:**
  1. **Filtros Globais:** Seletor de Ano (2014–2026), Modalidade de Emenda (Individual, Bancada, Comissão, Relator).
  2. **Evolução Orçamentária Anual (Plotly Area Chart):**
     * Linhas de Empenhado vs. Liquidado vs. Pago ao longo do tempo.
  3. **Treemap Setorial de Políticas Públicas (Plotly Treemap):**
     * Visualização hierárquica por Função $\rightarrow$ Subfunção (ex.: Saúde $\rightarrow$ Atenção Primária vs. Educação $\rightarrow$ Ensino Superior).
  4. **Taxas Médias de Eficiência:**
     * Gauge chart com a Taxa de Execução Orçamentária global do ano selecionado.
  5. **Tabela de Variação Anual (YoY):**
     * Ranking das políticas públicas com maior aceleração ou retração orçamentária.

---

### 🏛️ Dashboard 2: Raio-X dos Parlamentares (`2_🏛️_Parlamentares.py`)
* **Tabela Gold de Origem:** `tbl_execucao_parlamentar`
* **Módulos & Gráficos:**
  1. **Seletor Inteligente de Autor:**
     * Campo `st.selectbox` com busca textual por nome do deputado/senador.
  2. **Perfil Orçamentário do Parlamentar:**
     * Total indicado, valor pago, restos a pagar a liquidar e quantidade de emendas únicas.
  3. **Ranking dos Top 15 Parlamentares (Horizontal Bar Chart Plotly):**
     * Maiores empenhos e pagamentos por congressista.
  4. **Quadrante de Eficiência (Scatter Plot Plotly):**
     * Eixo X: Volume Empenhado; Eixo Y: Taxa de Execução (%); Tamanho da bolha: Qtd de Emendas.
     * Divisão em 4 quadrantes (Alta Alocação / Alta Execução; Alta Alocação / Baixa Execução, etc.).
  5. **Tabela de Detalhamento com Download:**
     * Visualização tabular com paginação, filtros e exportação em CSV/Excel.

---

### 🗺️ Dashboard 3: Distribuição Geográfica & Mapa Brasil (`3_🗺️_Mapa_Brasil.py`)
* **Tabela Gold de Origem:** `tbl_distribuicao_geografica`
* **Módulos & Gráficos:**
  1. **Mapa Coroplético do Brasil (Plotly Choropleth Map):**
     * Mapa com preenchimento em escala de azuis destacando o volume de repasses por UF.
  2. **Segmentação por Esfera (`DS_AMBITO_GEOGRAFICO`):**
     * Filtro entre `MUNICIPAL`, `ESTADUAL` e `NACIONAL_REGIONAL`.
  3. **Top 20 Municípios com Maior Volume de Recursos (Bar Chart):**
     * Cidades que mais receberam transferências de emendas parlamentares.
  4. **Distribuição Macrorregional (Donut Chart):**
     * Percentual destinado ao Norte, Nordeste, Centro-Oeste, Sudeste e Sul.
  5. **Indicador de Ticket Médio por Emenda (`TKM_PAGO_POR_EMENDA`):**
     * Média de recursos por projeto/emenda enviada ao município.

---

### 🏢 Dashboard 4: Beneficiários, Fornecedores e Convênios (`4_🏢_Beneficiarios.py`)
* **Tabelas Gold de Origem:** `tbl_ranking_favorecidos` + `tbl_painel_convenios`
* **Módulos & Gráficos:**
  1. **Filtro por Natureza Jurídica & Tipo de Favorecido:**
     * Prefeituras, Entidades sem Fins Lucrativos (ONGs), Empresas Privadas e Pessoas Físicas.
  2. **Top 20 Maiores Recebedores do País (Bar Chart):**
     * Ranking por valor acumulado histórico e no ano.
  3. **Indicador de Concentração Política (Auditoria Cívica):**
     * Entidades que recebem recursos de **um único parlamentar** vs. aquelas apoiadas por múltiplos congressistas.
  4. **Histórico Mensal de Pagamentos:**
     * Linha do tempo com o fluxo de caixa recebido pela entidade ao longo dos meses.
  5. **Painel de Convênios Federais:**
     * Órgãos com maior volume de instrumentos firmados e taxa de consorciamento de emendas por convênio.

---

### 🤖 Dashboard 5: Assistente IA & Pesquisa Inteligente (`5_🤖_Assistente_IA.py`)
* **Objetivo:** Permitir ao cidadão e pesquisador consultar dados oficiais e notícias em linguagem natural.
* **Componentes da Interface:**
  1. **Histórico de Conversa Dinâmico (`st.chat_message`):**
     * Balões estilizados em Dark Navy com borda azul e avatar personalizado.
  2. **Chips / Sugestões de Perguntas Rápidas (Quick Starters):**
     * *"Quais os 5 deputados que mais destinaram emendas para a Saúde em 2024?"*
     * *"Quais municípios de Minas Gerais mais receberam recursos de comissão?"*
     * *"O que a imprensa noticiou sobre emendas de relator (RP9) e decisões do STF?"*
     * *"Existe alguma ONG de destaque entre os maiores recebedores no estado do Maranhão?"*
  3. **Roteamento Híbrido da IA:**
     * **Consulta Analítica:** Traduz a pergunta para SQL, consulta os Data Marts `3_gold.*` no BigQuery e plota a resposta com tabela ou gráfico interativo direto no chat.
     * **Consulta Contextual (RAG):** Busca artigos jornalísticos e observatórios no Cloud Storage (Folha, EBC, Senado, Transparência Brasil) e retorna resumo com fontes citadas.
  4. **Citações Auditáveis:**
     * Badges clicáveis indicando a procedência do dado (Tabela BigQuery ou Artigo com data e veículo).

---

## 🛠️ 5. Módulo Utilitário de Dados & Cache (`app/utils/db.py`)

Para viabilizar consultas ultrarrápidas com consumo mínimo de quotas do BigQuery:

```python
import streamlit as st
import pandas as pd
from google.cloud import bigquery
from etl_emendas_parlamentares.conexao.big_query import get_bigquery_client
from etl_emendas_parlamentares.config.config import GOLD_DATASET


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_dados_gold(nome_tabela: str, query_filtro: str = "") -> pd.DataFrame:
    """Executa consultas cacheadas sobre os Data Marts da Camada Gold."""
    client = get_bigquery_client()
    projeto = client.project
    sql = f"SELECT * FROM `{projeto}.{GOLD_DATASET}.{nome_tabela}`"
    if query_filtro:
        sql += f" WHERE {query_filtro}"
    return client.query(sql).to_dataframe()
```

---

## 📋 6. Checklist de Ações por Etapa

### Fase 1: Fundação & Design System
- [ ] Adicionar dependências no projeto: `uv add streamlit plotly`.
- [ ] Criar o arquivo de tema `.streamlit/config.toml` com a paleta dark/blue.
- [ ] Implementar `app/utils/styles.py` com CSS customizado para cards e KPIs.
- [ ] Implementar `app/utils/formatters.py` com funções de formatação monetária (BRL).
- [ ] Implementar `app/utils/db.py` com client do BigQuery e cache de 1 hora.

### Fase 2: Home e Visão Geral
- [ ] Atualizar `app/Home.py` com hero banner, métricas de cabeçalho e navegação.
- [ ] Implementar `app/pages/1_📊_Visao_Geral.py` conectando a `tbl_politicas_publicas`.
- [ ] Criar gráficos de área histórica, treemap setorial e gauge de execução.

### Fase 3: Telas Parlamentares e Geográfica
- [ ] Implementar `app/pages/2_🏛️_Parlamentares.py` com filtros por congressista, scatter plot e ranking.
- [ ] Implementar `app/pages/3_🗺️_Mapa_Brasil.py` com mapa coroplético do Brasil e divisão por âmbito.

### Fase 4: Beneficiários e Convênios
- [ ] Implementar `app/pages/4_🏢_Beneficiarios.py` com ranking de entidades, indicador de paroquialismo e instrumentos.

### Fase 5: Assistente IA & RAG
- [ ] Implementar `app/pages/5_🤖_Assistente_IA.py` com interface de chat e quick starter pills.
- [ ] Conectar o roteador conversacional com BigQuery (Text-to-SQL) e Vertex AI Agent Builder.

### Fase 6: Testes, CI/CD e Execução
- [ ] Criar testes unitários para os utilitários de formatação e conexão em `tests/`.
- [ ] Garantir validação completa via `ruff` e `pytest`.
- [ ] Testar navegação fluida em execução local: `uv run streamlit run app/Home.py`.

