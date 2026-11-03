"""Módulo de orquestração e execução da camada Gold no Google BigQuery.

Executa os scripts SQL analíticos localizados em sql/gold/ para materializar os Data Marts
no BigQuery (tbl_execucao_parlamentar, tbl_distribuicao_geografica, tbl_politicas_publicas,
tbl_ranking_favorecidos e tbl_painel_convenios).
"""

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

from etl_emendas_parlamentares.conexao.big_query import get_bigquery_client
from etl_emendas_parlamentares.config.config import (
    DIRETORIO_GOLD_SQL,
    GOLD_DATASET,
    SILVER_DATASET,
)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def garantir_dataset_existe(client: bigquery.Client, dataset_id: str = GOLD_DATASET) -> None:
    """Verifica se o dataset de destino da Gold existe no BigQuery e o cria se necessário."""
    projeto = str(client.project or os.getenv("GCP_PROJECT_ID") or "")
    dataset_ref = bigquery.DatasetReference(projeto, dataset_id)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        logger.info("Dataset '%s' não encontrado. Criando dataset no BigQuery...", dataset_id)
        dataset = bigquery.Dataset(dataset_ref)
        client.create_dataset(dataset, exists_ok=True)
        logger.info("Dataset '%s' criado com sucesso.", dataset_id)


def preparar_sql_query(
    conteudo_sql: str,
    projeto_destino: str,
    silver_dataset: str = SILVER_DATASET,
    gold_dataset: str = GOLD_DATASET,
) -> str:
    """Ajusta referências de projeto e datasets no SQL para portabilidade entre ambientes."""
    # Substitui projeto padrão caso o cliente esteja rodando sob outro GCP_PROJECT_ID
    query = conteudo_sql.replace("project-f2711ebc-82b0-49cb-b84", projeto_destino)

    # Garante que os datasets utilizados correspondam às configurações do ambiente
    query = query.replace("2_silver", silver_dataset)
    query = query.replace("3_gold", gold_dataset)
    return query


def executar_script_gold(
    caminho_sql: Path | str,
    client: bigquery.Client | None = None,
    silver_dataset: str = SILVER_DATASET,
    gold_dataset: str = GOLD_DATASET,
) -> str:
    """Lê e executa um script SQL da camada Gold no BigQuery, aguardando sua materialização."""
    caminho = Path(caminho_sql)
    if not caminho.exists():
        raise FileNotFoundError(f"Script SQL não encontrado: {caminho}")

    if client is None:
        client = get_bigquery_client()

    projeto = str(client.project or os.getenv("GCP_PROJECT_ID") or "")
    garantir_dataset_existe(client, gold_dataset)

    conteudo_original = caminho.read_text(encoding="utf-8")
    query_execucao = preparar_sql_query(
        conteudo_sql=conteudo_original,
        projeto_destino=projeto,
        silver_dataset=silver_dataset,
        gold_dataset=gold_dataset,
    )

    inicio = time.time()
    logger.info("Executando Data Mart Gold: '%s' no BigQuery...", caminho.name)

    query_job = client.query(query_execucao)
    query_job.result()  # Aguarda a conclusão da materialização

    duracao = time.time() - inicio
    logger.info("Data Mart '%s' materializado com sucesso em %.2f segundos.", caminho.name, duracao)
    return caminho.name


def upload_gold(
    diretorio_sql: str | Path = DIRETORIO_GOLD_SQL,
    gold_dataset: str = GOLD_DATASET,
    silver_dataset: str = SILVER_DATASET,
) -> list[str]:
    """Orquestra a execução de todos os Data Marts SQL da camada Gold no BigQuery.

    Args:
        diretorio_sql: Pasta contendo os arquivos .sql da camada Gold (padrão: sql/gold).
        gold_dataset: Dataset de destino das tabelas Gold (padrão: 3_gold).
        silver_dataset: Dataset de origem das tabelas Silver (padrão: 2_silver).

    Returns:
        list[str]: Lista com os nomes dos scripts SQL executados com sucesso.
    """
    marts_executados: list[str] = []

    try:
        caminho_diretorio = Path(diretorio_sql)
        if not caminho_diretorio.exists():
            logger.warning("Diretório de scripts Gold '%s' não existe.", caminho_diretorio)
            return marts_executados

        scripts_sql = sorted(caminho_diretorio.glob("*.sql"))
        if not scripts_sql:
            logger.warning("Nenhum script SQL encontrado em '%s'.", caminho_diretorio)
            return marts_executados

        client = get_bigquery_client()
        garantir_dataset_existe(client, gold_dataset)

        logger.info("Iniciando materialização dos Data Marts da Camada Gold (%d scripts)...", len(scripts_sql))

        for script in scripts_sql:
            nome = executar_script_gold(
                caminho_sql=script,
                client=client,
                silver_dataset=silver_dataset,
                gold_dataset=gold_dataset,
            )
            marts_executados.append(nome)

        logger.info(
            "Carga da Camada Gold no BigQuery finalizada com sucesso! Total: %d Data Mart(s).",
            len(marts_executados),
        )

    except Exception:
        logger.exception("Erro durante a materialização dos Data Marts da camada Gold no BigQuery.")
        raise

    return marts_executados


if __name__ == "__main__":
    upload_gold()
