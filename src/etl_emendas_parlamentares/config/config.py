"""Configurações e constantes do projeto ETL de Emendas Parlamentares."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

# Valores carregados estritamente via variáveis de ambiente (.env ou ambiente de execução)
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION", "global")
VERTEX_MODEL_NAME = os.getenv("VERTEX_MODEL_NAME", "gemini-3.8-flash")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

LOG_CONFIG = logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

ARQUIVOS_ALVO = [
    "EmendasParlamentares.csv",
    "EmendasParlamentares_Convenios.csv",
    "EmendasParlamentares_PorFavorecido.csv",
]

RAW_PREFIX = "0_raw"
BRONZE_PREFIX = "1_bronze"
DIRETORIO_BRONZE_LOCAL = os.getenv("DIRETORIO_BRONZE_LOCAL", "data/bronze")

SILVER_PREFIX = "2_silver"
SILVER_DATASET = os.getenv("SILVER_DATASET", "2_silver")
DIRETORIO_SILVER_LOCAL = os.getenv("DIRETORIO_SILVER_LOCAL", "data/silver")

GOLD_PREFIX = "3_gold"
GOLD_DATASET = os.getenv("GOLD_DATASET", "3_gold")
DIRETORIO_GOLD_SQL = os.getenv("DIRETORIO_GOLD_SQL", "sql/gold")

DIRETORIO_SCRAPING_LOCAL = os.getenv("DIRETORIO_SCRAPING_LOCAL", "data/silver/scraping")
TABELA_FATO_NOTICIAS = os.getenv("TABELA_FATO_NOTICIAS", "fato_noticias_contexto")
SCRAPING_USER_AGENT = os.getenv(
    "SCRAPING_USER_AGENT",
    "EmendasParlamentaresBot/1.0 (+https://portaldatransparencia.gov.br/emendas)",
)
SCRAPING_TIMEOUT_SECONDS = float(os.getenv("SCRAPING_TIMEOUT_SECONDS", "20.0"))
SCRAPING_RATE_LIMIT_SECONDS = float(os.getenv("SCRAPING_RATE_LIMIT_SECONDS", "1.0"))
