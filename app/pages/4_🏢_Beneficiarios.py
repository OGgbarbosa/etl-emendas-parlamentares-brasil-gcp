"""Página 4: Beneficiários, Fornecedores e Painel de Convênios Federais."""

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
from app.utils.formatters import formatar_documento, formatar_moeda, formatar_numero
from app.utils.styles import aplicar_estilos_globais, renderizar_card_metrica, renderizar_hero

st.set_page_config(
    page_title="Beneficiários & Convênios",
    page_icon="🏢",
    layout="wide",
)

aplicar_estilos_globais()


def main() -> None:
    renderizar_hero(
        titulo="Beneficiários, Fornecedores e Convênios",
        subtitulo="Auditoria cívica de empresas, prefeituras, fundos e entidades recebedoras de recursos das emendas.",
        badge="Data Marts: tbl_ranking_favorecidos & tbl_painel_convenios",
    )

    df_fav = carregar_tabela_gold("tbl_ranking_favorecidos")
    df_conv = carregar_tabela_gold("tbl_painel_convenios")

    if df_fav.empty or df_conv.empty:
        st.warning("Dados de favorecidos ou convênios não encontrados no BigQuery.")
        return

    # Sidebar: Filtros
    st.sidebar.markdown("### 🔍 Filtros de Beneficiários")

    tipos_fav = ["Todos os Tipos"] + sorted(df_fav["DS_TIPO_FAVORECIDO"].dropna().unique().tolist())
    tipo_sel = st.sidebar.selectbox("Tipo de Entidade:", tipos_fav, index=0)

    ufs_fav = ["Todas as UFs"] + sorted(df_fav["SG_UF_FAVORECIDO"].dropna().unique().tolist())
    uf_sel = st.sidebar.selectbox("UF do Beneficiário:", ufs_fav, index=0)

    df_fav_filt = df_fav.copy()
    if tipo_sel != "Todos os Tipos":
        df_fav_filt = df_fav_filt[df_fav_filt["DS_TIPO_FAVORECIDO"] == tipo_sel]
    if uf_sel != "Todas as UFs":
        df_fav_filt = df_fav_filt[df_fav_filt["SG_UF_FAVORECIDO"] == uf_sel]

    # KPIs Gerais de Favorecidos
    total_recebido_ano = df_fav_filt["VL_RECEBIDO_ANO"].sum()
    qtd_favorecidos = df_fav_filt["CD_FAVORECIDO"].nunique()
    total_conveniado = df_conv["VL_TOTAL_CONVENIADO"].sum()
    qtd_convenios = df_conv["QTD_CONVENIOS"].sum()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        renderizar_card_metrica("Repassado a Beneficiários", formatar_moeda(total_recebido_ano, abreviado=True))
    with k2:
        renderizar_card_metrica(
            "Entidades Beneficiadas",
            formatar_numero(qtd_favorecidos),
            "Pessoas físicas e jurídicas",
            "color-success",
        )
    with k3:
        renderizar_card_metrica(
            "Total em Convênios",
            formatar_moeda(total_conveniado, abreviado=True),
            "Instrumentos deduplicados",
            "color-primary",
        )
    with k4:
        renderizar_card_metrica("Convênios Pactuados", formatar_numero(qtd_convenios), classe_cor="color-warning")

    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Top 20 Maiores Recebedores
    st.markdown("### 🏆 Top 20 Entidades com Maior Volume de Recursos Recebidos")
    df_top = (
        df_fav_filt.groupby(["DS_FAVORECIDO", "CD_FAVORECIDO", "DS_TIPO_FAVORECIDO"])[
            ["VL_RECEBIDO_ANO", "QTD_PARLAMENTARES_DISTINTOS_ANO"]
        ]
        .sum()
        .reset_index()
        .sort_values("VL_RECEBIDO_ANO", ascending=False)
        .head(20)
    )
    df_top["VL_RECEBIDO_TXT"] = df_top["VL_RECEBIDO_ANO"].apply(lambda v: formatar_moeda(v, abreviado=True))

    fig_fav = px.bar(
        df_top,
        x="VL_RECEBIDO_ANO",
        y="DS_FAVORECIDO",
        orientation="h",
        color="VL_RECEBIDO_ANO",
        color_continuous_scale=["#151C2C", "#2563EB", "#38BDF8"],
        labels={"VL_RECEBIDO_ANO": "Valor Recebido", "DS_FAVORECIDO": "Beneficiário"},
        text="VL_RECEBIDO_TXT",
    )
    fig_fav.update_traces(
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>Valor Recebido: %{text}<extra></extra>",
    )
    fig_fav.update_layout(
        template="plotly_dark",
        paper_bgcolor="#151C2C",
        plot_bgcolor="#151C2C",
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        height=520,
        yaxis={"autorange": "reversed"},
        xaxis={
            "title": "Valor Recebido",
            "tickprefix": "R$ ",
            "tickformat": "~s",
            "gridcolor": "rgba(255,255,255,0.08)",
        },
    )
    st.plotly_chart(fig_fav, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Painel de Convênios Federais
    st.markdown("### 📜 Top 10 Convenentes com Maior Volume Pactuado")
    df_top_conv = (
        df_conv.groupby(["DS_CONVENENTE", "SG_UF", "DS_FUNCAO"])[["VL_TOTAL_CONVENIADO", "QTD_CONVENIOS"]]
        .sum()
        .reset_index()
        .sort_values("VL_TOTAL_CONVENIADO", ascending=False)
        .head(10)
    )
    df_top_conv["VL_TOTAL_CONVENIADO"] = df_top_conv["VL_TOTAL_CONVENIADO"].apply(lambda v: formatar_moeda(v))
    df_top_conv.columns = ["Ente / Convenente", "UF", "Função", "Valor Conveniado", "Qtd Convênios"]

    st.dataframe(df_top_conv, use_container_width=True, hide_index=True)

    # 3. Tabela com busca de favorecidos
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Detalhamento com Documento Fiscal (CNPJ/CPF)")

    df_tabela = (
        df_fav_filt[
            [
                "CD_FAVORECIDO",
                "DS_FAVORECIDO",
                "DS_TIPO_FAVORECIDO",
                "SG_UF_FAVORECIDO",
                "VL_RECEBIDO_ANO",
                "VL_RECEBIDO_TOTAL_HISTORICO",
            ]
        ]
        .head(100)
        .copy()
    )
    df_tabela["CD_FAVORECIDO"] = df_tabela["CD_FAVORECIDO"].apply(formatar_documento)
    df_tabela["VL_RECEBIDO_ANO"] = df_tabela["VL_RECEBIDO_ANO"].apply(formatar_moeda)
    df_tabela["VL_RECEBIDO_TOTAL_HISTORICO"] = df_tabela["VL_RECEBIDO_TOTAL_HISTORICO"].apply(formatar_moeda)
    df_tabela.columns = ["CNPJ/CPF", "Beneficiário", "Tipo", "UF", "Valor no Ano", "Total Histórico"]

    st.dataframe(df_tabela, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
