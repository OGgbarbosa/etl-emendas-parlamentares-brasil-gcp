"""Motor de Inteligência Artificial Generativa (LLM) com Google Vertex AI (Gemini) e Text-to-SQL + RAG."""

import json
import logging
import os
import re
from dataclasses import dataclass

import pandas as pd
from google import genai
from google.genai import types

import etl_emendas_parlamentares.config.config as _cfg
from app.guardrails import validar_consulta_sql, validar_resposta_ia
from app.utils.formatters import formatar_moeda, formatar_numero, formatar_percentual
from etl_emendas_parlamentares.conexao.big_query import get_bigquery_client
from etl_emendas_parlamentares.scraping.parser import MAPA_ESTADOS_UF, SIGLAS_UF_VALIDAS

logger = logging.getLogger(__name__)

GCP_PROJECT_ID = getattr(_cfg, "GCP_PROJECT_ID", None) or os.getenv("GCP_PROJECT_ID", "")
GCP_LOCATION = getattr(_cfg, "GCP_LOCATION", None) or os.getenv("GCP_LOCATION", "global")
VERTEX_MODEL_NAME = getattr(_cfg, "VERTEX_MODEL_NAME", None) or os.getenv("VERTEX_MODEL_NAME", "gemini-3.8-flash")
GOLD_DATASET = getattr(_cfg, "GOLD_DATASET", "3_gold")
SILVER_DATASET = getattr(_cfg, "SILVER_DATASET", "2_silver")


