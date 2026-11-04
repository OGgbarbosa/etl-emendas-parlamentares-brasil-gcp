"""Estilos CSS e componentes visuais do Design System Dark & Blue."""

import streamlit as st

CSS_GLOBAL = """
<style>
/* Fonte e background geral */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Reduzir paddings padrão da página */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    padding-left: 2.5rem;
    padding-right: 2.5rem;
}

/* Card Hero estilizado */
.hero-card {
    background: linear-gradient(135deg, #151C2C 0%, #0D1527 100%);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 12px;
    padding: 1.8rem 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
}

.hero-title {
    color: #F8FAFC;
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 0.6rem;
    letter-spacing: -0.025em;
    line-height: 1.25;
}

.hero-subtitle {
    color: #94A3B8;
    font-size: 1.05rem;
    line-height: 1.6;
    margin-bottom: 0;
    max-width: 850px;
}

/* Cards de Métricas Orçamentárias Rigorosamente Uniformes e Lineares */
div[data-testid="column"] {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}

div[data-testid="column"] > div {
    width: 100%;
}

.metric-card {
    background: #151C2C;
    border: 1px solid rgba(56, 189, 248, 0.15);
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
    height: 125px;
    min-height: 125px;
    max-height: 125px;
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.2s ease, border-color 0.2s ease;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    box-sizing: border-box;
    overflow: hidden;
}

.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(56, 189, 248, 0.4);
}

.metric-label {
    color: #94A3B8;
    font-size: 0.82rem;
    font-weight: 500;
    line-height: 1.2;
    height: 1.2rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 0.25rem;
}

.metric-value {
    color: #F8FAFC;
    font-size: 1.65rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin: 0.1rem 0;
}

.metric-subtext {
    font-size: 0.78rem;
    color: #64748B;
    height: 1.1rem;
    line-height: 1.1rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.color-primary { color: #38BDF8; }
.color-success { color: #10B981; }
.color-warning { color: #F59E0B; }
.color-danger { color: #EF4444; }

/* Cards de Navegação Uniformes */
.nav-card {
    background: #151C2C;
    border: 1px solid rgba(56, 189, 248, 0.15);
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    height: 145px;
    min-height: 145px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    transition: all 0.2s ease;
    box-sizing: border-box;
}

.nav-card:hover {
    border-color: #38BDF8;
    box-shadow: 0 0 15px rgba(56, 189, 248, 0.15);
}

.nav-card-title {
    color: #F8FAFC;
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.4rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.nav-card-desc {
    color: #94A3B8;
    font-size: 0.85rem;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* Badges e tags */
.badge {
    display: inline-block;
    padding: 0.25rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.badge-blue {
    background: rgba(56, 189, 248, 0.15);
    color: #38BDF8;
    border: 1px solid rgba(56, 189, 248, 0.3);
}

.badge-green {
    background: rgba(16, 185, 129, 0.15);
    color: #10B981;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

/* Customização de Chat Messages */
.chat-container {
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
}
</style>
"""


def aplicar_estilos_globais() -> None:
    """Injeta a folha de estilos CSS global na aplicação Streamlit."""
    st.markdown(CSS_GLOBAL, unsafe_allow_html=True)


def renderizar_hero(titulo: str, subtitulo: str, badge: str = "Dados Oficiais CGU / SIAFI") -> None:
    """Renderiza um Hero Banner padronizado."""
    html = f"""
    <div class="hero-card">
        <div style="margin-bottom: 0.8rem;">
            <span class="badge badge-blue">{badge}</span>
        </div>
        <div class="hero-title">{titulo}</div>
        <div class="hero-subtitle">{subtitulo}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def renderizar_card_metrica(
    label: str,
    valor: str,
    subtexto: str = "",
    classe_cor: str = "color-primary",
) -> None:
    """Renderiza um card individual de KPI com design system Dark & Blue rigorosamente uniforme."""
    texto_sub = subtexto.strip() if subtexto else "&nbsp;"
    html = (
        f'<div class="metric-card">'
        f'<div class="metric-label" title="{label}">{label}</div>'
        f'<div class="metric-value {classe_cor}" title="{valor}">{valor}</div>'
        f'<div class="metric-subtext color-muted">{texto_sub}</div>'
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)
