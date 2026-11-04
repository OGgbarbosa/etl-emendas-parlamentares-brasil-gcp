"""Página 5: Assistente IA & Chatbot em Linguagem Natural com Gemini & BigQuery."""

import sys
from pathlib import Path

_raiz = str(Path(__file__).resolve().parent.parent.parent)
_src = str(Path(_raiz) / "src")
for p in [_raiz, _src]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import streamlit as st

from app.guardrails import validar_prompt_usuario, validar_resposta_ia
from app.utils.db import carregar_tabela_gold
from app.utils.formatters import formatar_moeda, formatar_numero, formatar_percentual
from app.utils.styles import aplicar_estilos_globais, renderizar_hero

st.set_page_config(
    page_title="Assistente IA - Emendas",
    page_icon="🤖",
    layout="wide",
)

aplicar_estilos_globais()

PERGUNTAS_RAPIDAS = [
    "Quais os parlamentares que mais destinaram recursos pagos?",
    "Quais áreas de políticas públicas receberam mais recursos em emendas?",
    "Quais municípios receberam os maiores volumes de recursos?",
    "Quem são os maiores recebedores e favorecidos de emendas?",
    "Qual a situação dos convênios pactuados a partir de emendas?",
]


def extrair_resumo_seguro(row: pd.Series, tipo: str) -> str:
    """Extrai ou reconstrói dinamicamente a narrativa semântica sem jamais retornar nan."""
    resumo = str(row.get("DS_RESUMO_SEMANTICO", "")).strip()
    if resumo and resumo.lower() not in ["nan", "none", "null", ""]:
        return resumo

    # Síntese segura e factível em Python como contingência à prova de falhas
    if tipo == "parlamentar":
        return (
            f"No exercício de {row.get('DT_ANO', 'N/D')}, o parlamentar/autor {row.get('DS_AUTOR', 'Não informado')} "
            f"(UF: {row.get('SG_UF', 'NACI')}, Tipo: {row.get('DS_TIPO_EMENDA', 'Geral')}) destinou "
            f"{formatar_numero(row.get('QTD_EMENDAS', 0))} emenda(s), totalizando "
            f"{formatar_moeda(row.get('VL_PAGO', 0))} pagos efetivos "
            f"(Taxa de Execução: {formatar_percentual(row.get('TX_EXECUCAO', 0))})."
        )
    if tipo == "politica":
        return (
            f"No exercício de {row.get('DT_ANO', 'N/D')}, a área temática {row.get('DS_FUNCAO', 'Geral')} "
            f"({row.get('DS_SUBFUNCAO', 'Geral')}) acumulou {formatar_numero(row.get('QTD_EMENDAS', 0))} emenda(s), "
            f"com {formatar_moeda(row.get('VL_PAGO', 0))} pagos efetivos "
            f"(Taxa de Execução: {formatar_percentual(row.get('TX_EXECUCAO', 0))})."
        )
    if tipo == "municipio":
        return (
            f"No exercício de {row.get('DT_ANO', 'N/D')}, o município {row.get('DS_MUNICIPIO', 'N/D')} "
            f"({row.get('SG_UF', 'NACI')}) recebeu {formatar_numero(row.get('QTD_EMENDAS', 0))} emenda(s), "
            f"com repasse total efetivo de {formatar_moeda(row.get('VL_PAGO', 0))}."
        )
    if tipo == "favorecido":
        return (
            f"No exercício de {row.get('DT_ANO', 'N/D')}, a entidade {row.get('DS_FAVORECIDO', 'N/D')} "
            f"({row.get('SG_UF_FAVORECIDO', 'NACI')}) recebeu {formatar_moeda(row.get('VL_RECEBIDO_ANO', 0))} "
            f"em transferências oriundas de emendas parlamentares."
        )
    if tipo == "convenio":
        return (
            f"O convenente {row.get('DS_CONVENENTE', 'N/D')} ({row.get('SG_UF', 'NACI')}) "
            f"pactuou {formatar_numero(row.get('QTD_CONVENIOS', 0))} convênio(s) somando "
            f"{formatar_moeda(row.get('VL_TOTAL_CONVENIADO', 0))} em recursos federais."
        )
    return "Registro auditado disponível na base oficial."