CATALOGO_SEMANTICO_PROMPT = """
Você é o Agente Especialista em Orçamento Público e Emendas Parlamentares do Brasil, operando sobre o Google Vertex AI e BigQuery.
Você tem acesso de leitura (SOMENTE SELECT) às seguintes Views Semânticas na camada Gold (`{project}.{gold}`) e à Tabela Qualitativa na camada Silver (`{project}.{silver}`):

1. `{project}.{gold}.view_ai_execucao_parlamentar`
   - Grão: [DT_ANO, CD_AUTOR, DS_AUTOR, DS_TIPO_EMENDA, SG_UF]
   - Colunas principais: DT_ANO (INT64), CD_AUTOR (INT64), DS_AUTOR (STRING), DS_TIPO_EMENDA (STRING: INDIVIDUAL, BANCADA, COMISSAO, RELATOR), SG_UF (STRING), QTD_EMENDAS (INT64), VL_EMPENHADO (FLOAT64), VL_LIQUIDADO (FLOAT64), VL_PAGO (FLOAT64), VL_RESTOS_SALDO_A_PAGAR (FLOAT64), TX_EXECUCAO (FLOAT64), DS_RESUMO_SEMANTICO (STRING).

2. `{project}.{gold}.view_ai_politicas_publicas`
   - Grão: [DT_ANO, CD_FUNCAO, DS_FUNCAO, CD_SUBFUNCAO, DS_SUBFUNCAO, DS_TIPO_EMENDA]
   - Colunas principais: DT_ANO (INT64), DS_FUNCAO (STRING: ex. Saúde, Educação, Assistência Social, Urbanismo, Segurança Pública), DS_SUBFUNCAO (STRING), DS_TIPO_EMENDA (STRING), QTD_EMENDAS (INT64), VL_EMPENHADO (FLOAT64), VL_LIQUIDADO (FLOAT64), VL_PAGO (FLOAT64), TX_EXECUCAO (FLOAT64), PC_REPRESENTATIVIDADE_PAGO (FLOAT64), DS_TENDENCIA_YOY (STRING), DS_RESUMO_SEMANTICO (STRING).

3. `{project}.{gold}.view_ai_distribuicao_geografica`
   - Grão: [DT_ANO, SG_REGIAO, SG_UF, DS_MUNICIPIO, CD_MUNICIPIO_IBGE, DS_AMBITO_GEOGRAFICO]
   - Colunas principais: DT_ANO (INT64), SG_REGIAO (STRING: NORTE, NORDESTE, SUDESTE, SUL, CENTRO-OESTE), SG_UF (STRING), DS_MUNICIPIO (STRING), CD_MUNICIPIO_IBGE (INT64, > 0 para municípios específicos), DS_AMBITO_GEOGRAFICO (STRING), QTD_EMENDAS (INT64), QTD_CONVENIOS (INT64), VL_EMPENHADO (FLOAT64), VL_LIQUIDADO (FLOAT64), VL_PAGO (FLOAT64), TX_EXECUCAO (FLOAT64), DS_RESUMO_SEMANTICO (STRING).

4. `{project}.{gold}.view_ai_ranking_favorecidos`
   - Grão: [DT_ANO, CD_FAVORECIDO, DS_FAVORECIDO, DS_TIPO_FAVORECIDO, DS_NATUREZA_JURIDICA, SG_UF_FAVORECIDO]
   - Colunas principais: DT_ANO (INT64), CD_FAVORECIDO (STRING), DS_FAVORECIDO (STRING), DS_TIPO_FAVORECIDO (STRING), SG_UF_FAVORECIDO (STRING), VL_RECEBIDO_ANO (FLOAT64), VL_RECEBIDO_TOTAL_HISTORICO (FLOAT64 - NUNCA aplique SUM() sobre esta coluna), QTD_PARLAMENTARES_DISTINTOS_ANO (INT64), QTD_TRANSFERENCIAS_RECEBIDAS (INT64), DS_RESUMO_SEMANTICO (STRING).

5. `{project}.{gold}.view_ai_painel_convenios`
   - Grão: [DT_ANO, SG_UF, DS_CONVENENTE, DS_FUNCAO]
   - Colunas principais: DT_ANO (INT64), SG_UF (STRING), DS_CONVENENTE (STRING), DS_FUNCAO (STRING), QTD_CONVENIOS (INT64), QTD_EMENDAS_VINCULADAS (INT64), VL_TOTAL_CONVENIADO (FLOAT64), TKM_VALOR_POR_CONVENIO (FLOAT64), DS_RESUMO_SEMANTICO (STRING).

REGRAS OBRIGATÓRIAS DE SQL BIGQUERY:
- Gere apenas instruções `SELECT` válidas no Google Standard SQL.
- NUNCA use `AVG(TX_EXECUCAO)` ao agrupar com `GROUP BY`; se agrupar, calcule `ROUND(SAFE_DIVIDE(SUM(VL_PAGO), SUM(VL_EMPENHADO)) * 100, 2) AS TX_EXECUCAO`.
- Sempre limite o resultado com `LIMIT` (máximo 15 linhas).
- Para buscas textuais em nomes de autores, municípios, funções ou `DS_TIPO_EMENDA`, use SEMPRE `UPPER(coluna) LIKE UPPER('%termo%')` (pois `DS_TIPO_EMENDA` contém valores como `'Emenda Individual - Transferências...'`).
- Ao usar `SUM()`, mantenha os aliases padrões `VL_EMPENHADO`, `VL_LIQUIDADO`, `VL_PAGO`, `QTD_EMENDAS`.
- Ignore registros sentinela (`DS_AUTOR != 'Sem informação'`, `DS_FUNCAO NOT IN ('Sem informação', 'Múltiplo')`).

Responda ESTRITAMENTE em formato JSON válido com as chaves:
{{
  "intencao": "quantitativo" | "qualitativo" | "hibrido",
  "dominio": "parlamentar" | "politica" | "municipio" | "favorecido" | "convenio" | "noticias",
  "sql_query": "SELECT ...",
  "explicacao_consulta": "Breve descrição do que a query consulta"
}}
"""


@dataclass
class PlanoConsultaLLM:
    """Plano de consulta gerado pelo LLM (ou pelo motor NL2SQL de contingência)."""

    intencao: str
    dominio: str
    sql_query: str
    explicacao_consulta: str
    gerado_por_vertex: bool = True
    erro_vertex: str = ""


def criar_cliente_vertex(
    project_id: str | None = None,
    location: str | None = None,
    api_key: str | None = None,
) -> genai.Client:
    """Inicializa o cliente Google GenAI autenticado no Vertex AI (ou via API Key se informada)."""
    chave = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if chave:
        return genai.Client(api_key=chave)

    proj = project_id or GCP_PROJECT_ID
    loc = location or GCP_LOCATION
    return genai.Client(vertexai=True, project=proj, location=loc)


