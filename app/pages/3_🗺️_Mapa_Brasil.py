"""Página 3: Distribuição Geográfica e Territorial das Emendas."""

import sys
from pathlib import Path

_raiz = str(Path(__file__).resolve().parent.parent.parent)
_src = str(Path(_raiz) / "src")
for p in [_raiz, _src]:
    if p not in sys.path:
        sys.path.insert(0, p)

import plotly.express as px
import streamlit as st

from app.utils.db import carregar_tabela_gold
from app.utils.formatters import formatar_moeda, formatar_numero
from app.utils.styles import aplicar_estilos_globais, renderizar_card_metrica, renderizar_hero

st.set_page_config(
    page_title="Mapa Brasil - Emendas",
    page_icon="🗺️",
    layout="wide",
)

aplicar_estilos_globais()


def main() -> None:
    renderizar_hero(
        titulo="Distribuição Geográfica e Mapa Brasil",
        subtitulo="Repasses consolidados por Unidade Federativa, cidades beneficiadas e âmbito de destinação.",
        badge="Data Mart: tbl_distribuicao_geografica",
    )

    df_geo = carregar_tabela_gold("tbl_distribuicao_geografica")

    if df_geo.empty:
        st.warning("Dados geográficos não encontrados no BigQuery.")
        return

    # Sidebar: Filtros
    st.sidebar.markdown("### 🔍 Filtros Geográficos")

    regioes = ["Todas as Regiões"] + sorted(df_geo["SG_REGIAO"].dropna().unique().tolist())
    regiao_sel = st.sidebar.selectbox("Grande Região:", regioes, index=0)

    ambitos = ["Todos os Âmbitos"] + sorted(df_geo["DS_AMBITO_GEOGRAFICO"].dropna().unique().tolist())
    ambito_sel = st.sidebar.selectbox("Âmbito Federativo:", ambitos, index=0)

    anos = ["Todos os Anos"] + [str(a) for a in sorted(df_geo["DT_ANO"].dropna().unique(), reverse=True)]
    ano_sel = st.sidebar.selectbox("Ano de Referência:", anos, index=0)

    df_filtrado = df_geo.copy()
    if regiao_sel != "Todas as Regiões":
        df_filtrado = df_filtrado[df_filtrado["SG_REGIAO"] == regiao_sel]
    if ambito_sel != "Todos os Âmbitos":
        df_filtrado = df_filtrado[df_filtrado["DS_AMBITO_GEOGRAFICO"] == ambito_sel]
    if ano_sel != "Todos os Anos":
        df_filtrado = df_filtrado[df_filtrado["DT_ANO"] == int(ano_sel)]

    # Métricas Macro Geográficas
    total_pago = df_filtrado["VL_PAGO"].sum()
    total_convenio = df_filtrado["VL_CONVENIO"].sum()
    qtd_emendas = df_filtrado["QTD_EMENDAS"].sum()
    qtd_mun = df_filtrado[df_filtrado["CD_MUNICIPIO_IBGE"] > 0]["CD_MUNICIPIO_IBGE"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        renderizar_card_metrica("Total Pago na Região", formatar_moeda(total_pago, abreviado=True))
    with c2:
        renderizar_card_metrica(
            "Valor em Convênios",
            formatar_moeda(total_convenio, abreviado=True),
            classe_cor="color-primary",
        )
    with c3:
        renderizar_card_metrica(
            "Municípios com Repasse",
            formatar_numero(qtd_mun),
            "Cidades distintas",
            "color-success",
        )
    with c4:
        renderizar_card_metrica("Emendas Vinculadas", formatar_numero(qtd_emendas), classe_cor="color-warning")

    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Gráficos Comparativos: UF e Macrorregiões
    col_uf, col_reg = st.columns([1.6, 1])

    with col_uf:
        st.markdown("### 🏛️ Volume Pago por Unidade Federativa (UF)")
        df_uf = (
            df_filtrado.groupby("SG_UF")[["VL_PAGO", "VL_EMPENHADO"]]
            .sum()
            .reset_index()
            .sort_values("VL_PAGO", ascending=False)
        )
        df_uf["VL_PAGO_TXT"] = df_uf["VL_PAGO"].apply(lambda v: formatar_moeda(v, abreviado=True))

        fig_uf = px.bar(
            df_uf,
            x="SG_UF",
            y="VL_PAGO",
            color="VL_PAGO",
            color_continuous_scale=["#151C2C", "#2563EB", "#38BDF8"],
            labels={"SG_UF": "UF", "VL_PAGO": "Valor Pago"},
            text="VL_PAGO_TXT",
        )
        fig_uf.update_traces(
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>Valor Pago: %{text}<extra></extra>",
        )
        fig_uf.update_layout(
            template="plotly_dark",
            paper_bgcolor="#151C2C",
            plot_bgcolor="#151C2C",
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            height=380,
            yaxis={
                "title": "Valor Pago",
                "tickprefix": "R$ ",
                "tickformat": "~s",
                "gridcolor": "rgba(255,255,255,0.08)",
            },
        )
        st.plotly_chart(fig_uf, use_container_width=True)

    with col_reg:
        st.markdown("### 🍩 Share por Grande Região")
        df_reg = df_geo.groupby("SG_REGIAO")["VL_PAGO"].sum().reset_index()
        df_reg["VL_PAGO_TXT"] = df_reg["VL_PAGO"].apply(lambda v: formatar_moeda(v, abreviado=True))

        fig_donut = px.pie(
            df_reg,
            values="VL_PAGO",
            names="SG_REGIAO",
            hole=0.55,
            color_discrete_sequence=["#38BDF8", "#2563EB", "#10B981", "#F59E0B", "#8B5CF6", "#64748B"],
            custom_data=["VL_PAGO_TXT"],
        )
        fig_donut.update_traces(
            hovertemplate="<b>%{label}</b><br>Valor Pago: %{customdata[0]}<br>Share: %{percent}<extra></extra>",
        )
        fig_donut.update_layout(
            template="plotly_dark",
            paper_bgcolor="#151C2C",
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            height=380,
            showlegend=True,
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Top 20 Municípios com Maior Volume
    st.markdown("### 🏙️ Top 20 Municípios com Maior Volume de Recursos Recebidos")
    df_mun = (
        df_filtrado[df_filtrado["CD_MUNICIPIO_IBGE"] > 0]
        .groupby(["DS_MUNICIPIO", "SG_UF"])[["VL_PAGO", "QTD_EMENDAS", "TKM_PAGO_POR_EMENDA"]]
        .sum()
        .reset_index()
        .sort_values("VL_PAGO", ascending=False)
        .head(20)
    )
    df_mun["Cidade"] = df_mun["DS_MUNICIPIO"] + " - " + df_mun["SG_UF"]
    df_mun["VL_PAGO_TXT"] = df_mun["VL_PAGO"].apply(lambda v: formatar_moeda(v, abreviado=True))

    fig_mun = px.bar(
        df_mun,
        x="VL_PAGO",
        y="Cidade",
        orientation="h",
        color="VL_PAGO",
        color_continuous_scale=["#151C2C", "#10B981", "#38BDF8"],
        labels={"VL_PAGO": "Valor Pago", "Cidade": "Município"},
        text="VL_PAGO_TXT",
    )
    fig_mun.update_traces(
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>Valor Pago: %{text}<extra></extra>",
    )
    fig_mun.update_layout(
        template="plotly_dark",
        paper_bgcolor="#151C2C",
        plot_bgcolor="#151C2C",
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        height=520,
        yaxis={"autorange": "reversed"},
        xaxis={
            "title": "Valor Pago",
            "tickprefix": "R$ ",
            "tickformat": "~s",
            "gridcolor": "rgba(255,255,255,0.08)",
        },
    )
    st.plotly_chart(fig_mun, use_container_width=True)


if __name__ == "__main__":
    main()
