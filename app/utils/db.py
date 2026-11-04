"""Camada de acesso a dados e caching para o Streamlit via BigQuery."""

import logging
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from etl_emendas_parlamentares.conexao.big_query import get_bigquery_client
from etl_emendas_parlamentares.config.config import GOLD_DATASET

logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_tabela_gold(
    nome_tabela: str,
    query_filtro: str = "",
    colunas: list[str] | None = None,
    limite: int | None = None,
    order_by: str = "",
    **kwargs,
) -> pd.DataFrame:
    """Executa consultas cacheadas sobre Data Marts e Views da Camada Gold no BigQuery.

    Args:
        nome_tabela: Nome da tabela ou view (ex: tbl_execucao_parlamentar ou view_ai_execucao_parlamentar).
        query_filtro: Cláusula WHERE opcional (ex: "DT_ANO = 2023").
        colunas: Lista de colunas a selecionar (padrão: todas "*").
        limite: Limite de registros retornado (LIMIT).
        order_by: Cláusula ORDER BY opcional para ordenação no BigQuery (ex: "VL_PAGO DESC").

    Returns:
        pd.DataFrame: DataFrame com os resultados tipados.
    """
    try:
        client = get_bigquery_client()
        projeto = client.project or os.getenv("GCP_PROJECT_ID", "")

        cols_str = ", ".join(colunas) if colunas else "*"
        sql = f"SELECT {cols_str} FROM `{projeto}.{GOLD_DATASET}.{nome_tabela}`"
        if query_filtro:
            sql += f" WHERE {query_filtro}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limite:
            sql += f" LIMIT {limite}"

        logger.info("Executando consulta BigQuery: %s", sql)
        df = client.query(sql).to_dataframe()
        return df

    except Exception as e:
        logger.warning("Falha ao consultar BigQuery (%s). Tentando fallback local...", e)
        # Fallback local se houver parquet gerado
        caminho_local = Path("data/silver") / f"{nome_tabela}.parquet"
        if caminho_local.exists():
            return pd.read_parquet(caminho_local)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_kpis_macro() -> dict:
    """Carrega os 4 KPIs macro orçamentários para a Home e visão executiva."""
    try:
        client = get_bigquery_client()
        projeto = client.project or os.getenv("GCP_PROJECT_ID", "")

        query_macro = f"""
        SELECT 
            SUM(VL_EMPENHADO) as total_empenhado,
            SUM(VL_LIQUIDADO) as total_liquidado,
            SUM(VL_PAGO) as total_pago,
            SUM(VL_RESTOS_SALDO_A_PAGAR) as total_restos_saldo,
            COUNT(DISTINCT CD_AUTOR) as qtd_parlamentares
        FROM `{projeto}.{GOLD_DATASET}.tbl_execucao_parlamentar`
        """

        query_geo = f"""
        SELECT 
            COUNT(DISTINCT CD_MUNICIPIO_IBGE) as qtd_municipios
        FROM `{projeto}.{GOLD_DATASET}.tbl_distribuicao_geografica`
        WHERE CD_MUNICIPIO_IBGE > 0
        """

        df_macro = client.query(query_macro).to_dataframe()
        df_geo = client.query(query_geo).to_dataframe()

        return {
            "total_empenhado": float(df_macro["total_empenhado"].iloc[0] or 0.0),
            "total_liquidado": float(df_macro["total_liquidado"].iloc[0] or 0.0),
            "total_pago": float(df_macro["total_pago"].iloc[0] or 0.0),
            "total_restos_saldo": float(df_macro["total_restos_saldo"].iloc[0] or 0.0),
            "qtd_parlamentares": int(df_macro["qtd_parlamentares"].iloc[0] or 0),
            "qtd_municipios": int(df_geo["qtd_municipios"].iloc[0] or 0),
        }

    except Exception as e:
        logger.warning("Erro ao carregar KPIs macro: %s", e)
        return {
            "total_empenhado": 0.0,
            "total_liquidado": 0.0,
            "total_pago": 0.0,
            "total_restos_saldo": 0.0,
            "qtd_parlamentares": 0,
            "qtd_municipios": 0,
        }