def _limpar_bloco_json(texto: str) -> str:
    """Remove cercas markdown ```json ... ``` de uma resposta do modelo."""
    limpo = texto.strip()
    limpo = re.sub(r"^```(?:json)?\s*", "", limpo, flags=re.IGNORECASE)
    limpo = re.sub(r"\s*```$", "", limpo)
    return limpo.strip()


def extrair_parametros_nl(pergunta: str) -> dict[str, object]:
    """Extrai parâmetros estruturados (ano, UF, função, limite, modalidade) de qualquer pergunta natural."""
    p_lower = pergunta.lower()

    # 1. Ano (2014 a 2026)
    anos = [int(a) for a in re.findall(r"\b(201[4-9]|202[0-6])\b", p_lower)]
    ano = anos[0] if anos else None

    # 2. UF (por nome do estado ou sigla)
    uf_detectada: str | None = None
    for nome_est, sigla in MAPA_ESTADOS_UF.items():
        if re.search(rf"\b{re.escape(nome_est)}\b", p_lower):
            uf_detectada = sigla
            break
    if not uf_detectada:
        for token in re.findall(r"\b([A-Z]{2})\b", pergunta):
            if token in SIGLAS_UF_VALIDAS:
                uf_detectada = token
                break

    # 3. Área / Função de Governo
    mapa_funcoes = {
        "saúde": "Saúde",
        "saude": "Saúde",
        "educação": "Educação",
        "educacao": "Educação",
        "assistência social": "Assistência Social",
        "assistencia social": "Assistência Social",
        "urbanismo": "Urbanismo",
        "segurança": "Segurança Pública",
        "seguranca": "Segurança Pública",
        "agricultura": "Agricultura",
        "desporto": "Desporto e Lazer",
        "esporte": "Desporto e Lazer",
        "cultura": "Cultura",
        "transporte": "Transporte",
        "defesa": "Defesa Nacional",
    }
    funcao_detectada: str | None = None
    for termo, nome_func in mapa_funcoes.items():
        if termo in p_lower:
            funcao_detectada = nome_func
            break

    # 4. Modalidade de Emenda
    modalidade: str | None = None
    if "individual" in p_lower or "individuais" in p_lower or "rp6" in p_lower:
        modalidade = "Individual"
    elif "bancada" in p_lower or "rp7" in p_lower:
        modalidade = "Bancada"
    elif "comissão" in p_lower or "comissao" in p_lower or "rp8" in p_lower:
        modalidade = "Comissão"
    elif "relator" in p_lower or "rp9" in p_lower:
        modalidade = "Relator"

    # 5. Top N / Limite
    match_top = re.search(r"\b(?:top|os|as|primeiros|maiores)\s+(\d{1,2})\b", p_lower)
    limite = int(match_top.group(1)) if match_top else 10
    limite = max(1, min(limite, 15))

    return {
        "ano": ano,
        "uf": uf_detectada,
        "funcao": funcao_detectada,
        "modalidade": modalidade,
        "limite": limite,
    }


