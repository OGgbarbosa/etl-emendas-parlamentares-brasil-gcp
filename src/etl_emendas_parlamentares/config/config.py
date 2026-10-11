"""Configurações e constantes do projeto ETL de Emendas Parlamentares."""

import os

from dotenv import load_dotenv

load_dotenv()

# Valores carregados estritamente via variáveis de ambiente (.env ou ambiente de execução)
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
_raw_bucket = os.getenv("GCS_BUCKET_NAME", "")
GCS_BUCKET_NAME = _raw_bucket.replace("gs://", "").strip("/") if _raw_bucket else None
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

ARQUIVOS_ALVO = [
    "EmendasParlamentares.csv",
    "EmendasParlamentares_Convenios.csv",
    "EmendasParlamentares_PorFavorecido.csv",
]

RAW_PREFIX = "0_raw"
