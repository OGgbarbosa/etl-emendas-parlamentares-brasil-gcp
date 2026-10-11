"""Configurações e constantes do projeto ETL de Emendas Parlamentares."""

import os

from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "project-f2711ebc-82b0-49cb-b84")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "bucket-landing-general").replace("gs://", "").strip("/")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "gcp-credentials.json")

ARQUIVOS_ALVO = [
    "EmendasParlamentares.csv",
    "EmendasParlamentares_Convenios.csv",
    "EmendasParlamentares_PorFavorecido.csv",
]

RAW_PREFIX = "0_raw"
