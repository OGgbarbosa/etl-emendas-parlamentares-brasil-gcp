"""Configurações e constantes do projeto ETL de Emendas Parlamentares."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

# Valores carregados estritamente via variáveis de ambiente (.env ou ambiente de execução)
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
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
