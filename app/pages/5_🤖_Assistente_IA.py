"""Página 5: Assistente IA & Chatbot em Linguagem Natural com Google Vertex AI (Gemini) & BigQuery."""

import importlib
import sys
from pathlib import Path

_raiz = str(Path(__file__).resolve().parent.parent.parent)
_src = str(Path(_raiz) / "src")
for p in [_raiz, _src]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import streamlit as st

import app.utils.db as _db_mod
import app.utils.llm_vertex as _llm_mod
from app.guardrails import validar_prompt_usuario, validar_resposta_ia
from app.utils.formatters import formatar_moeda, formatar_numero, formatar_percentual
from app.utils.styles import aplicar_estilos_globais, renderizar_hero

if not hasattr(_db_mod, "carregar_noticias_contexto"):
    _db_mod = importlib.reload(_db_mod)
if getattr(_llm_mod, "GCP_LOCATION", "") != "global":
    _llm_mod = importlib.reload(_llm_mod)

carregar_noticias_contexto = _db_mod.carregar_noticias_contexto
carregar_tabela_gold = _db_mod.carregar_tabela_gold

st.set_page_config(
    page_title="Assistente IA Vertex - Emendas",
    page_icon="🤖",
    layout="wide",
)

aplicar_estilos_globais()

PERGUNTAS_RAPIDAS = [
    "Quais os parlamentares que mais destinaram recursos pagos?",
    "Quanto foi destinado para a Saúde em 2024?",
    "Quais municípios da Bahia receberam os maiores volumes de recursos?",
    "Quem são os maiores recebedores e favorecidos de emendas?",
    "O que o STF decidiu sobre rastreabilidade das Emendas PIX?",
]

MAPA_ROTULOS_AMIGAVEIS: dict[str, str] = {
    "DT_ANO": "Ano",
    "DS_AUTOR": "Parlamentar / Autor",
    "CD_AUTOR": "Cód. Autor",
    "SG_UF": "UF",
    "SG_UF_FAVORECIDO": "UF",
    "SG_REGIAO": "Região",
    "DS_TIPO_EMENDA": "Modalidade de Emenda",
    "DS_FUNCAO": "Área / Função",
    "DS_SUBFUNCAO": "Subfunção",
    "DS_MUNICIPIO": "Município / Destino",
    "DS_FAVORECIDO": "Entidade / Beneficiário",
    "DS_TIPO_FAVORECIDO": "Tipo de Favorecido",
    "DS_NATUREZA_JURIDICA": "Natureza Jurídica",
    "DS_CONVENENTE": "Convenente / Executor",
    "VL_EMPENHADO": "Valor Empenhado",
    "VL_TOTAL_EMPENHADO": "Valor Empenhado",
    "VL_LIQUIDADO": "Valor Liquidado",
    "VL_TOTAL_LIQUIDADO": "Valor Liquidado",
    "VL_PAGO": "Valor Pago",
    "VL_TOTAL_PAGO": "Valor Pago",
    "VL_RECEBIDO_ANO": "Valor Recebido no Ano",
    "VL_RECEBIDO_TOTAL_HISTORICO": "Total Histórico Acumulado",
    "VL_TOTAL_CONVENIADO": "Valor Total Conveniado",
    "TKM_VALOR_POR_CONVENIO": "Ticket Médio por Convênio",
    "TKM_PAGO_POR_EMENDA": "Ticket Médio por Emenda",
    "TX_EXECUCAO": "Taxa de Execução",
    "TX_LIQUIDACAO": "Taxa de Liquidação",
    "PC_REPRESENTATIVIDADE_PAGO": "Share no Ano",
    "DS_TENDENCIA_YOY": "Tendência Anual",
    "QTD_EMENDAS": "Qtd. Emendas",
    "QTD_CONVENIOS": "Qtd. Convênios",
    "QTD_TRANSFERENCIAS_RECEBIDAS": "Transferências",
}


