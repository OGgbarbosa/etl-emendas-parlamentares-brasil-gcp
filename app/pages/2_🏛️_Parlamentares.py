"""Página 2: Raio-X e Desempenho dos Parlamentares."""

import sys
from pathlib import Path

_raiz = str(Path(__file__).resolve().parent.parent.parent)
_src = str(Path(_raiz) / "src")
for p in [_raiz, _src]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import plotly.express as px
import streamlit as st

from app.utils.db import carregar_tabela_gold
from app.utils.formatters import formatar_moeda, formatar_numero, formatar_percentual
from app.utils.styles import aplicar_estilos_globais, renderizar_card_metrica, renderizar_hero

st.set_page_config(
    page_title="Parlamentares - Emendas",
    page_icon="🏛️",
    layout="wide",
)

aplicar_estilos_globais()


def main() -> None:
    renderizar_hero(
        titulo="Raio-X dos Parlamentares",
        subtitulo="Análise individualizada de deputados e senadores, rankings de liberação e quadrante de eficiência.",
        badge="Data Mart: tbl_execucao_parlamentar",
    )

    df_exec = carregar_tabela_gold("tbl_execucao_parlamentar")

    if df_exec.empty:
        st.warning("Dados de parlamentares não encontrados no BigQuery.")
        return

    # Filtros na barra lateral
    st.sidebar.markdown("### 🔍 Filtros de Parlamentares")

    ufs_disponiveis = ["Todas as UFs"] + sorted(df_exec["SG_UF"].dropna().unique().tolist())
    uf_sel = st.sidebar.selectbox("Estado (UF):", ufs_disponiveis, index=0)

    anos_disponiveis = ["Todos os Anos"] + [str(a) for a in sorted(df_exec["DT_ANO"].dropna().unique(), reverse=True)]
    ano_sel = st.sidebar.selectbox("Ano de Referência:", anos_disponiveis, index=0)

    df_base = df_exec.copy()
    if uf_sel != "Todas as UFs":
        df_base = df_base[df_base["SG_UF"] == uf_sel]
    if ano_sel != "Todos os Anos":
        df_base = df_base[df_base["DT_ANO"] == int(ano_sel)]

    # 1. Seletor de Autor Individual
    st.markdown("### 👤 Perfil do Parlamentar")
    autores_lista = sorted(df_base["DS_AUTOR"].dropna().unique().tolist())

    if not autores_lista:
        st.info("Nenhum parlamentar encontrado para os filtros selecionados.")
        return

    autor_selecionado = st.selectbox(
        "Selecione um Deputado, Senador ou Colegiado:",
        autores_lista,
        index=0,
    )

    # Detalhes do parlamentar selecionado
    df_autor = df_base[df_base["DS_AUTOR"] == autor_selecionado]

    empenhado_autor = df_autor["VL_EMPENHADO"].sum()
    liquidado_autor = df_autor["VL_LIQUIDADO"].sum()
    pago_autor = df_autor["VL_PAGO"].sum()
    saldo_rap_autor = df_autor["VL_RESTOS_SALDO_A_PAGAR"].sum()
    qtd_emendas_autor = df_autor["QTD_EMENDAS"].sum()
    taxa_autor = (pago_autor / empenhado_autor * 100) if empenhado_autor > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        renderizar_card_metrica(
            "Total Empenhado",
            formatar_moeda(empenhado_autor, abreviado=True),
            f"Dotação ({formatar_numero(qtd_emendas_autor)} emendas)",
            classe_cor="color-primary",
        )
    with c2:
        renderizar_card_metrica(
            "Total Liquidado",
            formatar_moeda(liquidado_autor, abreviado=True),
            "Execução atestada",
            classe_cor="color-primary",
        )
    with c3:
        renderizar_card_metrica(
            "Total Pago",
            formatar_moeda(pago_autor, abreviado=True),
            f"Saldo RAP: {formatar_moeda(saldo_rap_autor, abreviado=True)}",
            classe_cor="color-success",
        )
    with c4:
        renderizar_card_metrica(
            "Taxa de Execução",
            formatar_percentual(taxa_autor),
            "Percentual pago / empenhado",
            classe_cor="color-warning" if taxa_autor < 70 else "color-success",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Ranking dos Top 15 Parlamentares
    st.markdown("### 🏆 Top 15 Parlamentares com Maior Volume de Recursos")

    df_ranking = (
        df_base.groupby("DS_AUTOR")[["VL_EMPENHADO", "VL_PAGO", "QTD_EMENDAS"]]
        .sum()
        .reset_index()
        .sort_values("VL_PAGO", ascending=False)
        .head(15)
    )
    df_ranking["VL_PAGO_TXT"] = df_ranking["VL_PAGO"].apply(lambda v: formatar_moeda(v, abreviado=True))

    fig_bar = px.bar(
        df_ranking,
        x="VL_PAGO",
        y="DS_AUTOR",
        orientation="h",
        color="VL_PAGO",
        color_continuous_scale=["#151C2C", "#2563EB", "#38BDF8"],
        labels={"VL_PAGO": "Valor Pago (BRL)", "DS_AUTOR": "Parlamentar"},
        text="VL_PAGO_TXT",
    )
    fig_bar.update_traces(
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>Valor Pago: %{text}<extra></extra>",
    )
    fig_bar.update_layout(
        template="plotly_dark",
        paper_bgcolor="#151C2C",
        plot_bgcolor="#151C2C",
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        height=480,
        yaxis={"autorange": "reversed"},
        xaxis={
            "title": "Valor Pago",
            "tickprefix": "R$ ",
            "tickformat": "~s",
            "gridcolor": "rgba(255,255,255,0.08)",
        },
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Quadrante de Eficiência
    st.markdown("### 🎯 Quadrante de Eficiência Orçamentária")
    st.caption("Eixo X: Volume Empenhado • Eixo Y: Taxa de Execução (%) • Tamanho da Bolha: Quantidade de Emendas")

    df_quadrante = (
        df_base.groupby(["DS_AUTOR", "SG_UF"])[["VL_EMPENHADO", "VL_PAGO", "QTD_EMENDAS"]].sum().reset_index()
    )
    df_quadrante = df_quadrante[df_quadrante["VL_EMPENHADO"] > 0].copy()
    df_quadrante["TAXA_EXEC"] = (df_quadrante["VL_PAGO"] / df_quadrante["VL_EMPENHADO"] * 100).round(2)
    df_quadrante["EMPENHADO_TXT"] = df_quadrante["VL_EMPENHADO"].apply(lambda v: formatar_moeda(v, abreviado=True))
    df_quadrante["PAGO_TXT"] = df_quadrante["VL_PAGO"].apply(lambda v: formatar_moeda(v, abreviado=True))

    fig_scatter = px.scatter(
        df_quadrante,
        x="VL_EMPENHADO",
        y="TAXA_EXEC",
        size="QTD_EMENDAS",
        color="SG_UF",
        hover_name="DS_AUTOR",
        custom_data=["EMPENHADO_TXT", "PAGO_TXT", "SG_UF", "QTD_EMENDAS"],
        labels={
            "VL_EMPENHADO": "Volume Empenhado",
            "TAXA_EXEC": "Taxa de Execução (%)",
            "SG_UF": "UF",
            "QTD_EMENDAS": "Emendas",
        },
    )
    fig_scatter.update_traces(
        hovertemplate="<b>%{hovertext} (%{customdata[2]})</b><br>Empenhado: %{customdata[0]}<br>Pago: %{customdata[1]}<br>Emendas: %{customdata[3]}<br>Taxa Execução: %{y:.1f}%<extra></extra>"
    )
    fig_scatter.update_layout(
        template="plotly_dark",
        paper_bgcolor="#151C2C",
        plot_bgcolor="#151C2C",
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        height=480,
        yaxis={"range": [0, 105], "gridcolor": "rgba(255,255,255,0.08)"},
        xaxis={
            "title": "Volume Empenhado",
            "tickprefix": "R$ ",
            "tickformat": "~s",
            "gridcolor": "rgba(255,255,255,0.08)",
        },
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # 4. Tabela com Exportação
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Tabela Detalhada com Exportação")

    df_tabela = df_base[
        [
            "DT_ANO",
            "DS_AUTOR",
            "SG_UF",
            "DS_TIPO_EMENDA",
            "QTD_EMENDAS",
            "VL_EMPENHADO",
            "VL_PAGO",
            "TX_EXECUCAO",
        ]
    ].copy()
    df_tabela_display = pd.DataFrame(
        {
            "Ano": df_tabela["DT_ANO"],
            "Parlamentar / Autor": df_tabela["DS_AUTOR"],
            "UF": df_tabela["SG_UF"],
            "Tipo de Emenda": df_tabela["DS_TIPO_EMENDA"],
            "Qtd. Emendas": df_tabela["QTD_EMENDAS"].apply(formatar_numero),
            "Valor Empenhado": df_tabela["VL_EMPENHADO"].apply(formatar_moeda),
            "Valor Pago": df_tabela["VL_PAGO"].apply(formatar_moeda),
            "Taxa de Execução": df_tabela["TX_EXECUCAO"].apply(formatar_percentual),
        }
    )
    st.dataframe(df_tabela_display, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