def formatar_tabela_view(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Transforma nomes de campos em nomes amigáveis, valores monetários em BRL e percentuais em %."""
    if df.empty:
        return df

    if tipo == "parlamentar":
        return pd.DataFrame(
            {
                "Parlamentar / Autor": df["DS_AUTOR"].fillna("Não informado"),
                "UF": df["SG_UF"].fillna("NACI"),
                "Tipo de Emenda": df.get("DS_TIPO_EMENDA", pd.Series(["Geral"] * len(df))).fillna("Geral"),
                "Valor Empenhado": df["VL_EMPENHADO"].apply(formatar_moeda),
                "Valor Liquidado": df["VL_LIQUIDADO"].apply(formatar_moeda),
                "Valor Pago": df["VL_PAGO"].apply(formatar_moeda),
                "Taxa de Execução": df["TX_EXECUCAO"].apply(formatar_percentual),
            }
        )

    if tipo == "politica":
        return pd.DataFrame(
            {
                "Área / Função": df["DS_FUNCAO"].fillna("Geral"),
                "Subfunção": df["DS_SUBFUNCAO"].fillna("Geral"),
                "Tipo de Emenda": df.get("DS_TIPO_EMENDA", pd.Series(["Geral"] * len(df))).fillna("Geral"),
                "Valor Empenhado": df["VL_EMPENHADO"].apply(formatar_moeda),
                "Valor Pago": df["VL_PAGO"].apply(formatar_moeda),
                "Taxa de Execução": df["TX_EXECUCAO"].apply(formatar_percentual),
                "Share no Ano": df.get("PC_REPRESENTATIVIDADE_PAGO", pd.Series([0.0] * len(df))).apply(
                    formatar_percentual
                ),
                "Tendência Anual": df.get("DS_TENDENCIA_YOY", pd.Series(["ESTAVEL"] * len(df))).fillna("ESTAVEL"),
            }
        )

    if tipo == "municipio":
        return pd.DataFrame(
            {
                "Município / Destino": df["DS_MUNICIPIO"].fillna("Não informado"),
                "UF": df["SG_UF"].fillna("NACI"),
                "Região": df.get("SG_REGIAO", pd.Series(["Nacional"] * len(df))).fillna("Nacional"),
                "Valor Empenhado": df["VL_EMPENHADO"].apply(formatar_moeda),
                "Valor Pago": df["VL_PAGO"].apply(formatar_moeda),
                "Taxa de Execução": df["TX_EXECUCAO"].apply(formatar_percentual),
                "Qtd. Emendas": df["QTD_EMENDAS"].apply(formatar_numero),
                "Qtd. Convênios": df["QTD_CONVENIOS"].apply(formatar_numero),
            }
        )

    if tipo == "favorecido":
        return pd.DataFrame(
            {
                "Entidade / Beneficiário": df["DS_FAVORECIDO"].fillna("Não informado"),
                "UF": df["SG_UF_FAVORECIDO"].fillna("NACI"),
                "Tipo de Favorecido": df["DS_TIPO_FAVORECIDO"].fillna("Não informado"),
                "Valor Recebido no Ano": df["VL_RECEBIDO_ANO"].apply(formatar_moeda),
                "Total Histórico Acumulado": df["VL_RECEBIDO_TOTAL_HISTORICO"].apply(formatar_moeda),
                "Transferências": df.get("QTD_TRANSFERENCIAS_RECEBIDAS", pd.Series([0] * len(df))).apply(
                    formatar_numero
                ),
            }
        )

    if tipo == "convenio":
        return pd.DataFrame(
            {
                "Convenente / Executor": df["DS_CONVENENTE"].fillna("Não informado"),
                "UF": df["SG_UF"].fillna("NACI"),
                "Área Governamental": df["DS_FUNCAO"].fillna("Geral"),
                "Valor Total Conveniado": df["VL_TOTAL_CONVENIADO"].apply(formatar_moeda),
                "Ticket Médio por Convênio": df.get("TKM_VALOR_POR_CONVENIO", pd.Series([0.0] * len(df))).apply(
                    formatar_moeda
                ),
                "Qtd. Convênios": df["QTD_CONVENIOS"].apply(formatar_numero),
            }
        )

    return df


def responder_pergunta(prompt: str) -> dict:
    """Roteia a pergunta em linguagem natural para as views semânticas de IA com dados reais e auditados."""
    # 1. Guardrail de Entrada (Prevenção de Injeção e Controle de Escopo)
    val_in = validar_prompt_usuario(prompt)
    if not val_in.valido:
        return {
            "tipo": "bloqueio",
            "texto": f"⚠️ **Aviso de Governança dos Guardrails:** {val_in.motivo}",
            "tabela": None,
            "fonte": "Guardrails de Entrada",
        }

    p = val_in.prompt_higienizado.lower().strip()

    # 1. Favorecidos e Beneficiários (prioridade para evitar colisão com 'quem')
    if any(
        k in p
        for k in [
            "favorecido",
            "favorecidos",
            "beneficiário",
            "beneficiario",
            "beneficiários",
            "beneficiarios",
            "recebedor",
            "recebedores",
            "empresa",
            "ong",
            "entidade",
        ]
    ):
        df = carregar_tabela_gold(
            "view_ai_ranking_favorecidos",
            query_filtro="VL_RECEBIDO_ANO > 0 AND DS_FAVORECIDO NOT IN ('Sem informação')",
            order_by="VL_RECEBIDO_ANO DESC",
            limite=10,
        )
        if not df.empty:
            df_top = df.head(5).copy()
            resumos = [extrair_resumo_seguro(row, "favorecido") for _, row in df_top.iterrows()]
            texto = "**Ranking dos Principais Entes e Favorecidos:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            df_display = formatar_tabela_view(df_top, "favorecido")
            texto_seguro = validar_resposta_ia(texto).texto_filtrado
            return {
                "tipo": "analitico",
                "texto": texto_seguro,
                "tabela": df_display,
                "fonte": "view_ai_ranking_favorecidos",
            }

    # 2. Convênios Pactuados
    if any(
        k in p
        for k in [
            "convênio",
            "convenio",
            "convênios",
            "convenios",
            "instrumento",
            "contrato",
            "pactuado",
            "pactuados",
        ]
    ):
        df = carregar_tabela_gold(
            "view_ai_painel_convenios",
            query_filtro="VL_TOTAL_CONVENIADO > 0",
            order_by="VL_TOTAL_CONVENIADO DESC",
            limite=10,
        )
        if not df.empty:
            df_top = df.head(5).copy()
            resumos = [extrair_resumo_seguro(row, "convenio") for _, row in df_top.iterrows()]
            texto = "**Consolidação do Painel de Convênios Federais:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            df_display = formatar_tabela_view(df_top, "convenio")
            texto_seguro = validar_resposta_ia(texto).texto_filtrado
            return {
                "tipo": "analitico",
                "texto": texto_seguro,
                "tabela": df_display,
                "fonte": "view_ai_painel_convenios",
            }

    # 3. Municípios e Distribuição Territorial
    if any(
        k in p
        for k in [
            "município",
            "municipio",
            "municípios",
            "municipios",
            "cidade",
            "cidades",
            "estado",
            "uf",
            "região",
            "regiao",
            "geografia",
            "território",
        ]
    ):
        df = carregar_tabela_gold(
            "view_ai_distribuicao_geografica",
            query_filtro="CD_MUNICIPIO_IBGE > 0 AND VL_PAGO > 0",
            order_by="VL_PAGO DESC",
            limite=10,
        )
        if not df.empty:
            df_top = df.head(5).copy()
            resumos = [extrair_resumo_seguro(row, "municipio") for _, row in df_top.iterrows()]
            texto = "**Distribuição Territorial e Cidades Mais Beneficiadas:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            df_display = formatar_tabela_view(df_top, "municipio")
            texto_seguro = validar_resposta_ia(texto).texto_filtrado
            return {
                "tipo": "analitico",
                "texto": texto_seguro,
                "tabela": df_display,
                "fonte": "view_ai_distribuicao_geografica",
            }

    # 4. Políticas Públicas e Funções de Governo
    if any(
        k in p
        for k in [
            "política",
            "politica",
            "políticas",
            "politicas",
            "saúde",
            "saude",
            "educação",
            "educacao",
            "área",
            "area",
            "áreas",
            "função",
            "funcao",
            "setor",
            "setorial",
        ]
    ):
        df = carregar_tabela_gold(
            "view_ai_politicas_publicas",
            query_filtro="DS_FUNCAO NOT IN ('Sem informação', 'Múltiplo')",
            order_by="VL_PAGO DESC",
            limite=10,
        )
        if not df.empty:
            df_top = df.head(5).copy()
            resumos = [extrair_resumo_seguro(row, "politica") for _, row in df_top.iterrows()]
            texto = "**Alocação Setorial em Políticas Públicas:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            df_display = formatar_tabela_view(df_top, "politica")
            texto_seguro = validar_resposta_ia(texto).texto_filtrado
            return {
                "tipo": "analitico",
                "texto": texto_seguro,
                "tabela": df_display,
                "fonte": "view_ai_politicas_publicas",
            }

    # 5. Parlamentares, Deputados e Senadores
    if any(
        k in p
        for k in [
            "parlamentar",
            "parlamentares",
            "deputado",
            "deputados",
            "senador",
            "senadores",
            "autor",
            "autores",
            "bancada",
            "relator",
            "quem",
        ]
    ):
        df = carregar_tabela_gold(
            "view_ai_execucao_parlamentar",
            query_filtro="DS_AUTOR != 'Sem informação' AND CD_AUTOR IS NOT NULL AND CD_AUTOR > 0",
            order_by="VL_PAGO DESC",
            limite=10,
        )
        if not df.empty:
            df_top = df.head(5).copy()
            resumos = [extrair_resumo_seguro(row, "parlamentar") for _, row in df_top.iterrows()]
            texto = "**Análise dos Parlamentares com Maior Execução Financeira:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            df_display = formatar_tabela_view(df_top, "parlamentar")
            texto_seguro = validar_resposta_ia(texto).texto_filtrado
            return {
                "tipo": "analitico",
                "texto": texto_seguro,
                "tabela": df_display,
                "fonte": "view_ai_execucao_parlamentar",
            }

    # Resposta genérica orientada
    return {
        "tipo": "orientacao",
        "texto": (
            "Consultei os metadados da camada Gold no BigQuery. Você pode formular perguntas específicas sobre:\n\n"
            "1. **Parlamentares e autores** (ex: *Quais os deputados que mais destinaram recursos?*)\n"
            "2. **Políticas públicas** (ex: *Quanto foi pago para Saúde e Educação?*)\n"
            "3. **Geografia e municípios** (ex: *Quais cidades mais receberam recursos?*)\n"
            "4. **Beneficiários e empresas** (ex: *Quem são os maiores recebedores de emendas?*)\n"
            "5. **Convênios federais** (ex: *Qual o total de recursos pactuados em convênios?*)"
        ),
        "tabela": None,
        "fonte": "Catálogo de Metadados Gold BigQuery",
    }


def main() -> None:
    renderizar_hero(
        titulo="Assistente IA de Consulta Natural",
        subtitulo="Consulte a base oficial de emendas em linguagem natural com suporte a RAG e dados auditados do BigQuery.",
        badge="Google Vertex AI • BigQuery Semantic Views",
    )

    # Inicializa histórico de conversa
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Olá! Sou o Assistente de Inteligência Artificial do Observatório de Emendas Parlamentares. "
                    "Posso consultar diretamente os Data Marts e Views Semânticas da camada Gold no BigQuery. "
                    "Como posso te ajudar hoje?"
                ),
                "fonte": "BigQuery 3_gold.view_ai_*",
            }
        ]

    # Chips de Perguntas Rápidas
    st.markdown("##### 💡 Sugestões de Perguntas Rápidas:")
    cols = st.columns(len(PERGUNTAS_RAPIDAS))
    for i, pergunta in enumerate(PERGUNTAS_RAPIDAS):
        with cols[i]:
            if st.button(pergunta, key=f"chip_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": pergunta})
                resp = responder_pergunta(pergunta)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": resp["texto"],
                        "tabela": resp.get("tabela"),
                        "fonte": resp.get("fonte", "BigQuery"),
                    }
                )
                st.rerun()

    st.markdown("<hr style='border: 1px solid rgba(56, 189, 248, 0.15); margin: 1.5rem 0;'>", unsafe_allow_html=True)

    # Renderiza histórico de mensagens
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("tabela") is not None and not msg["tabela"].empty:
                st.dataframe(msg["tabela"], use_container_width=True, hide_index=True)
            if msg.get("fonte"):
                st.caption(f"📌 Fonte auditada: `{msg['fonte']}`")

    # Input do Chat
    if prompt := st.chat_input("Digite sua dúvida sobre o orçamento de emendas..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando dados da camada Gold no BigQuery..."):
                resp = responder_pergunta(prompt)
                st.markdown(resp["texto"])
                if resp.get("tabela") is not None and not resp["tabela"].empty:
                    st.dataframe(resp["tabela"], use_container_width=True, hide_index=True)
                st.caption(f"📌 Fonte auditada: `{resp.get('fonte', 'BigQuery')}`")

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": resp["texto"],
                    "tabela": resp.get("tabela"),
                    "fonte": resp.get("fonte", "BigQuery"),
                }
            )


if __name__ == "__main__":
    main()
