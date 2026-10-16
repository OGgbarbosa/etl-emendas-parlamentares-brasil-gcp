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


def carregar_bronze_emendas(
    origem_local: str | Path = DIRETORIO_BRONZE_LOCAL,
    prefixo_gcs: str = BRONZE_PREFIX,
    diretorio_csv: str | Path = "database",
) -> pl.DataFrame:
    """Carrega os dados da camada Bronze de Emendas Parlamentares.

    Prioriza a obtenção direta a partir do Bucket GCS (gs://<bucket>/1_bronze/EmendasParlamentares.parquet).
    Caso não localize no bucket ou ocorra falha de conexão/permissão, realiza o fallback
    para o arquivo local:
      1. Tenta carregar o arquivo Parquet local em data/bronze/EmendasParlamentares.parquet.
      2. Caso não exista o Parquet local, busca arquivos CSV locais (em database/ ou data/bronze/).

    Args:
        origem_local: Diretório local onde os arquivos Parquet da Bronze residem.
        prefixo_gcs: Prefixo/pasta no GCS onde o Parquet reside (padrão: 1_bronze).
        diretorio_csv: Diretório local onde arquivos CSV brutos residem (padrão: database).

    Returns:
        pl.DataFrame: DataFrame com os dados brutos da Bronze.
    """
    # 1. Prioridade: Obter diretamente do Bucket GCS
    bucket_name = os.getenv("GCS_BUCKET_NAME", "")
    if bucket_name:
        try:
            caminho_gcs = f"{prefixo_gcs}/EmendasParlamentares.parquet"
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
    caminho_parquet_local = Path(origem_local) / "EmendasParlamentares.parquet"
    if caminho_parquet_local.exists():
        logger.info("Fallback local: Carregando Parquet de '%s'...", caminho_parquet_local)
        return pl.read_parquet(caminho_parquet_local)

    # 3. Fallback secundário: CSV local
    candidatos_csv = [
        Path(diretorio_csv) / "EmendasParlamentares_utf8.csv",
        Path(diretorio_csv) / "EmendasParlamentares.csv",
        Path(origem_local) / "EmendasParlamentares.csv",
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
        f"Não foi possível obter os dados do GCS (gs://{bucket_name}/{prefixo_gcs}/EmendasParlamentares.parquet) "
        f"nem dos arquivos locais (Parquet em '{caminho_parquet_local}' ou CSV em '{diretorio_csv}')."
    )


