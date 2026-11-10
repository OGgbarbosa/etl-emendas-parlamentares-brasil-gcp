"""Ingestão dos payloads brutos de Web Scraping nas tabelas 2_silver.raw_scraping_<fonte>."""

import logging
import os
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

from etl_emendas_parlamentares.conexao.big_query import get_bigquery_client
from etl_emendas_parlamentares.config.config import (
    DIRETORIO_SCRAPING_LOCAL,
    SILVER_DATASET,
)
from etl_emendas_parlamentares.ingestao.upload_silver import garantir_dataset_existe
from etl_emendas_parlamentares.scraping.client import RespostaColeta
from etl_emendas_parlamentares.scraping.fontes import FONTES_SCRAPING, obter_fonte

logger = logging.getLogger(__name__)

SCHEMA_RAW_SCRAPING = [
    bigquery.SchemaField("id_requisicao", "STRING", mode="REQUIRED", description="UUID único da requisição"),
    bigquery.SchemaField("url_artigo", "STRING", mode="REQUIRED", description="URL canônica do artigo coletado"),
    bigquery.SchemaField("nome_fonte", "STRING", mode="REQUIRED", description="Identificador da fonte (ex: folha)"),
    bigquery.SchemaField("dh_coleta", "TIMESTAMP", mode="REQUIRED", description="Data e hora exata da raspagem (UTC)"),
    bigquery.SchemaField("http_status", "INT64", mode="REQUIRED", description="Código HTTP retornado (ex: 200, 301)"),
    bigquery.SchemaField(
        "payload_bruto", "STRING", mode="REQUIRED", description="HTML ou JSON íntegro retornado pela página"
    ),
    bigquery.SchemaField(
        "hash_conteudo", "STRING", mode="REQUIRED", description="Hash SHA-256 do payload para idempotência"
    ),
]


def gerar_ddl_tabela_raw(projeto: str, dataset_id: str, tabela_raw: str) -> str:
    """Gera a instrução DDL para criação da tabela bruta com clusterização."""
    return f"""
CREATE TABLE IF NOT EXISTS `{projeto}.{dataset_id}.{tabela_raw}` (
    id_requisicao STRING NOT NULL OPTIONS(description="UUID único da requisição"),
    url_artigo STRING NOT NULL OPTIONS(description="URL canônica do artigo coletado"),
    nome_fonte STRING NOT NULL OPTIONS(description="Identificador da fonte (ex: folha)"),
    dh_coleta TIMESTAMP NOT NULL OPTIONS(description="Data e hora exata da raspagem (UTC)"),
    http_status INT64 NOT NULL OPTIONS(description="Código HTTP retornado (ex: 200, 301)"),
    payload_bruto STRING NOT NULL OPTIONS(description="HTML ou JSON íntegro retornado pela página"),
    hash_conteudo STRING NOT NULL OPTIONS(description="Hash SHA-256 do payload para idempotência")
)
CLUSTER BY dh_coleta, url_artigo;
""".strip()


def garantir_tabelas_raw_existem(
    client: bigquery.Client | None = None,
    dataset_id: str = SILVER_DATASET,
) -> list[str]:
    """Garante a existência de todas as 6 tabelas brutas raw_scraping_* no BigQuery."""
    bq_client = client or get_bigquery_client()
    projeto = str(bq_client.project or os.getenv("GCP_PROJECT_ID") or "")
    garantir_dataset_existe(bq_client, dataset_id)

    tabelas_criadas: list[str] = []
    for fonte in FONTES_SCRAPING.values():
        ddl = gerar_ddl_tabela_raw(projeto, dataset_id, fonte.tabela_raw)
        bq_client.query(ddl).result()
        fqn = f"{projeto}.{dataset_id}.{fonte.tabela_raw}"
        tabelas_criadas.append(fqn)
        logger.info("Tabela bruta verificada/criada: %s", fqn)

    return tabelas_criadas


def obter_hashes_existentes(
    client: bigquery.Client,
    projeto: str,
    dataset_id: str,
    tabela_raw: str,
) -> set[str]:
    """Consulta os hashes SHA-256 já registrados na tabela bruta para garantir idempotência."""
    sql = f"SELECT DISTINCT hash_conteudo FROM `{projeto}.{dataset_id}.{tabela_raw}`"
    try:
        df = client.query(sql).to_dataframe()
        if df.empty or "hash_conteudo" not in df.columns:
            return set()
        return set(df["hash_conteudo"].dropna().astype(str).tolist())
    except Exception:
        return set()


