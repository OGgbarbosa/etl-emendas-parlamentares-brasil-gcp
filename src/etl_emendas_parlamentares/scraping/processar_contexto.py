"""Processamento das tabelas brutas raw_scraping_* para a tabela analítica 2_silver.fato_noticias_contexto."""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

from etl_emendas_parlamentares.conexao.big_query import get_bigquery_client
from etl_emendas_parlamentares.config.config import (
    DIRETORIO_SCRAPING_LOCAL,
    DIRETORIO_SILVER_LOCAL,
    SILVER_DATASET,
    TABELA_FATO_NOTICIAS,
)
from etl_emendas_parlamentares.ingestao.upload_silver import garantir_dataset_existe
from etl_emendas_parlamentares.scraping.client import RespostaColeta
from etl_emendas_parlamentares.scraping.fontes import FONTES_SCRAPING
from etl_emendas_parlamentares.scraping.parser import ArtigoProcessado, extrair_artigo_limpo

logger = logging.getLogger(__name__)

SCHEMA_FATO_NOTICIAS = [
    bigquery.SchemaField("id_artigo", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("nome_fonte", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("url_artigo", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("titulo", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("subtitulo", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("autor", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("data_publicacao", "DATE", mode="NULLABLE"),
    bigquery.SchemaField("dh_publicacao", "TIMESTAMP", mode="NULLABLE"),
    bigquery.SchemaField("conteudo_texto", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("lead_resumo", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("tags", "STRING", mode="REPEATED"),
    bigquery.SchemaField("parlamentares_mencionados", "STRING", mode="REPEATED"),
    bigquery.SchemaField("ufs_mencionadas", "STRING", mode="REPEATED"),
    bigquery.SchemaField("qtd_palavras", "INT64", mode="NULLABLE"),
    bigquery.SchemaField("dh_processamento", "TIMESTAMP", mode="REQUIRED"),
]


def gerar_ddl_fato_noticias(
    projeto: str,
    dataset_id: str = SILVER_DATASET,
    nome_tabela: str = TABELA_FATO_NOTICIAS,
) -> str:
    """Gera o DDL oficial da tabela analítica 2_silver.fato_noticias_contexto."""
    return f"""
CREATE TABLE IF NOT EXISTS `{projeto}.{dataset_id}.{nome_tabela}` (
    id_artigo STRING NOT NULL,
    nome_fonte STRING NOT NULL,
    url_artigo STRING NOT NULL,
    titulo STRING NOT NULL,
    subtitulo STRING,
    autor STRING,
    data_publicacao DATE,
    dh_publicacao TIMESTAMP,
    conteudo_texto STRING NOT NULL,
    lead_resumo STRING,
    tags ARRAY<STRING>,
    parlamentares_mencionados ARRAY<STRING>,
    ufs_mencionadas ARRAY<STRING>,
    qtd_palavras INT64,
    dh_processamento TIMESTAMP NOT NULL
)
CLUSTER BY data_publicacao, nome_fonte;
""".strip()


def transformar_respostas_em_artigos(respostas: list[RespostaColeta]) -> list[ArtigoProcessado]:
    """Processa uma lista de RespostaColeta, extraindo texto limpo e deduplicando por id_artigo."""
    artigos_por_id: dict[str, ArtigoProcessado] = {}

    urls_institucionais_ignoradas = {
        "https://www1.folha.uol.com.br/empreendedorsocial/edicoes-anteriores.shtml",
        "https://www1.folha.uol.com.br/institucional/expediente.shtml",
        "https://www.transparencia.org.br/publicacoes/",
    }

    for resp in respostas:
        if (
            resp.http_status != 200
            or not resp.payload_bruto.strip()
            or resp.url_artigo.strip() in urls_institucionais_ignoradas
        ):
            continue

        artigo = extrair_artigo_limpo(
            html_bruto=resp.payload_bruto,
            url_artigo=resp.url_artigo,
            id_fonte=resp.nome_fonte,
            dh_coleta=resp.dh_coleta,
        )
        if artigo and artigo.id_artigo not in artigos_por_id:
            artigos_por_id[artigo.id_artigo] = artigo

    return list(artigos_por_id.values())


def carregar_respostas_brutas_locais(
    diretorio_scraping: str | Path | None = None,
) -> list[RespostaColeta]:
    """Lê todos os arquivos Parquet brutos locais de scraping e reconstrói objetos RespostaColeta."""
    pasta = Path(diretorio_scraping if diretorio_scraping is not None else DIRETORIO_SCRAPING_LOCAL)
    if not pasta.exists():
        return []

    respostas: list[RespostaColeta] = []
    for fonte in FONTES_SCRAPING.values():
        caminho = pasta / f"{fonte.tabela_raw}.parquet"
        if not caminho.exists():
            continue
        try:
            df = pd.read_parquet(caminho)
            for _, row in df.iterrows():
                dh_val = row.get("dh_coleta")
                if isinstance(dh_val, pd.Timestamp):
                    dh_dt = dh_val.to_pydatetime()
                elif isinstance(dh_val, datetime):
                    dh_dt = dh_val
                else:
                    dh_dt = datetime.now(timezone.utc)

                if dh_dt.tzinfo is None:
                    dh_dt = dh_dt.replace(tzinfo=timezone.utc)

                respostas.append(
                    RespostaColeta(
                        id_requisicao=str(row.get("id_requisicao", "")),
                        url_artigo=str(row.get("url_artigo", "")),
                        nome_fonte=str(row.get("nome_fonte", fonte.id_fonte)),
                        dh_coleta=dh_dt,
                        http_status=int(row.get("http_status", 200)),
                        payload_bruto=str(row.get("payload_bruto", "")),
                        hash_conteudo=str(row.get("hash_conteudo", "")),
                    )
                )
        except Exception as exc:
            logger.warning("Erro ao ler Parquet bruto local %s: %s", caminho, exc)

    return respostas


def materializar_fato_noticias_contexto(
    respostas_em_memoria: list[RespostaColeta] | None = None,
    client: bigquery.Client | None = None,
    dataset_id: str = SILVER_DATASET,
    nome_tabela: str = TABELA_FATO_NOTICIAS,
    diretorio_silver_local: str | Path | None = None,
    diretorio_scraping_local: str | Path | None = None,
) -> pd.DataFrame:
    """Consolida as coletas brutas, higieniza os textos e materializa 2_silver.fato_noticias_contexto."""
    respostas_locais = carregar_respostas_brutas_locais(diretorio_scraping=diretorio_scraping_local)
    todas_respostas = list(respostas_em_memoria or []) + respostas_locais

    artigos = transformar_respostas_em_artigos(todas_respostas)
    if not artigos:
        logger.warning("Nenhum artigo válido encontrado para materializar em %s.", nome_tabela)
        return pd.DataFrame()

    df_fato = pd.DataFrame([a.to_dict() for a in artigos])
    df_fato = df_fato.drop_duplicates(subset=["id_artigo"], keep="first").reset_index(drop=True)

    # Salva espelho analítico na pasta Silver local (para fallback rápido do Streamlit)
    pasta_silver = Path(diretorio_silver_local if diretorio_silver_local is not None else DIRETORIO_SILVER_LOCAL)
    try:
        pasta_silver.mkdir(parents=True, exist_ok=True)
        caminho_parquet = pasta_silver / f"{nome_tabela}.parquet"
        df_fato.to_parquet(caminho_parquet, index=False)
        logger.info("Arquivo analítico salvo localmente em: %s (%d artigos)", caminho_parquet, len(df_fato))
    except Exception as exc:
        logger.warning("Não foi possível salvar Parquet analítico local em %s: %s", pasta_silver, exc)

    # Materializa na camada Silver do BigQuery
    try:
        bq_client = client or get_bigquery_client()
        projeto = str(bq_client.project or os.getenv("GCP_PROJECT_ID") or "")
        garantir_dataset_existe(bq_client, dataset_id)

        ddl = gerar_ddl_fato_noticias(projeto, dataset_id, nome_tabela)
        bq_client.query(ddl).result()

        tabela_fqn = f"{projeto}.{dataset_id}.{nome_tabela}"
        job_config = bigquery.LoadJobConfig(
            schema=SCHEMA_FATO_NOTICIAS,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        job = bq_client.load_table_from_dataframe(df_fato, tabela_fqn, job_config=job_config)
        job.result()
        logger.info(
            "Tabela analítica '%s' materializada com sucesso no BigQuery (%d artigos).",
            tabela_fqn,
            len(df_fato),
        )
    except Exception as exc:
        logger.warning("Aviso ao carregar '%s' no BigQuery (mantido Parquet local): %s", nome_tabela, exc)

    return df_fato
