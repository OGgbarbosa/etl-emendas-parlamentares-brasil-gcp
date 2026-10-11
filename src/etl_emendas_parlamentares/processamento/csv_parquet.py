import glob
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from etl_emendas_parlamentares.config.config import ARQUIVOS_ALVO, DIRETORIO_BRONZE_LOCAL
from etl_emendas_parlamentares.processamento.normalizar import normalizar_colunas

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def processar_csv_para_parquet(
    pasta_origem: str | None = None,
    pasta_destino: str | Path = DIRETORIO_BRONZE_LOCAL,
) -> list[Path]:
    """Lê os CSVs brutos de Emendas Parlamentares, sanitiza colunas, adiciona metadados da Bronze

    e grava os arquivos em formato Parquet comprimido (Snappy) no diretório de destino local.

    Args:
        pasta_origem: Diretório opcional com os CSVs de entrada.
                      Se None, usa 'database' ou fallback para 'database_sample'.
        pasta_destino: Diretório local onde os arquivos .parquet serão armazenados
                       (padrão: DIRETORIO_BRONZE_LOCAL = 'data/bronze').

    Returns:
        list[Path]: Lista com os caminhos dos arquivos Parquet gerados.
    """
    arquivos_gerados: list[Path] = []
    caminho_destino = Path(pasta_destino)

    try:
        if not pasta_origem:
            pasta_origem = (
                "database" if os.path.exists("database") and glob.glob("database/*.csv") else "database_sample"
            )

        logger.info("Iniciando processamento de CSV para Parquet a partir de: '%s'", pasta_origem)

        if not os.path.exists(pasta_origem):
            logger.warning("Pasta de origem '%s' não encontrada.", pasta_origem)
            return arquivos_gerados

        caminho_destino.mkdir(parents=True, exist_ok=True)

        for nome_arquivo in ARQUIVOS_ALVO:
            caminho_csv = os.path.join(pasta_origem, nome_arquivo)

            if not os.path.exists(caminho_csv):
                logger.warning("Arquivo '%s' não encontrado em '%s'. Pulando...", nome_arquivo, pasta_origem)
                continue

            logger.info("Lendo arquivo local: '%s'...", caminho_csv)

            # infer_schema_length=0 garante leitura fiel de todos os dados brutos como String
            df = pl.read_csv(caminho_csv, separator=";", infer_schema_length=0, encoding="latin1")

            # Sanitiza todos os nomes de colunas para snake_case (sem acentos/especiais)
            df = df.rename({col: normalizar_colunas(col) for col in df.columns})

            # Inclusão de colunas de auditoria indispensáveis para a camada Bronze
            df_bronze = df.with_columns(
                [
                    pl.lit(datetime.now(timezone.utc)).alias("_ingestion_timestamp"),
                    pl.lit(nome_arquivo).alias("_source_file"),
                ]
            )

            nome_parquet = f"{Path(nome_arquivo).stem}.parquet"
            arquivo_saida = caminho_destino / nome_parquet

            df_bronze.write_parquet(arquivo_saida, compression="snappy")
            tamanho_mb = arquivo_saida.stat().st_size / (1024 * 1024)
            arquivos_gerados.append(arquivo_saida)

            logger.info(
                "Processamento concluído: '%s' salvo em '%s' | %d linhas | %d colunas | %.2f MB.",
                nome_parquet,
                arquivo_saida,
                df_bronze.shape[0],
                df_bronze.shape[1],
                tamanho_mb,
            )

        logger.info(
            "Finalizado processamento de Parquet. Total de %d arquivos gerados com sucesso em '%s'.",
            len(arquivos_gerados),
            caminho_destino,
        )

    except Exception:
        logger.exception("Erro inesperado durante o processamento de CSV para Parquet.")
        raise

    return arquivos_gerados


if __name__ == "__main__":
    processar_csv_para_parquet()
