import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from etl_emendas_parlamentares.conexao.big_query import get_storage_client
from etl_emendas_parlamentares.config.config import (
    BRONZE_PREFIX,
    DIRETORIO_BRONZE_LOCAL,
    DIRETORIO_SILVER_LOCAL,
)
from etl_emendas_parlamentares.processamento.normalizar import normalizar_colunas

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def carregar_bronze_favorecidos(
    origem_local: str | Path = DIRETORIO_BRONZE_LOCAL,
    prefixo_gcs: str = BRONZE_PREFIX,
    diretorio_csv: str | Path = "database",
) -> pl.DataFrame:
    """Carrega os dados da camada Bronze de Pagamentos por Favorecido de Emendas Parlamentares.

    Prioriza a obtenção direta a partir do Bucket GCS (gs://<bucket>/1_bronze/EmendasParlamentares_PorFavorecido.parquet).
    Caso não localize no bucket ou ocorra falha de conexão/permissão, realiza o fallback
    para o arquivo local:
      1. Tenta carregar o arquivo Parquet local em data/bronze/EmendasParlamentares_PorFavorecido.parquet.
      2. Caso não exista o Parquet local, busca arquivos CSV locais (em database/ ou data/bronze/).

    Args:
        origem_local: Diretório local onde os arquivos Parquet da Bronze residem.
        prefixo_gcs: Prefixo/pasta no GCS onde o Parquet reside (padrão: 1_bronze).
        diretorio_csv: Diretório local onde arquivos CSV brutos residem (padrão: database).

    Returns:
        pl.DataFrame: DataFrame com os dados brutos de favorecidos da Bronze.
    """
    nome_arquivo = "EmendasParlamentares_PorFavorecido.parquet"
    bucket_name = os.getenv("GCS_BUCKET_NAME", "")

    # 1. Prioridade: Obter diretamente do Bucket GCS
    if bucket_name:
        try:
            caminho_gcs = f"{prefixo_gcs}/{nome_arquivo}"
            logger.info("Tentando obter dados do Bucket GCS: 'gs://%s/%s'...", bucket_name, caminho_gcs)
            client = get_storage_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(caminho_gcs)

            if blob.exists():
                buffer = io.BytesIO()
                blob.download_to_file(buffer)
                buffer.seek(0)
                logger.info("Dados obtidos com sucesso do Bucket GCS ('gs://%s/%s').", bucket_name, caminho_gcs)
                return pl.read_parquet(buffer)

            logger.warning("Arquivo 'gs://%s/%s' não localizado no Bucket GCS.", bucket_name, caminho_gcs)
        except Exception as e:
            logger.warning("Falha ao obter dados do Bucket GCS (%s). Acionando fallback local...", e)
    else:
        logger.warning("GCS_BUCKET_NAME não configurado. Acionando fallback local...")

    # 2. Fallback primário: Parquet local
    caminho_parquet_local = Path(origem_local) / nome_arquivo
    if caminho_parquet_local.exists():
        logger.info("Fallback local: Carregando Parquet de '%s'...", caminho_parquet_local)
        return pl.read_parquet(caminho_parquet_local)

    # 3. Fallback secundário: CSV local
    candidatos_csv = [
        Path(diretorio_csv) / "EmendasParlamentares_PorFavorecido.csv",
        Path(origem_local) / "EmendasParlamentares_PorFavorecido.csv",
    ]
    for caminho_csv in candidatos_csv:
        if caminho_csv.exists():
            logger.info("Fallback local: Carregando CSV de '%s'...", caminho_csv)
            encoding = "utf-8" if "utf8" in caminho_csv.name.lower() else "latin1"
            df_csv = pl.read_csv(
                caminho_csv,
                separator=";",
                encoding=encoding,
                infer_schema_length=0,
                truncate_ragged_lines=True,
            )
            mapeamento = {col: normalizar_colunas(col) for col in df_csv.columns}
            return df_csv.rename(mapeamento)

    raise FileNotFoundError(
        f"Não foi possível obter os dados do GCS (gs://{bucket_name}/{prefixo_gcs}/{nome_arquivo}) "
        f"nem dos arquivos locais (Parquet em '{caminho_parquet_local}' ou CSV em '{diretorio_csv}')."
    )


