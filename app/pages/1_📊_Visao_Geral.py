"""Página 1: Visão Geral e Macro-Orçamento das Emendas Parlamentares."""

import sys
from pathlib import Path

_raiz = str(Path(__file__).resolve().parent.parent.parent)
_src = str(Path(_raiz) / "src")
for p in [_raiz, _src]:
    if p not in sys.path:
        sys.path.insert(0, p)

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.utils.db import carregar_tabela_gold
from app.utils.formatters import formatar_moeda, formatar_percentual
from app.utils.styles import aplicar_estilos_globais, renderizar_card_metrica, renderizar_hero

st.set_page_config(
    page_title="Visão Geral - Emendas Parlamentares",
    page_icon="📊",
    layout="wide",
)

aplicar_estilos_globais()


def main() -> None:
    renderizar_hero(
        titulo="Visão Geral e Macro-Orçamento",
        subtitulo="Acompanhamento da execução financeira agregada, evolução histórica do ciclo da despesa e alocação setorial.",
        badge="Data Mart: tbl_politicas_publicas & tbl_execucao_parlamentar",
    )

    # Carrega dados
    df_politicas = carregar_tabela_gold("tbl_politicas_publicas")
    df_execucao = carregar_tabela_gold("tbl_execucao_parlamentar")

    if df_politicas.empty or df_execucao.empty:
        st.warning("Dados não encontrados no BigQuery. Verifique a execução da camada Gold.")
        return

    # Sidebar: Filtros
    st.sidebar.markdown("### 🔍 Filtros de Análise")

    anos_disponiveis = sorted(df_politicas["DT_ANO"].dropna().unique(), reverse=True)
    anos_opcoes = ["Todos os Anos"] + [str(a) for a in anos_disponiveis]
    ano_sel = st.sidebar.selectbox("Ano de Referência:", anos_opcoes, index=0)

    tipos_disponiveis = sorted(df_politicas["DS_TIPO_EMENDA"].dropna().unique())
    tipos_opcoes = ["Todas as Modalidades"] + list(tipos_disponiveis)
    tipo_sel = st.sidebar.selectbox("Tipo de Emenda:", tipos_opcoes, index=0)

    # Aplicação de filtros
    df_pol_filtrado = df_politicas.copy()
    df_exec_filtrado = df_execucao.copy()

    if ano_sel != "Todos os Anos":
        ano_num = int(ano_sel)
        df_pol_filtrado = df_pol_filtrado[df_pol_filtrado["DT_ANO"] == ano_num]
        df_exec_filtrado = df_exec_filtrado[df_exec_filtrado["DT_ANO"] == ano_num]

    if tipo_sel != "Todas as Modalidades":
        df_pol_filtrado = df_pol_filtrado[df_pol_filtrado["DS_TIPO_EMENDA"] == tipo_sel]
        df_exec_filtrado = df_exec_filtrado[df_exec_filtrado["DS_TIPO_EMENDA"] == tipo_sel]

    # Cálculos de KPIs consolidados
    total_empenhado = df_exec_filtrado["VL_EMPENHADO"].sum()
    total_liquidado = df_exec_filtrado["VL_LIQUIDADO"].sum()
    total_pago = df_exec_filtrado["VL_PAGO"].sum()
    taxa_exec = (total_pago / total_empenhado * 100) if total_empenhado > 0 else 0.0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        renderizar_card_metrica(
            "Empenhado",
            formatar_moeda(total_empenhado, abreviado=True),
            f"Filtro: {ano_sel}",
            "color-primary",
        )
    with k2:
        renderizar_card_metrica(
            "Liquidado",
            formatar_moeda(total_liquidado, abreviado=True),
            "Serviços/bens atestados",
            "color-primary",
        )
    with k3:
        renderizar_card_metrica(
            "Efetivamente Pago",
            formatar_moeda(total_pago, abreviado=True),
            "Ordens bancárias quitadas",
            "color-success",
        )
    with k4:
        renderizar_card_metrica(
            "Taxa de Execução",
            formatar_percentual(taxa_exec),
            "Pago / Empenhado",
            "color-warning" if taxa_exec < 70 else "color-success",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Gráfico de Área da Evolução Orçamentária
    st.markdown("### 📈 Evolução Histórica do Ciclo Orçamentário")

    # Agrupa por ano (respeitando o filtro de tipo de emenda, se houver)
    df_tempo_base = (
        df_execucao if tipo_sel == "Todas as Modalidades" else df_execucao[df_execucao["DS_TIPO_EMENDA"] == tipo_sel]
    )
    df_tempo = (
        df_tempo_base.groupby("DT_ANO")[["VL_EMPENHADO", "VL_LIQUIDADO", "VL_PAGO"]]
        .sum()
        .reset_index()
        .sort_values("DT_ANO")
    )

    # Valores formatados para exibição visual no hover
    empenhado_txt = df_tempo["VL_EMPENHADO"].apply(lambda v: formatar_moeda(v, abreviado=True))
    liquidado_txt = df_tempo["VL_LIQUIDADO"].apply(lambda v: formatar_moeda(v, abreviado=True))
    pago_txt = df_tempo["VL_PAGO"].apply(lambda v: formatar_moeda(v, abreviado=True))

    fig_tempo = go.Figure()
    fig_tempo.add_trace(
        go.Scatter(
            x=df_tempo["DT_ANO"],
            y=df_tempo["VL_EMPENHADO"],
            customdata=empenhado_txt,
            mode="lines+markers",
            name="Empenhado",
            line={"color": "#38BDF8", "width": 3},
            fill="tozeroy",
            fillcolor="rgba(56, 189, 248, 0.1)",
            hovertemplate="<b>Empenhado (%{x})</b>: %{customdata}<extra></extra>",
        )
    )
    fig_tempo.add_trace(
        go.Scatter(
            x=df_tempo["DT_ANO"],
            y=df_tempo["VL_LIQUIDADO"],
            customdata=liquidado_txt,
            mode="lines+markers",
            name="Liquidado",
            line={"color": "#2563EB", "width": 2.5},
            fill="tonexty",
            fillcolor="rgba(37, 99, 235, 0.1)",
            hovertemplate="<b>Liquidado (%{x})</b>: %{customdata}<extra></extra>",
        )
    )
    fig_tempo.add_trace(
        go.Scatter(
            x=df_tempo["DT_ANO"],
            y=df_tempo["VL_PAGO"],
            customdata=pago_txt,
            mode="lines+markers",
            name="Pago",
            line={"color": "#10B981", "width": 3},
            fill="tonexty",
            fillcolor="rgba(16, 185, 129, 0.15)",
            hovertemplate="<b>Pago (%{x})</b>: %{customdata}<extra></extra>",
        )
    )

    fig_tempo.update_layout(
        template="plotly_dark",
        paper_bgcolor="#151C2C",
        plot_bgcolor="#151C2C",
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        height=380,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        hovermode="x unified",
        xaxis={"title": "Exercício Fiscal", "dtick": 1},
        yaxis={
            "title": "Volume Orçamentário",
            "tickprefix": "R$ ",
            "tickformat": "~s",
            "gridcolor": "rgba(255,255,255,0.08)",
        },
    )
    st.plotly_chart(fig_tempo, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Treemap de Políticas Públicas
    st.markdown("### 🌳 Distribuição Temática de Políticas Públicas (Função ➔ Subfunção)")
    st.caption("Visualização hierárquica por área temática. Clique nos retângulos para detalhar subfunções.")

    # Agrupa por Função e Subfunção no dataset filtrado
    df_tree = df_pol_filtrado.groupby(["DS_FUNCAO", "DS_SUBFUNCAO"])[["VL_PAGO", "VL_EMPENHADO"]].sum().reset_index()
    df_tree = df_tree[df_tree["VL_PAGO"] > 0].copy()

    # Diferencia Subfunção quando coincidir com o nome da Função para prevenir loop no Plotly
    df_tree["SUBFUNCAO_LABEL"] = df_tree.apply(
        lambda r: f"{r['DS_SUBFUNCAO']} " if r["DS_SUBFUNCAO"] == r["DS_FUNCAO"] else r["DS_SUBFUNCAO"],
        axis=1,
    )
    df_tree["VL_PAGO_ABREV"] = df_tree["VL_PAGO"].apply(lambda v: formatar_moeda(v, abreviado=True))

    if not df_tree.empty:
        fig_tree = px.treemap(
            df_tree,
            path=["DS_FUNCAO", "SUBFUNCAO_LABEL"],
            values="VL_PAGO",
            color="VL_PAGO",
            color_continuous_scale=["#0D1527", "#1E40AF", "#38BDF8", "#10B981"],
            title="",
            custom_data=["VL_PAGO_ABREV"],
        )
        fig_tree.update_layout(
            template="plotly_dark",
            paper_bgcolor="#151C2C",
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            height=480,
        )
        fig_tree.update_traces(
            textinfo="label+value",
            texttemplate="<b>%{label}</b><br>%{customdata[0]}",
            hovertemplate="<b>%{label}</b><br>Valor Pago: %{customdata[0]}<br>(%{percentParent:.1%} do setor pai)<extra></extra>",
        )
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado para os filtros selecionados.")

    # 3. Tabela Comparativa de Políticas Públicas
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Consolidação por Função de Governo")

    df_resumo_funcao = (
        df_pol_filtrado.groupby("DS_FUNCAO")[["VL_EMPENHADO", "VL_LIQUIDADO", "VL_PAGO"]]
        .sum()
        .reset_index()
        .sort_values("VL_PAGO", ascending=False)
    )
    df_resumo_funcao["Taxa de Execução (%)"] = (
        df_resumo_funcao["VL_PAGO"] / df_resumo_funcao["VL_EMPENHADO"] * 100
    ).round(2)
    df_resumo_funcao["VL_EMPENHADO"] = df_resumo_funcao["VL_EMPENHADO"].apply(lambda v: formatar_moeda(v))
    df_resumo_funcao["VL_LIQUIDADO"] = df_resumo_funcao["VL_LIQUIDADO"].apply(lambda v: formatar_moeda(v))
    df_resumo_funcao["VL_PAGO"] = df_resumo_funcao["VL_PAGO"].apply(lambda v: formatar_moeda(v))

    df_resumo_funcao.columns = [
        "Função Governamental",
        "Valor Empenhado",
        "Valor Liquidado",
        "Valor Pago",
        "Taxa Execução (%)",
    ]

    st.dataframe(df_resumo_funcao, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
