"""Aplicação Web Streamlit - Portal de Análise das Emendas Parlamentares do Brasil.

Ponto de entrada (Home) com visão geral do projeto, arquitetura e navegação.
Para executar localmente:
    uv run streamlit run app/Home.py
"""


def main() -> None:
    """Função principal da Home do Streamlit."""
    try:
        import streamlit as st
    except ImportError:
        print("Streamlit ainda não está instalado no ambiente. Instale com: uv add streamlit")
        return

    st.set_page_config(
        page_title="Emendas Parlamentares Brasil",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🏛️ Portal de Análise de Emendas Parlamentares")
    st.markdown(
        """
        Bem-vindo ao observatório analítico de **Emendas Parlamentares da União**.
        
        Este portal foi construído sobre uma esteira moderna de engenharia de dados (Modern Data Stack):
        * **Raw / Ingestão:** Dados públicos do Portal da Transparência (CGU).
        * **Silver:** Saneamento, tipagem estrita e modelo multidimensional (*Star Schema*) em **Polars**.
        * **Gold:** Data Marts analíticos agregados e materializados no **Google BigQuery**.
        * **IA & Contexto:** RAG híbrido conectando números oficiais e notícias no **Google Vertex AI**.

        ---
        ### 🧭 Navegue pelas páginas na barra lateral:
        1. **📊 Visão Geral:** KPIs macro, volume empenhado vs pago e restos a pagar.
        2. **🏛️ Parlamentares:** Desempenho e alocação orçamentária por deputado e senador.
        3. **🗺️ Mapa Brasil:** Distribuição geográfica dos repasses por UF e Municípios.
        4. **🏢 Beneficiários:** Ranking de prefeituras, órgãos e fornecedores recebedores.
        5. **🤖 Assistente IA:** Chat interativo com Gemini para consultas em linguagem natural.
        """
    )

    st.sidebar.success("Selecione uma visão analítica acima.")


if __name__ == "__main__":
    main()

