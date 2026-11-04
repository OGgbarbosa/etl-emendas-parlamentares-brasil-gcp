"""Módulo de orquestração e execução da camada Gold no Google BigQuery.

Executa os scripts SQL analíticos localizados em sql/gold/ para materializar os Data Marts físicos
(tbl_execucao_parlamentar, tbl_distribuicao_geografica, tbl_politicas_publicas, tbl_ranking_favorecidos
e tbl_painel_convenios) e em seguida as Views Semânticas de Consumo com metadados para IA (view_ai_*).
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


def ordenar_scripts_gold(scripts: list[Path], incluir_views_semanticas: bool = True) -> list[Path]:
    """Ordena scripts SQL garantindo que tabelas físicas sejam executadas antes das views semânticas.

    Args:
        scripts: Lista de caminhos Path dos scripts SQL.
        incluir_views_semanticas: Se False, exclui scripts iniciados por view_ai_.

    Returns:
        list[Path]: Lista ordenada com tabelas físicas seguidas de views semânticas.
    """
    tabelas = sorted([s for s in scripts if not s.name.startswith("view_ai_")])
    if not incluir_views_semanticas:
        return tabelas

    views = sorted([s for s in scripts if s.name.startswith("view_ai_")])
    return tabelas + views


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
    # Substitui placeholder de projeto para o GCP_PROJECT_ID configurado no ambiente
    query = conteudo_sql.replace("{PROJECT_ID}", projeto_destino)
    query = query.replace("{{project_id}}", projeto_destino)

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

    tipo_objeto = "View Semântica IA" if caminho.name.startswith("view_ai_") else "Data Mart Físico"
    inicio = time.time()
    logger.info("Executando %s Gold: '%s' no BigQuery...", tipo_objeto, caminho.name)

    query_job = client.query(query_execucao)
    query_job.result()  # Aguarda a conclusão da materialização

    duracao = time.time() - inicio
    logger.info("%s '%s' materializado com sucesso em %.2f segundos.", tipo_objeto, caminho.name, duracao)
    return caminho.name


def upload_gold(
    diretorio_sql: str | Path = DIRETORIO_GOLD_SQL,
    gold_dataset: str = GOLD_DATASET,
    silver_dataset: str = SILVER_DATASET,
    incluir_views_semanticas: bool = True,
) -> list[str]:
    """Orquestra a execução de todos os Data Marts e Views Semânticas da camada Gold no BigQuery.

    Garante a ordem de execução com tabelas físicas sendo criadas antes das views semânticas.

    Args:
        diretorio_sql: Pasta contendo os arquivos .sql da camada Gold (padrão: sql/gold).
        gold_dataset: Dataset de destino das tabelas e views Gold (padrão: 3_gold).
        silver_dataset: Dataset de origem das tabelas Silver (padrão: 2_silver).
        incluir_views_semanticas: Se True, executa também os scripts view_ai_*.sql.

    Returns:
        list[str]: Lista com os nomes dos scripts SQL executados com sucesso na ordem correta.
    """
    marts_executados: list[str] = []

    try:
        caminho_diretorio = Path(diretorio_sql)
        if not caminho_diretorio.exists():
            logger.warning("Diretório de scripts Gold '%s' não existe.", caminho_diretorio)
            return marts_executados

        scripts_encontrados = list(caminho_diretorio.glob("*.sql"))
        if not scripts_encontrados:
            logger.warning("Nenhum script SQL encontrado em '%s'.", caminho_diretorio)
            return marts_executados

        scripts_sql = ordenar_scripts_gold(
            scripts=scripts_encontrados,
            incluir_views_semanticas=incluir_views_semanticas,
        )

        client = get_bigquery_client()
        garantir_dataset_existe(client, gold_dataset)

        logger.info(
            "Iniciando materialização dos artefatos da Camada Gold (%d scripts na fila)...",
            len(scripts_sql),
        )

        for script in scripts_sql:
            nome = executar_script_gold(
                caminho_sql=script,
                client=client,
                silver_dataset=silver_dataset,
                gold_dataset=gold_dataset,
            )
            marts_executados.append(nome)

        logger.info(
            "Carga da Camada Gold no BigQuery finalizada com sucesso! Total: %d artefatos.",
            len(marts_executados),
        )

    except Exception:
        logger.exception("Erro durante a materialização dos Data Marts e Views da camada Gold no BigQuery.")
        raise

    return marts_executados


if __name__ == "__main__":
    upload_gold()