def construir_plano_nl2sql_dinamico(
    pergunta: str, project_id: str | None = None, erro_vertex: str = ""
) -> PlanoConsultaLLM:
    """Constrói dinamicamente uma query SQL parametrizada a partir da linguagem natural."""
    proj = project_id or GCP_PROJECT_ID
    p = pergunta.lower().strip()
    params = extrair_parametros_nl(pergunta)
    ano = params["ano"]
    uf = params["uf"]
    funcao = params["funcao"]
    modalidade = params["modalidade"]
    limite = int(params["limite"])  # type: ignore[arg-type]

    # Intenção qualitativa (Notícias, STF, Emendas PIX, Normas)
    if any(
        k in p
        for k in [
            "notícia",
            "noticia",
            "notícias",
            "noticias",
            "stf",
            "pix",
            "rastreabilidade",
            "norma",
            "normas",
            "regra",
            "regras",
            "portaria",
            "imprensa",
            "folha",
            "ebc",
            "observatório",
            "observatorio",
            "o que é",
            "o que sao",
            "o que são",
            "como funciona",
        ]
    ):
        return PlanoConsultaLLM(
            intencao="qualitativo",
            dominio="noticias",
            sql_query="",
            explicacao_consulta="Busca contextual na base de notícias, decisões do STF e normas técnicas (Camada Silver).",
            gerado_por_vertex=False,
            erro_vertex=erro_vertex,
        )

    # 1. Favorecidos / Recebedores / ONGs / Empresas
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
            "fornecedor",
        ]
    ):
        filtros = ["VL_RECEBIDO_ANO > 0", "DS_FAVORECIDO NOT IN ('Sem informação')"]
        if ano:
            filtros.append(f"DT_ANO = {ano}")
        if uf:
            filtros.append(f"SG_UF_FAVORECIDO = '{uf}'")
        if "ong" in p or "sem fins lucrativos" in p:
            filtros.append(
                "UPPER(DS_NATUREZA_JURIDICA) LIKE '%ASSOCIA%' OR UPPER(DS_TIPO_FAVORECIDO) LIKE '%SEM FINS%'"
            )
        where_clause = " AND ".join(f"({f})" for f in filtros)
        sql = (
            f"SELECT DT_ANO, DS_FAVORECIDO, SG_UF_FAVORECIDO, DS_TIPO_FAVORECIDO, "
            f"VL_RECEBIDO_ANO, VL_RECEBIDO_TOTAL_HISTORICO, QTD_TRANSFERENCIAS_RECEBIDAS, DS_RESUMO_SEMANTICO "
            f"FROM `{proj}.{GOLD_DATASET}.view_ai_ranking_favorecidos` "
            f"WHERE {where_clause} ORDER BY VL_RECEBIDO_ANO DESC LIMIT {limite}"
        )
        return PlanoConsultaLLM(
            intencao="quantitativo",
            dominio="favorecido",
            sql_query=sql,
            explicacao_consulta="Consulta parametrizada sobre o ranking de favorecidos e recebedores diretos.",
            gerado_por_vertex=False,
            erro_vertex=erro_vertex,
        )

    # 2. Convênios
    if any(k in p for k in ["convênio", "convenio", "convênios", "convenios", "instrumento", "pactuado", "pactuados"]):
        filtros = ["VL_TOTAL_CONVENIADO > 0"]
        if ano:
            filtros.append(f"DT_ANO = {ano}")
        if uf:
            filtros.append(f"SG_UF = '{uf}'")
        if funcao:
            filtros.append(f"UPPER(DS_FUNCAO) LIKE UPPER('%{funcao}%')")
        where_clause = " AND ".join(filtros)
        sql = (
            f"SELECT DT_ANO, DS_CONVENENTE, SG_UF, DS_FUNCAO, QTD_CONVENIOS, "
            f"VL_TOTAL_CONVENIADO, TKM_VALOR_POR_CONVENIO, DS_RESUMO_SEMANTICO "
            f"FROM `{proj}.{GOLD_DATASET}.view_ai_painel_convenios` "
            f"WHERE {where_clause} ORDER BY VL_TOTAL_CONVENIADO DESC LIMIT {limite}"
        )
        return PlanoConsultaLLM(
            intencao="quantitativo",
            dominio="convenio",
            sql_query=sql,
            explicacao_consulta="Consulta parametrizada sobre o painel de convênios federais.",
            gerado_por_vertex=False,
            erro_vertex=erro_vertex,
        )

    # 3. Municípios / Cidades / Estados / Geografia
    if any(
        k in p
        for k in [
            "município",
            "municipio",
            "municípios",
            "municipios",
            "cidade",
            "cidades",
            "território",
            "região",
            "regiao",
        ]
    ) or (uf and not any(k in p for k in ["deputado", "senador", "parlamentar", "autor"])):
        filtros = ["CD_MUNICIPIO_IBGE > 0", "VL_PAGO > 0"]
        if ano:
            filtros.append(f"DT_ANO = {ano}")
        if uf:
            filtros.append(f"SG_UF = '{uf}'")
        where_clause = " AND ".join(filtros)
        sql = (
            f"SELECT DT_ANO, DS_MUNICIPIO, SG_UF, SG_REGIAO, QTD_EMENDAS, QTD_CONVENIOS, "
            f"VL_EMPENHADO, VL_LIQUIDADO, VL_PAGO, TX_EXECUCAO, DS_RESUMO_SEMANTICO "
            f"FROM `{proj}.{GOLD_DATASET}.view_ai_distribuicao_geografica` "
            f"WHERE {where_clause} ORDER BY VL_PAGO DESC LIMIT {limite}"
        )
        return PlanoConsultaLLM(
            intencao="quantitativo",
            dominio="municipio",
            sql_query=sql,
            explicacao_consulta="Consulta parametrizada sobre a distribuição geográfica por município e UF.",
            gerado_por_vertex=False,
            erro_vertex=erro_vertex,
        )

    # 4. Políticas Públicas / Funções de Governo
    if funcao or any(
        k in p
        for k in [
            "política",
            "politica",
            "políticas",
            "politicas",
            "área",
            "area",
            "áreas",
            "função",
            "funcao",
            "setor",
        ]
    ):
        filtros = ["DS_FUNCAO NOT IN ('Sem informação', 'Múltiplo')", "VL_PAGO > 0"]
        if ano:
            filtros.append(f"DT_ANO = {ano}")
        if funcao:
            filtros.append(f"UPPER(DS_FUNCAO) LIKE UPPER('%{funcao}%')")
        if modalidade:
            filtros.append(f"UPPER(DS_TIPO_EMENDA) LIKE UPPER('%{modalidade}%')")
        where_clause = " AND ".join(filtros)
        sql = (
            f"SELECT DT_ANO, DS_FUNCAO, DS_SUBFUNCAO, DS_TIPO_EMENDA, QTD_EMENDAS, "
            f"VL_EMPENHADO, VL_LIQUIDADO, VL_PAGO, TX_EXECUCAO, PC_REPRESENTATIVIDADE_PAGO, "
            f"DS_TENDENCIA_YOY, DS_RESUMO_SEMANTICO "
            f"FROM `{proj}.{GOLD_DATASET}.view_ai_politicas_publicas` "
            f"WHERE {where_clause} ORDER BY VL_PAGO DESC LIMIT {limite}"
        )
        return PlanoConsultaLLM(
            intencao="quantitativo",
            dominio="politica",
            sql_query=sql,
            explicacao_consulta="Consulta parametrizada sobre investimentos por área de política pública.",
            gerado_por_vertex=False,
            erro_vertex=erro_vertex,
        )

    # 5. Parlamentares / Deputados / Senadores / Autores (Default analítico)
    filtros = ["DS_AUTOR != 'Sem informação'", "CD_AUTOR IS NOT NULL", "CD_AUTOR > 0", "VL_PAGO > 0"]
    if ano:
        filtros.append(f"DT_ANO = {ano}")
    if uf:
        filtros.append(f"SG_UF = '{uf}'")
    if modalidade:
        filtros.append(f"UPPER(DS_TIPO_EMENDA) LIKE UPPER('%{modalidade}%')")
    where_clause = " AND ".join(filtros)
    sql = (
        f"SELECT DT_ANO, DS_AUTOR, SG_UF, DS_TIPO_EMENDA, QTD_EMENDAS, "
        f"VL_EMPENHADO, VL_LIQUIDADO, VL_PAGO, TX_EXECUCAO, DS_RESUMO_SEMANTICO "
        f"FROM `{proj}.{GOLD_DATASET}.view_ai_execucao_parlamentar` "
        f"WHERE {where_clause} ORDER BY VL_PAGO DESC LIMIT {limite}"
    )
    return PlanoConsultaLLM(
        intencao="quantitativo",
        dominio="parlamentar",
        sql_query=sql,
        explicacao_consulta="Consulta parametrizada sobre execução orçamentária por parlamentar/autor.",
        gerado_por_vertex=False,
        erro_vertex=erro_vertex,
    )


