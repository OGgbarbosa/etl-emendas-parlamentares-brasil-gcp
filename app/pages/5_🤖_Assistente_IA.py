"""Página 5: Assistente IA & Chatbot em Linguagem Natural com Gemini & BigQuery."""

import sys
from pathlib import Path

_raiz = str(Path(__file__).resolve().parent.parent.parent)
_src = str(Path(_raiz) / "src")
for p in [_raiz, _src]:
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st

from app.utils.db import carregar_tabela_gold
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


def responder_pergunta(prompt: str) -> dict:
    """Roteia a pergunta em linguagem natural para as views semânticas de IA."""
    p = prompt.lower()

    if any(k in p for k in ["parlamentar", "deputado", "senador", "autor", "quem"]):
        df = carregar_tabela_gold("view_ai_execucao_parlamentar", limite=15)
        if not df.empty:
            df_top = df.sort_values("VL_PAGO", ascending=False).head(5)
            resumos = df_top["DS_RESUMO_SEMANTICO"].tolist()
            texto = "**Análise dos Parlamentares com Maior Execução Financeira:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            return {
                "tipo": "analitico",
                "texto": texto,
                "tabela": df_top[["DS_AUTOR", "SG_UF", "VL_EMPENHADO", "VL_PAGO", "TX_EXECUCAO"]],
                "fonte": "view_ai_execucao_parlamentar",
            }

    if any(k in p for k in ["política", "politica", "saúde", "saude", "educação", "educacao", "área", "função"]):
        df = carregar_tabela_gold("view_ai_politicas_publicas", limite=20)
        if not df.empty:
            df_top = df.sort_values("VL_PAGO", ascending=False).head(5)
            resumos = df_top["DS_RESUMO_SEMANTICO"].tolist()
            texto = "**Alocação Setorial em Políticas Públicas:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            return {
                "tipo": "analitico",
                "texto": texto,
                "tabela": df_top[["DS_FUNCAO", "DS_SUBFUNCAO", "VL_EMPENHADO", "VL_PAGO", "DS_TENDENCIA_YOY"]],
                "fonte": "view_ai_politicas_publicas",
            }

    if any(k in p for k in ["município", "municipio", "cidade", "estado", "uf", "região", "geografia"]):
        df = carregar_tabela_gold("view_ai_distribuicao_geografica", query_filtro="CD_MUNICIPIO_IBGE > 0", limite=20)
        if not df.empty:
            df_top = df.sort_values("VL_PAGO", ascending=False).head(5)
            resumos = df_top["DS_RESUMO_SEMANTICO"].tolist()
            texto = "**Distribuição Territorial e Cidades Mais Beneficiadas:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            return {
                "tipo": "analitico",
                "texto": texto,
                "tabela": df_top[["DS_MUNICIPIO", "SG_UF", "VL_PAGO", "QTD_EMENDAS", "QTD_CONVENIOS"]],
                "fonte": "view_ai_distribuicao_geografica",
            }

    if any(k in p for k in ["favorecido", "empresa", "ong", "prefeitura", "recebedor", "beneficiário", "beneficiario"]):
        df = carregar_tabela_gold("view_ai_ranking_favorecidos", limite=20)
        if not df.empty:
            df_top = df.sort_values("VL_RECEBIDO_ANO", ascending=False).head(5)
            resumos = df_top["DS_RESUMO_SEMANTICO"].tolist()
            texto = "**Ranking dos Principais Entes e Favorecidos:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            return {
                "tipo": "analitico",
                "texto": texto,
                "tabela": df_top[
                    [
                        "DS_FAVORECIDO",
                        "SG_UF_FAVORECIDO",
                        "DS_TIPO_FAVORECIDO",
                        "VL_RECEBIDO_ANO",
                        "VL_RECEBIDO_TOTAL_HISTORICO",
                    ]
                ],
                "fonte": "view_ai_ranking_favorecidos",
            }

    if any(k in p for k in ["convênio", "convenio", "instrumento", "contrato"]):
        df = carregar_tabela_gold("view_ai_painel_convenios", limite=20)
        if not df.empty:
            df_top = df.sort_values("VL_TOTAL_CONVENIADO", ascending=False).head(5)
            resumos = df_top["DS_RESUMO_SEMANTICO"].tolist()
            texto = "**Consolidação do Painel de Convênios Federais:**\n\n"
            for r in resumos:
                texto += f"• {r}\n\n"
            return {
                "tipo": "analitico",
                "texto": texto,
                "tabela": df_top[["DS_CONVENENTE", "SG_UF", "DS_FUNCAO", "VL_TOTAL_CONVENIADO", "QTD_CONVENIOS"]],
                "fonte": "view_ai_painel_convenios",
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
        titulo="🤖 Assistente IA de <span>Consulta Natural</span>",
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