def _formatar_lista_array(valor: object) -> str:
    """Formata colunas ARRAY<STRING> do BigQuery/Parquet para string legível."""
    if valor is None:
        return "-"
    if isinstance(valor, (list, tuple, set)):
        itens = [str(x).strip() for x in valor if str(x).strip()]
        return ", ".join(itens) if itens else "-"
    if hasattr(valor, "tolist"):
        lista = valor.tolist()
        if isinstance(lista, list):
            itens = [str(x).strip() for x in lista if str(x).strip()]
            return ", ".join(itens) if itens else "-"
    texto = str(valor).strip()
    return texto if texto and texto.lower() not in ["nan", "none", "[]"] else "-"


def formatar_tabela_noticias(df: pd.DataFrame) -> pd.DataFrame:
    """Formata a tabela fato_noticias_contexto com rótulos amigáveis em português."""
    if df.empty:
        return df

    datas_fmt = pd.to_datetime(df["data_publicacao"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("-")
    return pd.DataFrame(
        {
            "Fonte Oficial": df["nome_fonte"].fillna("-"),
            "Data": datas_fmt,
            "Título / Manchete": df["titulo"].fillna("-"),
            "Tags Temáticas": df.get("tags", pd.Series([[]] * len(df))).apply(_formatar_lista_array),
            "UFs Citadas": df.get("ufs_mencionadas", pd.Series([[]] * len(df))).apply(_formatar_lista_array),
            "Palavras": df.get("qtd_palavras", pd.Series([0] * len(df))).apply(formatar_numero),
            "Link Original": df["url_artigo"].fillna("-"),
        }
    )


def formatar_tabela_view(df: pd.DataFrame, tipo: str = "") -> pd.DataFrame:
    """Transforma nomes de campos de qualquer query em rótulos amigáveis, BRL e %."""
    if df.empty:
        return df

    df_out = pd.DataFrame()
    colunas_ocultas = {"DS_RESUMO_SEMANTICO", "DH_PROCESSAMENTO", "CD_AUTOR", "CD_MUNICIPIO_IBGE"}

    for col in df.columns:
        col_up = col.upper()
        if col_up in colunas_ocultas:
            continue

        rotulo = MAPA_ROTULOS_AMIGAVEIS.get(col_up, col.replace("_", " ").title())
        serie = df[col]

        if col_up.startswith(("VL_", "TKM_", "TOTAL_", "VALOR_")) and pd.api.types.is_numeric_dtype(serie):
            df_out[rotulo] = serie.fillna(0.0).apply(formatar_moeda)
        elif col_up.startswith(("TX_", "PC_", "TAXA_", "PERC_")) and pd.api.types.is_numeric_dtype(serie):
            df_out[rotulo] = serie.fillna(0.0).apply(formatar_percentual)
        elif col_up.startswith("QTD_") and pd.api.types.is_numeric_dtype(serie):
            df_out[rotulo] = serie.fillna(0).apply(formatar_numero)
        elif col_up == "DT_ANO":
            df_out[rotulo] = serie.fillna(0).astype(int).astype(str)
        else:
            df_out[rotulo] = serie.fillna("-").astype(str)

    return df_out


def buscar_noticias_relevantes(prompt: str, limite: int = 4) -> pd.DataFrame:
    """Filtra os artigos mais aderentes de 2_silver.fato_noticias_contexto para compor o RAG."""
    df_noticias = carregar_noticias_contexto(limite=25)
    if df_noticias.empty:
        return pd.DataFrame()

    termos = [t for t in prompt.lower().split() if len(t) > 3]
    df_rank = df_noticias.copy()

    def pontuar(row: pd.Series) -> int:
        bloco = (
            f"{row.get('titulo', '')} {row.get('subtitulo', '')} "
            f"{row.get('conteudo_texto', '')} {_formatar_lista_array(row.get('tags'))}"
        ).lower()
        return sum(2 if t in str(row.get("titulo", "")).lower() else 1 for t in termos if t in bloco)

    df_rank["_score"] = df_rank.apply(pontuar, axis=1)
    df_filt = df_rank[df_rank["_score"] > 0].sort_values("_score", ascending=False)
    if df_filt.empty:
        df_filt = df_rank

    return df_filt.head(limite).drop(columns=["_score"], errors="ignore")


def responder_pergunta(
    prompt: str,
    model_name: str = "gemini-3.8-flash",
    location: str = "global",
    api_key: str | None = None,
) -> dict:
    """Executa o fluxo completo: Guardrails ➔ Vertex AI LLM (Text-to-SQL) ➔ BigQuery ➔ Síntese RAG."""
    # 1. Guardrail de Entrada
    val_in = validar_prompt_usuario(prompt)
    if not val_in.valido:
        return {
            "tipo": "bloqueio",
            "texto": f"⚠️ **Aviso de Governança dos Guardrails:** {val_in.motivo}",
            "tabela": None,
            "sql": "",
            "fonte": "Guardrails de Entrada",
        }

    pergunta_limpa = val_in.prompt_higienizado.strip()

    # 2. Geração do Plano de Consulta via Vertex AI Gemini (com contingência NL2SQL dinâmica)
    plano = _llm_mod.gerar_plano_consulta_vertex(
        pergunta=pergunta_limpa,
        model_name=model_name,
        location=location,
        api_key=api_key,
    )

    # 3. Execução da Query SQL gerada no BigQuery (validada por Guardrail DQL)
    df_resultado = pd.DataFrame()
    if plano.sql_query:
        try:
            df_resultado = _llm_mod.executar_sql_seguro(plano.sql_query)
        except Exception as exc:
            # Se a query livre do LLM tiver algum erro de sintaxe, usa a query parametrizada segura
            plano_fallback = _llm_mod.construir_plano_nl2sql_dinamico(pergunta_limpa, erro_vertex=str(exc))
            plano = plano_fallback
            if plano.sql_query:
                try:
                    df_resultado = _llm_mod.executar_sql_seguro(plano.sql_query)
                except Exception:
                    df_resultado = pd.DataFrame()

    # 4. Recuperação de Contexto Qualitativo (RAG em 2_silver.fato_noticias_contexto)
    df_noticias = buscar_noticias_relevantes(pergunta_limpa, limite=4)

    # 5. Síntese Conversacional com Vertex AI Gemini + Guardrail de Saída
    texto_resposta = _llm_mod.sintetizar_resposta_vertex(
        pergunta=pergunta_limpa,
        df_resultado=df_resultado,
        df_noticias=df_noticias,
        plano=plano,
        model_name=model_name,
        location=location,
        api_key=api_key,
    )

    # 6. Formatação da Tabela para Exibição (Rótulos Amigáveis, BRL e %)
    if not df_resultado.empty:
        df_display = formatar_tabela_view(df_resultado, plano.dominio)
        fonte_label = (
            f"Vertex AI ({model_name}) • BigQuery 3_gold"
            if plano.gerado_por_vertex
            else f"Motor NL2SQL • BigQuery 3_gold ({plano.dominio})"
        )
    elif not df_noticias.empty:
        df_display = formatar_tabela_noticias(df_noticias)
        fonte_label = (
            f"Vertex AI ({model_name}) • 2_silver.fato_noticias_contexto"
            if plano.gerado_por_vertex
            else "RAG 2_silver.fato_noticias_contexto"
        )
    else:
        df_display = pd.DataFrame()
        fonte_label = "BigQuery Gold & Silver"

    return {
        "tipo": plano.intencao,
        "texto": validar_resposta_ia(texto_resposta).texto_filtrado,
        "tabela": df_display,
        "sql": plano.sql_query,
        "gerado_por_vertex": plano.gerado_por_vertex,
        "erro_vertex": plano.erro_vertex,
        "fonte": fonte_label,
    }


def main() -> None:
    renderizar_hero(
        titulo="Assistente IA com Google Vertex AI (Gemini)",
        subtitulo="Faça qualquer pergunta em linguagem natural. O modelo Gemini traduz sua dúvida em SQL no BigQuery e cruza com notícias e normas da camada Silver.",
        badge="Google Vertex AI • Text-to-SQL Dinâmico & RAG Híbrido",
    )

    # Barra Lateral: Configurações do Motor LLM Vertex AI
    with st.sidebar:
        st.markdown("### 🧠 Motor LLM (Vertex AI)")
        modelo_sel = st.selectbox(
            "Modelo Gemini:",
            ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-4-argon", "gemini-2.5-flash"],
            index=0,
            key="vertex_model_select",
        )
        regiao_sel = st.selectbox(
            "Região GCP (Vertex AI):",
            ["global", "us-central1", "southamerica-east1"],
            index=0,
            key="vertex_location_select",
        )
        api_key_input = st.text_input(
            "Gemini API Key (Opcional):",
            type="password",
            help="Por padrão utiliza a Service Account do GCP via Vertex AI. Se desejar, informe uma chave do Google AI Studio.",
            key="vertex_api_key_input",
        )
        st.caption(f"Projeto GCP: `{_llm_mod.GCP_PROJECT_ID}`")

    # Inicializa histórico de conversa
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Olá! Sou o Assistente de IA do Observatório de Emendas Parlamentares, integrado ao **Google Vertex AI (Gemini)**. "
                    "Você pode fazer perguntas abertas em linguagem natural — por exemplo, filtrando por **ano, estado (UF), município, deputado, área da Saúde/Educação ou decisões do STF**."
                ),
                "fonte": "Vertex AI Gemini • BigQuery 3_gold & 2_silver",
            }
        ]

    # Chips de Perguntas Rápidas
    st.markdown("##### 💡 Experimente perguntar em linguagem natural:")
    cols = st.columns(len(PERGUNTAS_RAPIDAS))
    for i, pergunta in enumerate(PERGUNTAS_RAPIDAS):
        with cols[i]:
            if st.button(pergunta, key=f"chip_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": pergunta})
                resp = responder_pergunta(
                    pergunta,
                    model_name=modelo_sel,
                    location=regiao_sel,
                    api_key=api_key_input or None,
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": resp["texto"],
                        "tabela": resp.get("tabela"),
                        "sql": resp.get("sql", ""),
                        "erro_vertex": resp.get("erro_vertex", ""),
                        "fonte": resp.get("fonte", "BigQuery"),
                    }
                )
                st.rerun()

    # Painel de Contexto Jornalístico, Normas e Observatórios Cívicos (2_silver.fato_noticias_contexto)
    with st.expander(
        "📰 Acervo de Contexto Jornalístico, Normas & Observatórios Cívicos (Camada Silver)", expanded=False
    ):
        df_contexto = carregar_noticias_contexto(limite=30)
        if not df_contexto.empty:
            fontes_disp = ["Todas"] + sorted(df_contexto["nome_fonte"].dropna().unique().tolist())
            fonte_sel = st.selectbox("Filtrar por Fonte Oficial:", fontes_disp, key="filtro_fonte_scraping")
            df_exib = df_contexto if fonte_sel == "Todas" else df_contexto[df_contexto["nome_fonte"] == fonte_sel]
            for _, art in df_exib.iterrows():
                dt_pub = pd.to_datetime(art.get("data_publicacao"), errors="coerce")
                dt_txt = dt_pub.strftime("%d/%m/%Y") if pd.notna(dt_pub) else "Recente"
                tags_txt = _formatar_lista_array(art.get("tags"))
                ufs_txt = _formatar_lista_array(art.get("ufs_mencionadas"))
                st.markdown(
                    f"**[{art.get('nome_fonte')} • {dt_txt}]** "
                    f"[{art.get('titulo')}]({art.get('url_artigo')})  \n"
                    f"<span style='color:#94A3B8; font-size:0.9rem;'>{art.get('lead_resumo', '')}</span>  \n"
                    f"<small>🏷️ <b>Tags:</b> {tags_txt} | 🗺️ <b>UFs:</b> {ufs_txt}</small>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<hr style='border: 0.5px solid rgba(255,255,255,0.06); margin: 0.6rem 0;'>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Nenhum artigo carregado ainda em `2_silver.fato_noticias_contexto`.")

    st.markdown("<hr style='border: 1px solid rgba(56, 189, 248, 0.15); margin: 1.5rem 0;'>", unsafe_allow_html=True)

    # Renderiza histórico de mensagens
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("tabela") is not None and not msg["tabela"].empty:
                st.dataframe(msg["tabela"], use_container_width=True, hide_index=True)
            if msg.get("sql"):
                with st.expander("🔍 Ver Consulta SQL Gerada (Text-to-SQL BigQuery)"):
                    st.code(msg["sql"], language="sql")
            if msg.get("erro_vertex") and "SERVICE_DISABLED" in str(msg.get("erro_vertex")):
                st.caption(
                    "ℹ️ *Nota: A API `aiplatform.googleapis.com` ainda não foi habilitada no Console deste projeto GCP. "
                    f"[Clique aqui para ativar a API Vertex AI no Google Cloud](https://console.developers.google.com/apis/api/aiplatform.googleapis.com/overview?project={_llm_mod.GCP_PROJECT_ID}) "
                    "ou insira uma Gemini API Key na barra lateral. Enquanto isso, o motor NL2SQL dinâmico processou sua consulta diretamente no BigQuery.*"
                )
            if msg.get("fonte"):
                st.caption(f"📌 Fonte auditada: `{msg['fonte']}`")

    # Input do Chat
    if prompt := st.chat_input(
        "Faça sua pergunta em linguagem natural (ex: Quais deputados do RJ mais destinaram emendas em 2024?)..."
    ):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Processando pergunta em linguagem natural com Vertex AI & BigQuery..."):
                resp = responder_pergunta(
                    prompt,
                    model_name=modelo_sel,
                    location=regiao_sel,
                    api_key=api_key_input or None,
                )
                st.markdown(resp["texto"])
                if resp.get("tabela") is not None and not resp["tabela"].empty:
                    st.dataframe(resp["tabela"], use_container_width=True, hide_index=True)
                if resp.get("sql"):
                    with st.expander("🔍 Ver Consulta SQL Gerada (Text-to-SQL BigQuery)"):
                        st.code(resp["sql"], language="sql")
                if resp.get("erro_vertex") and "SERVICE_DISABLED" in str(resp.get("erro_vertex")):
                    st.caption(
                        "ℹ️ *Nota: A API `aiplatform.googleapis.com` ainda não foi habilitada no Console deste projeto GCP. "
                        f"[Clique aqui para ativar a API Vertex AI no Google Cloud](https://console.developers.google.com/apis/api/aiplatform.googleapis.com/overview?project={_llm_mod.GCP_PROJECT_ID}) "
                        "ou insira uma Gemini API Key na barra lateral. Enquanto isso, o motor NL2SQL dinâmico processou sua consulta diretamente no BigQuery.*"
                    )
                st.caption(f"📌 Fonte auditada: `{resp.get('fonte', 'BigQuery')}`")

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": resp["texto"],
                    "tabela": resp.get("tabela"),
                    "sql": resp.get("sql", ""),
                    "erro_vertex": resp.get("erro_vertex", ""),
                    "fonte": resp.get("fonte", "BigQuery"),
                }
            )


if __name__ == "__main__":
    main()