def gerar_plano_consulta_vertex(
    pergunta: str,
    model_name: str = VERTEX_MODEL_NAME,
    project_id: str | None = None,
    location: str | None = None,
    api_key: str | None = None,
) -> PlanoConsultaLLM:
    """Usa o Gemini no Vertex AI para interpretar a pergunta natural e gerar o plano Text-to-SQL."""
    proj = project_id or GCP_PROJECT_ID
    system_prompt = CATALOGO_SEMANTICO_PROMPT.format(
        project=proj,
        gold=GOLD_DATASET,
        silver=SILVER_DATASET,
    )

    try:
        client = criar_cliente_vertex(project_id=proj, location=location, api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=f"Pergunta do usuário: {pergunta}",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        texto_json = _limpar_bloco_json(response.text or "{}")
        dados = json.loads(texto_json)

        sql = str(dados.get("sql_query", "")).strip()
        intencao = str(dados.get("intencao", "quantitativo")).strip().lower()
        dominio = str(dados.get("dominio", "parlamentar")).strip().lower()
        explicacao = str(dados.get("explicacao_consulta", "Consulta gerada via Vertex AI Gemini.")).strip()

        if sql and not validar_consulta_sql(sql):
            logger.warning("SQL gerado pelo LLM reprovado pelo Guardrail DQL: %s", sql)
            return construir_plano_nl2sql_dinamico(
                pergunta, project_id=proj, erro_vertex="SQL reprovado pelo Guardrail DQL"
            )

        return PlanoConsultaLLM(
            intencao=intencao,
            dominio=dominio,
            sql_query=sql,
            explicacao_consulta=explicacao,
            gerado_por_vertex=True,
        )

    except Exception as exc:
        msg_erro = str(exc)
        logger.warning("Vertex AI indisponível na geração de SQL (%s). Acionando motor NL2SQL dinâmico.", msg_erro)
        return construir_plano_nl2sql_dinamico(pergunta, project_id=proj, erro_vertex=msg_erro)


def executar_sql_seguro(sql_query: str) -> pd.DataFrame:
    """Valida a query via Guardrail DQL e executa no BigQuery."""
    if not sql_query or not sql_query.strip():
        return pd.DataFrame()

    if not validar_consulta_sql(sql_query):
        raise ValueError("Consulta bloqueada pelo Guardrail SQL: apenas instruções SELECT de leitura são permitidas.")

    bq_client = get_bigquery_client()
    return bq_client.query(sql_query).to_dataframe()


def sintetizar_resposta_vertex(
    pergunta: str,
    df_resultado: pd.DataFrame,
    df_noticias: pd.DataFrame,
    plano: PlanoConsultaLLM,
    model_name: str = VERTEX_MODEL_NAME,
    project_id: str | None = None,
    location: str | None = None,
    api_key: str | None = None,
) -> str:
    """Usa o Gemini no Vertex AI para redigir uma resposta conversacional fundamentada nos dados."""
    resumo_dados = "Nenhum registro quantitativo retornado."
    if not df_resultado.empty:
        df_amostra = df_resultado.head(8).copy()
        resumo_dados = df_amostra.to_json(orient="records", force_ascii=False, date_format="iso")

    resumo_noticias = "Nenhuma notícia complementar."
    if not df_noticias.empty:
        cols_not = [
            c
            for c in ["nome_fonte", "data_publicacao", "titulo", "lead_resumo", "url_artigo"]
            if c in df_noticias.columns
        ]
        resumo_noticias = df_noticias[cols_not].head(4).to_json(orient="records", force_ascii=False, date_format="iso")

    prompt_sintese = (
        f"Pergunta do usuário: {pergunta}\n\n"
        f"Dados Oficiais Auditados do BigQuery (Camada Gold):\n{resumo_dados}\n\n"
        f"Artigos e Normas Técnicas (Camada Silver - fato_noticias_contexto):\n{resumo_noticias}\n\n"
        "Instruções de resposta:\n"
        "1. Responda em português brasileiro claro, analítico e objetivo.\n"
        "2. Utilize EXCLUSIVAMENTE os números fornecidos nos dados acima. Formate valores monetários em Reais (R$ X.XXX,XX) e percentuais com %.\n"
        "3. Se houver artigos relevantes, cite a fonte com link em Markdown [Título](url_artigo).\n"
        "4. Nunca exiba 'nan', 'null' ou 'None'."
    )

    if plano.gerado_por_vertex:
        try:
            client = criar_cliente_vertex(project_id=project_id, location=location, api_key=api_key)
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt_sintese,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            if resp.text and resp.text.strip():
                return validar_resposta_ia(resp.text.strip()).texto_filtrado
        except Exception as exc:
            logger.warning("Falha na síntese Vertex AI (%s). Usando síntese estruturada.", exc)

    # Síntese estruturada determinística caso a API Vertex AI esteja aguardando ativação no GCP
    linhas: list[str] = []
    if not df_resultado.empty:
        linhas.append(f"### 📊 Análise Fundamentada nos Dados (`{plano.dominio.upper()}`)\n")
        linhas.append(f"*{plano.explicacao_consulta}*\n")
        for _, row in df_resultado.head(5).iterrows():
            resumo_sem = str(row.get("DS_RESUMO_SEMANTICO", "")).strip()
            if resumo_sem and resumo_sem.lower() not in ["nan", "none", "null"]:
                linhas.append(f"• {resumo_sem}")
            elif "DS_AUTOR" in row:
                linhas.append(
                    f"• **{row.get('DS_AUTOR', 'N/D')}** ({row.get('SG_UF', 'NACI')}, {row.get('DT_ANO', 'N/D')}): "
                    f"Empenhado {formatar_moeda(row.get('VL_EMPENHADO', 0))} | "
                    f"Pago **{formatar_moeda(row.get('VL_PAGO', 0))}** "
                    f"(Execução: {formatar_percentual(row.get('TX_EXECUCAO', 0))})."
                )
            elif "DS_MUNICIPIO" in row:
                linhas.append(
                    f"• **{row.get('DS_MUNICIPIO', 'N/D')} - {row.get('SG_UF', 'NACI')}** ({row.get('DT_ANO', 'N/D')}): "
                    f"Pago **{formatar_moeda(row.get('VL_PAGO', 0))}** em {formatar_numero(row.get('QTD_EMENDAS', 0))} emenda(s) "
                    f"(Execução: {formatar_percentual(row.get('TX_EXECUCAO', 0))})."
                )
            elif "DS_FAVORECIDO" in row:
                linhas.append(
                    f"• **{row.get('DS_FAVORECIDO', 'N/D')}** ({row.get('SG_UF_FAVORECIDO', 'NACI')}, {row.get('DT_ANO', 'N/D')}): "
                    f"Recebido no ano **{formatar_moeda(row.get('VL_RECEBIDO_ANO', 0))}** "
                    f"(Histórico: {formatar_moeda(row.get('VL_RECEBIDO_TOTAL_HISTORICO', 0))})."
                )
            elif "DS_CONVENENTE" in row:
                linhas.append(
                    f"• **{row.get('DS_CONVENENTE', 'N/D')}** ({row.get('SG_UF', 'NACI')} — {row.get('DS_FUNCAO', 'Geral')}): "
                    f"{formatar_numero(row.get('QTD_CONVENIOS', 0))} convênio(s) somando **{formatar_moeda(row.get('VL_TOTAL_CONVENIADO', 0))}**."
                )
            elif "DS_FUNCAO" in row:
                linhas.append(
                    f"• **{row.get('DS_FUNCAO', 'Geral')}** ({row.get('DS_SUBFUNCAO', 'Geral')}, {row.get('DT_ANO', 'N/D')}): "
                    f"Pago **{formatar_moeda(row.get('VL_PAGO', 0))}** "
                    f"(Execução: {formatar_percentual(row.get('TX_EXECUCAO', 0))})."
                )

    if not df_noticias.empty and (plano.intencao in ["qualitativo", "hibrido"] or df_resultado.empty):
        linhas.append("\n### 📰 Contexto Jornalístico, Decisões do STF & Normas Técnicas\n")
        for _, art in df_noticias.head(4).iterrows():
            dt_val = art.get("data_publicacao")
            dt_str = pd.to_datetime(dt_val, errors="coerce").strftime("%d/%m/%Y") if pd.notna(dt_val) else "Recente"
            linhas.append(
                f"• **[{art.get('nome_fonte', 'Fonte')} — {dt_str}]** "
                f"[{art.get('titulo', 'Artigo')}]({art.get('url_artigo', '#')})\n"
                f"  *{art.get('lead_resumo', '')}*"
            )

    texto_final = "\n\n".join(linhas) if linhas else "Não foram encontrados registros para os filtros informados."
    return validar_resposta_ia(texto_final).texto_filtrado