def filtrar_respostas_ineditas(
    respostas: list[RespostaColeta],
    hashes_existentes: set[str],
) -> list[RespostaColeta]:
    """Filtra apenas coletas cujo hash_conteudo ainda não foi persistido."""
    novas: list[RespostaColeta] = []
    vistos_lote: set[str] = set()
    for resp in respostas:
        if resp.hash_conteudo not in hashes_existentes and resp.hash_conteudo not in vistos_lote:
            novas.append(resp)
            vistos_lote.add(resp.hash_conteudo)
    return novas


def salvar_parquet_raw_local(
    id_fonte: str,
    respostas: list[RespostaColeta],
    diretorio_local: str | Path | None = None,
) -> Path | None:
    """Persiste espelho local em Parquet da tabela raw_scraping_<fonte> com deduplicação por hash."""
    if not respostas:
        return None

    fonte = obter_fonte(id_fonte)
    pasta = Path(diretorio_local if diretorio_local is not None else DIRETORIO_SCRAPING_LOCAL)
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        caminho_arquivo = pasta / f"{fonte.tabela_raw}.parquet"

        df_novos = pd.DataFrame([r.to_dict() for r in respostas])
        if caminho_arquivo.exists():
            try:
                df_antigo = pd.read_parquet(caminho_arquivo)
                df_combinado = pd.concat([df_antigo, df_novos], ignore_index=True)
                df_combinado = df_combinado.drop_duplicates(subset=["hash_conteudo"], keep="first")
            except Exception:
                df_combinado = df_novos.drop_duplicates(subset=["hash_conteudo"], keep="first")
        else:
            df_combinado = df_novos.drop_duplicates(subset=["hash_conteudo"], keep="first")

        df_combinado.to_parquet(caminho_arquivo, index=False)
        return caminho_arquivo
    except Exception as exc:
        logger.warning("Não foi possível salvar Parquet bruto local em %s: %s", pasta, exc)
        return None


def carregar_lote_raw_fonte(
    id_fonte: str,
    respostas: list[RespostaColeta],
    client: bigquery.Client | None = None,
    dataset_id: str = SILVER_DATASET,
    diretorio_local: str | Path | None = None,
) -> int:
    """Persiste um lote de coletas de uma fonte no Parquet local e na tabela bruta do BigQuery."""
    if not respostas:
        return 0

    fonte = obter_fonte(id_fonte)
    salvar_parquet_raw_local(id_fonte, respostas, diretorio_local=diretorio_local)

    try:
        bq_client = client or get_bigquery_client()
        projeto = str(bq_client.project or os.getenv("GCP_PROJECT_ID") or "")
        garantir_dataset_existe(bq_client, dataset_id)

        ddl = gerar_ddl_tabela_raw(projeto, dataset_id, fonte.tabela_raw)
        bq_client.query(ddl).result()

        hashes_bq = obter_hashes_existentes(bq_client, projeto, dataset_id, fonte.tabela_raw)
        ineditas = filtrar_respostas_ineditas(respostas, hashes_bq)

        if not ineditas:
            logger.info(
                "Idempotência [%s]: todos os %d registro(s) já constam no BigQuery.",
                fonte.tabela_raw,
                len(respostas),
            )
            return 0

        df_carga = pd.DataFrame([r.to_dict() for r in ineditas])
        tabela_fqn = f"{projeto}.{dataset_id}.{fonte.tabela_raw}"
        job_config = bigquery.LoadJobConfig(
            schema=SCHEMA_RAW_SCRAPING,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        job = bq_client.load_table_from_dataframe(df_carga, tabela_fqn, job_config=job_config)
        job.result()

        logger.info("Inseridos %d novo(s) registro(s) em %s.", len(ineditas), tabela_fqn)
        return len(ineditas)

    except Exception as exc:
        logger.warning("Aviso na carga BigQuery para %s (mantido espelho local): %s", fonte.tabela_raw, exc)
        return 0
