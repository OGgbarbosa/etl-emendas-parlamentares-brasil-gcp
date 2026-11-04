"""Portal de Análise das Emendas Parlamentares do Brasil - Home.

Observatório cívico e analítico construído sobre a esteira Medallion no GCP BigQuery.
"""

import sys
from pathlib import Path

# Assegura que a raiz e 'src' estejam no sys.path
_raiz = str(Path(__file__).resolve().parent.parent)
_src = str(Path(_raiz) / "src")
for p in [_raiz, _src]:
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st

from app.utils.db import carregar_kpis_macro
from app.utils.formatters import formatar_moeda, formatar_numero
from app.utils.styles import aplicar_estilos_globais, renderizar_card_metrica, renderizar_hero

st.set_page_config(
    page_title="Observatório de Emendas Parlamentares",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_estilos_globais()


def main() -> None:
    # Sidebar institucional
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Flag_of_Brazil.svg/200px-Flag_of_Brazil.svg.png",
        width=40,
    )
    st.sidebar.markdown("### 🏛️ Observatório Cívico")
    st.sidebar.info(
        """
        **Pipeline de Engenharia & IA:**
        - **Lakehouse:** GCS + BigQuery
        - **Camadas:** Bronze ➔ Silver ➔ Gold
        - **Inteligência:** Gemini & Vertex AI
        - **Fonte:** Portal da Transparência / CGU
        """
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Versão 1.0.0 • Dados consolidados")

    # Hero Banner
    renderizar_hero(
        titulo="Observatório de <span>Emendas Parlamentares</span>",
        subtitulo=(
            "Plataforma analítica e de transparência pública para acompanhamento das dotações, "
            "execução orçamentária e destinação dos recursos das emendas federais do Brasil."
        ),
        badge="Dados Oficiais CGU / SIAFI • BigQuery Gold",
    )

    # Carregamento dos KPIs macro
    kpis = carregar_kpis_macro()

    # 4 Cards de Métricas Principais
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        renderizar_card_metrica(
            label="Total Empenhado (Histórico)",
            valor=formatar_moeda(kpis["total_empenhado"], abreviado=True),
            subtexto=f"Total: {formatar_moeda(kpis['total_empenhado'])}",
            classe_cor="color-primary",
        )

    with col2:
        renderizar_card_metrica(
            label="Total Pago Efetivo",
            valor=formatar_moeda(kpis["total_pago"], abreviado=True),
            subtexto=f"Total: {formatar_moeda(kpis['total_pago'])}",
            classe_cor="color-success",
        )

    with col3:
        renderizar_card_metrica(
            label="Restos a Pagar (Saldo)",
            valor=formatar_moeda(kpis["total_restos_saldo"], abreviado=True),
            subtexto="Inscritos pendentes de quitação",
            classe_cor="color-warning",
        )

    with col4:
        renderizar_card_metrica(
            label="Municípios Alcançados",
            valor=formatar_numero(kpis["qtd_municipios"]),
            subtexto="Cidades brasileiras beneficiadas",
            classe_cor="color-primary",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Seção de Navegação Rápida
    st.markdown("### 🧭 Módulos Analíticos de Consulta")
    st.markdown("Selecione um painel na barra lateral ou explore os módulos abaixo:")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
            <div class="nav-card">
                <div class="nav-card-title">📊 1. Visão Geral e Macro-Orçamento</div>
                <div class="nav-card-desc">
                    Acompanhe a evolução histórica dos empenhos, liquidações e pagamentos. 
                    Explore a distribuição temática por políticas públicas (Saúde, Educação, etc.) e o Treemap setorial.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="nav-card">
                <div class="nav-card-title">🏛️ 2. Raio-X dos Parlamentares</div>
                <div class="nav-card-desc">
                    Consulte individualmente cada deputado e senador. Analise rankings de liberação, 
                    quadrante de eficiência orçamentária e saldos de restos a pagar por congressista.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class="nav-card">
                <div class="nav-card-title">🗺️ 3. Distribuição Geográfica & Mapa Brasil</div>
                <div class="nav-card-desc">
                    Visualização territorial interativa por UF e municípios. 
                    Segmentação por âmbito federativo (Municipal, Estadual, Nacional) e ticket médio por emenda.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="nav-card">
                <div class="nav-card-title">🏢 4. Beneficiários & Convênios</div>
                <div class="nav-card-desc">
                    Ranking dos maiores favorecidos e fornecedores contratados. Análise de concentração política 
                    e painel de convênios federais pactuados com prefeituras e estados.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="nav-card" style="border-color: rgba(56, 189, 248, 0.4);">
            <div class="nav-card-title" style="color: #38BDF8;">🤖 5. Assistente IA de Consulta Natural</div>
            <div class="nav-card-desc">
                Interaja em linguagem natural com o Agente Gemini. Formule perguntas como 
                <em>"Quais deputados mais destinaram recursos para a Saúde em 2024?"</em> 
                e receba respostas fundamentadas com tabelas, gráficos e dados auditados.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