def processar_silver_fato_favorecidos(
    pasta_destino: str | Path = DIRETORIO_SILVER_LOCAL,
    origem_bronze: str | Path = DIRETORIO_BRONZE_LOCAL,
) -> Path:
    """Processa os dados brutos da Bronze e gera a tabela fato 'fato_favorecidos' na camada Silver.

    Aplica as transformações concebidas no notebook: expurgo dos registros sem emenda
    válida (~8,1%), parse seguro da data mensal (ano_mes -> data_referencia), limpeza de textos,
    tratamento de sentinelas e conversão monetária de valor_recebido para Float64.

    Args:
        pasta_destino: Diretório onde o Parquet da Silver será salvo (padrão: data/silver).
        origem_bronze: Diretório local de origem da Bronze para fallback.

    Returns:
        Path: Caminho do arquivo Parquet gerado.
    """
    try:
        logger.info("Iniciando processamento da camada Silver: fato_favorecidos...")
        nome_arquivo = "EmendasParlamentares_PorFavorecido.parquet"
        df_bronze = carregar_bronze_favorecidos(origem_local=origem_bronze)

        fato_favorecidos = (
            df_bronze.filter(
                pl.col("codigo_da_emenda").is_not_null() & (pl.col("codigo_da_emenda") != "Sem informação")
            )
            .select(
                [
                    pl.col("codigo_da_emenda").cast(pl.Int64, strict=False).alias("codigo_da_emenda"),
                    pl.col("codigo_do_autor_da_emenda").cast(pl.Int64, strict=False).alias("codigo_do_autor_da_emenda"),
                    pl.col("codigo_do_favorecido").str.strip_chars().alias("codigo_do_favorecido"),
                    pl.col("numero_da_emenda").cast(pl.Int64, strict=False).alias("numero_da_emenda"),
                    pl.col("ano_mes").str.to_date("%Y%m").alias("data_referencia"),
                    pl.col("nome_do_autor_da_emenda").str.strip_chars().alias("nome_do_autor_da_emenda"),
                    pl.col("tipo_de_emenda").str.strip_chars().alias("tipo_de_emenda"),
                    pl.col("favorecido").str.strip_chars().alias("favorecido"),
                    pl.col("natureza_juridica").str.strip_chars().alias("natureza_juridica"),
                    pl.col("tipo_favorecido").str.strip_chars().alias("tipo_favorecido"),
                    pl.col("uf_favorecido").str.strip_chars().alias("uf_favorecido"),
                    pl.col("municipio_favorecido").str.strip_chars().alias("municipio_favorecido"),
                    pl.col("valor_recebido")
                    .str.replace_all(r"\.", "")
                    .str.replace(",", ".")
                    .cast(pl.Float64, strict=False)
                    .alias("valor_recebido"),
                    pl.lit(datetime.now(timezone.utc)).alias("dt_atualizacao"),
                    pl.lit(nome_arquivo).alias("_source_file"),
                ]
            )
            .sort(by=["data_referencia", "codigo_da_emenda"], descending=[True, False])
        )

        caminho_destino = Path(pasta_destino)
        caminho_destino.mkdir(parents=True, exist_ok=True)
        arquivo_saida = caminho_destino / "fato_favorecidos.parquet"

        fato_favorecidos.write_parquet(arquivo_saida, compression="snappy")
        tamanho_mb = arquivo_saida.stat().st_size / (1024 * 1024)

        logger.info(
            "Processamento da Silver concluído com sucesso: '%s' | %d linhas | %d colunas | %.2f MB.",
            arquivo_saida.name,
            fato_favorecidos.shape[0],
            fato_favorecidos.shape[1],
            tamanho_mb,
        )

        return arquivo_saida

    except Exception:
        logger.exception("Erro durante o processamento da camada Silver para fato_favorecidos.")
        raise


if __name__ == "__main__":
    processar_silver_fato_favorecidos()
