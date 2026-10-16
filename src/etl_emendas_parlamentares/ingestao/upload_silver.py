import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

from etl_emendas_parlamentares.conexao.big_query import get_bigquery_client
from etl_emendas_parlamentares.config.config import (
    DIRETORIO_SILVER_LOCAL,
    SILVER_DATASET,
)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def garantir_dataset_existe(client: bigquery.Client, dataset_id: str) -> None:
    """Verifica se o dataset existe no BigQuery e o cria se necessário."""
    projeto = str(client.project or os.getenv("GCP_PROJECT_ID") or "")
    dataset_ref = bigquery.DatasetReference(projeto, dataset_id)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        logger.info("Dataset '%s' não encontrado. Criando dataset no BigQuery...", dataset_id)
        dataset = bigquery.Dataset(dataset_ref)
        client.create_dataset(dataset, exists_ok=True)
        logger.info("Dataset '%s' criado com sucesso.", dataset_id)


def carregar_tabela_nativa_bigquery(
    caminho_parquet: Path | str,
    nome_tabela: str,
    dataset_id: str = SILVER_DATASET,
) -> str:
    """Carrega um arquivo Parquet diretamente como tabela nativa gerenciada no BigQuery."""
    client = get_bigquery_client()
    projeto = client.project or os.getenv("GCP_PROJECT_ID")
    tabela_id = f"{projeto}.{dataset_id}.{nome_tabela}"

    garantir_dataset_existe(client, dataset_id)

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    logger.info("Iniciando carga da tabela nativa no BigQuery: '%s' a partir de '%s'...", tabela_id, caminho_parquet)
    with open(caminho_parquet, "rb") as source_file:
        job = client.load_table_from_file(source_file, tabela_id, job_config=job_config)

    job.result()  # Aguarda a conclusão da carga
    logger.info("Tabela nativa '%s' carregada com sucesso no BigQuery.", tabela_id)
    return tabela_id


def upload_silver(
    origem_local: str | Path = DIRETORIO_SILVER_LOCAL,
    dataset_id: str = SILVER_DATASET,
) -> list[str]:
    """Lê os arquivos Parquet gerados na camada Silver local e carrega diretamente

    como tabelas nativas gerenciadas no BigQuery (sem passar por Bucket GCS).

    Args:
        origem_local: Diretório local onde os arquivos da Silver foram salvos (padrão: data/silver).
        dataset_id: Dataset de destino no BigQuery (padrão: 2_silver).

    Returns:
        list[str]: Lista com os IDs das tabelas carregadas no BigQuery.
    """
    tabelas_carregadas: list[str] = []

    try:
        caminho_origem = Path(origem_local)
        if not caminho_origem.exists():
            logger.warning("Diretório local '%s' não existe.", caminho_origem)
            return tabelas_carregadas

        arquivos_parquet = list(caminho_origem.glob("*.parquet"))
        if not arquivos_parquet:
            logger.warning("Nenhum arquivo Parquet encontrado em '%s' para carregar no BigQuery.", caminho_origem)
            return tabelas_carregadas

        for arquivo in arquivos_parquet:
            nome_tabela = arquivo.stem
            tabela_id = carregar_tabela_nativa_bigquery(
                caminho_parquet=arquivo,
                nome_tabela=nome_tabela,
                dataset_id=dataset_id,
            )
            tabelas_carregadas.append(tabela_id)

        logger.info(
            "Carga da camada Silver no BigQuery concluída com sucesso! Total: %d tabela(s).",
            len(tabelas_carregadas),
        )

    except Exception:
        logger.exception("Erro durante a carga das tabelas nativas da Silver no BigQuery.")
        raise

    return tabelas_carregadas


if __name__ == "__main__":
    upload_silver()
