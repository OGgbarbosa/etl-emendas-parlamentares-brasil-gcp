"""Módulo para leitura e ingestão de dados de Emendas Parlamentares."""

import re
import unicodedata
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyspark.sql import DataFrame
else:
    try:
        from pyspark.sql import DataFrame
    except ImportError:
        DataFrame = Any

try:
    from databricks.sdk.runtime import spark
except Exception:
    spark = None


CATALOG = "datalake_emendas"
SCHEMA = "bronze"
VOLUME = "raw"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"

def sanitizar_nome_coluna(nome: str) -> str:
    """Normaliza o nome da coluna para padrão Delta Lake (snake_case sem acentos/especiais)."""
    # Remove acentuação
    nfkd = unicodedata.normalize('NFKD', nome)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Substitui caracteres especiais/espaços por underscore
    substituido = re.sub(r'[^a-zA-Z0-9]', '_', sem_acento)
    # Remove underscores duplicados e limpa pontas
    limpo = re.sub(r'_+', '_', substituido).strip('_').lower()
    return limpo or "coluna"


def ler_csv_do_volume(nome_arquivo: str) -> DataFrame:
    """Lê um arquivo CSV do Volume raw e retorna um DataFrame Spark com colunas limpas.

    Args:
        nome_arquivo: Nome do arquivo CSV dentro do volume (ex: 'EmendasParlamentares.csv')

    Returns:
        DataFrame Spark com os dados do CSV e nomes de colunas normalizados.
    """
    caminho = f"{VOLUME_PATH}/{nome_arquivo}"
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .option("delimiter", ";")
        .option("encoding", "ISO-8859-1")
        .csv(caminho)
    )
    for col_name in df.columns:
        df = df.withColumnRenamed(col_name, sanitizar_nome_coluna(col_name))
    return df


def ler_emendas() -> DataFrame:
    """Lê o arquivo EmendasParlamentares.csv do Volume."""
    return ler_csv_do_volume("EmendasParlamentares.csv")


def ler_convenios() -> DataFrame:
    """Lê o arquivo EmendasParlamentares_Convenios.csv do Volume."""
    return ler_csv_do_volume("EmendasParlamentares_Convenios.csv")


def ler_favorecidos() -> DataFrame:
    """Lê o arquivo EmendasParlamentares_PorFavorecido.csv do Volume."""
    return ler_csv_do_volume("EmendasParlamentares_PorFavorecido.csv")