def processar_silver_dim_emenda(
    pasta_destino: str | Path = DIRETORIO_SILVER_LOCAL,
    origem_bronze: str | Path = DIRETORIO_BRONZE_LOCAL,
) -> Path:
    """Processa os dados brutos da Bronze e gera a dimensão 'dim_emenda' na camada Silver.

    Aplica as transformações e tipagens exatamente da forma que foi escrito no notebook.

    Args:
        pasta_destino: Diretório onde o Parquet da Silver será salvo (padrão: data/silver).
        origem_bronze: Diretório local de origem da Bronze para fallback.

    Returns:
        Path: Caminho do arquivo Parquet gerado.
    """
    try:
        logger.info("Iniciando processamento da camada Silver: dim_emenda...")
        nome_arquivo = "EmendasParlamentares.parquet"
        df_bronze = carregar_bronze_emendas(origem_local=origem_bronze)

        dim_emenda = (
            df_bronze.filter(pl.col("codigo_da_emenda") != "Sem informação")
            .select(
                [
                    # Identificador da emenda
                    pl.col("codigo_da_emenda").cast(pl.Int64).alias("codigo_da_emenda"),
                    pl.col("tipo_de_emenda").str.strip_chars().alias("tipo_emenda"),
                    pl.col("ano_da_emenda").cast(pl.Int64).alias("ano_emenda"),
                    pl.col("numero_da_emenda").cast(pl.Int64).alias("numero_emenda"),
                    # Autor
                    pl.col("codigo_do_autor_da_emenda").cast(pl.Int64).alias("codigo_autor"),
                    pl.col("nome_do_autor_da_emenda").str.strip_chars().alias("nome_autor"),
                    pl.col("possui_apoiador_solicitante").str.strip_chars().alias("possui_apoiador_solicitante"),
                    # Classificação Orçamentária
                    pl.col("codigo_funcao").replace("MU", None).cast(pl.Int64).alias("codigo_funcao"),
                    pl.col("nome_funcao").str.strip_chars().alias("nome_funcao"),
                    pl.col("codigo_subfuncao").replace("MU", None).cast(pl.Int64).alias("codigo_subfuncao"),
                    pl.col("nome_subfuncao").str.strip_chars().alias("nome_subfuncao"),
                    pl.col("codigo_programa").replace("MU", None).cast(pl.Int64).alias("codigo_programa"),
                    pl.col("nome_programa").str.strip_chars().alias("nome_programa"),
                    pl.col("codigo_acao").str.strip_chars().alias("codigo_acao"),
                    pl.col("nome_acao").str.strip_chars().alias("nome_acao"),
                    pl.col("codigo_plano_orcamentario").str.strip_chars().alias("codigo_plano_orcamentario"),
                    pl.col("nome_plano_orcamentario").str.strip_chars().alias("nome_plano_orcamentario"),
                    # Localidade principal
                    pl.col("uf").str.strip_chars().alias("Estado"),
                    pl.when(pl.col("uf") == "ACRE")
                    .then(pl.lit("AC"))
                    .when(pl.col("uf") == "ALAGOAS")
                    .then(pl.lit("AL"))
                    .when(pl.col("uf") == "AMAPÁ")
                    .then(pl.lit("AP"))
                    .when(pl.col("uf") == "AMAZONAS")
                    .then(pl.lit("AM"))
                    .when(pl.col("uf") == "BAHIA")
                    .then(pl.lit("BA"))
                    .when(pl.col("uf") == "CEARÁ")
                    .then(pl.lit("CE"))
                    .when(pl.col("uf") == "DISTRITO FEDERAL")
                    .then(pl.lit("DF"))
                    .when(pl.col("uf") == "ESPÍRITO SANTO")
                    .then(pl.lit("ES"))
                    .when(pl.col("uf") == "GOIÁS")
                    .then(pl.lit("GO"))
                    .when(pl.col("uf") == "MARANHÃO")
                    .then(pl.lit("MA"))
                    .when(pl.col("uf") == "MATO GROSSO")
                    .then(pl.lit("MT"))
                    .when(pl.col("uf") == "MATO GROSSO DO SUL")
                    .then(pl.lit("MS"))
                    .when(pl.col("uf") == "MINAS GERAIS")
                    .then(pl.lit("MG"))
                    .when(pl.col("uf") == "PARÁ")
                    .then(pl.lit("PA"))
                    .when(pl.col("uf") == "PARAÍBA")
                    .then(pl.lit("PB"))
                    .when(pl.col("uf") == "PARANÁ")
                    .then(pl.lit("PR"))
                    .when(pl.col("uf") == "PERNAMBUCO")
                    .then(pl.lit("PE"))
                    .when(pl.col("uf") == "PIAUÍ")
                    .then(pl.lit("PI"))
                    .when(pl.col("uf") == "RIO DE JANEIRO")
                    .then(pl.lit("RJ"))
                    .when(pl.col("uf") == "RIO GRANDE DO NORTE")
                    .then(pl.lit("RN"))
                    .when(pl.col("uf") == "RIO GRANDE DO SUL")
                    .then(pl.lit("RS"))
                    .when(pl.col("uf") == "RONDÔNIA")
                    .then(pl.lit("RO"))
                    .when(pl.col("uf") == "RORAIMA")
                    .then(pl.lit("RR"))
                    .when(pl.col("uf") == "SANTA CATARINA")
                    .then(pl.lit("SC"))
                    .when(pl.col("uf") == "SÃO PAULO")
                    .then(pl.lit("SP"))
                    .when(pl.col("uf") == "SERGIPE")
                    .then(pl.lit("SE"))
                    .when(pl.col("uf") == "TOCANTINS")
                    .then(pl.lit("TO"))
                    .when(pl.col("uf") == "Múltiplo")
                    .then(pl.lit("MULT"))
                    .when(pl.col("uf") == "Sem informação")
                    .then(pl.lit("NACI"))
                    .otherwise(pl.col("uf"))
                    .alias("uf"),
                    pl.col("localidade_de_aplicacao_do_recurso").str.strip_chars().alias("localidade_recurso"),
                    pl.col("codigo_uf_ibge").cast(pl.Int64).alias("codigo_uf_ibge"),
                    pl.col("regiao").str.strip_chars().alias("regiao"),
                    pl.when(pl.col("uf") == "Sem informação")
                    .then(pl.lit(-1))
                    .when(pl.col("uf") == "Múltiplo")
                    .then(pl.lit(-14))
                    .otherwise(pl.col("codigo_municipio_ibge").replace("Sem informação", -1).cast(pl.Int64))
                    .alias("codigo_municipio_ibge"),
                    pl.when(
                        pl.col("municipio").replace("Sem informação", None).is_null()
                        & pl.col("localidade_de_aplicacao_do_recurso").str.strip_chars().str.ends_with("Nacional")
                    )
                    .then(pl.lit("Nacional"))
                    .when(
                        pl.col("municipio").replace("Sem informação", None).is_null()
                        & pl.col("localidade_de_aplicacao_do_recurso").str.strip_chars().str.ends_with("(UF)")
                    )
                    .then(pl.lit("Estadual"))
                    .when(pl.col("municipio") == "Sem informação")
                    .then(pl.col("regiao").str.strip_chars())
                    .otherwise(pl.col("municipio").str.strip_chars())
                    .alias("municipio"),
                    pl.lit(datetime.now(timezone.utc)).alias("dt_atualizacao"),
                    pl.lit(nome_arquivo).alias("_source_file"),
                ]
            )
            .unique(subset=["codigo_da_emenda"])
        ).sort(by="ano_emenda", descending=True)

        caminho_destino = Path(pasta_destino)
        caminho_destino.mkdir(parents=True, exist_ok=True)
        arquivo_saida = caminho_destino / "dim_emenda.parquet"

        dim_emenda.write_parquet(arquivo_saida, compression="snappy")
        tamanho_mb = arquivo_saida.stat().st_size / (1024 * 1024)

        logger.info(
            "Processamento da Silver concluído com sucesso: '%s' | %d linhas | %d colunas | %.2f MB.",
            arquivo_saida.name,
            dim_emenda.shape[0],
            dim_emenda.shape[1],
            tamanho_mb,
        )

        return arquivo_saida

    except Exception:
        logger.exception("Erro durante o processamento da camada Silver para dim_emenda.")
        raise


if __name__ == "__main__":
    processar_silver_dim_emenda()
