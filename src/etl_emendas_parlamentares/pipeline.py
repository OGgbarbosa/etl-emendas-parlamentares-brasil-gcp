import sys
from pathlib import Path

# Assegura que o diretório 'src' esteja acessível no sys.path caso o script seja invocado diretamente por caminho de arquivo
_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from etl_emendas_parlamentares.ingestao.upload_bronze import upload_bronze
from etl_emendas_parlamentares.ingestao.upload_gold import upload_gold
from etl_emendas_parlamentares.ingestao.upload_silver import upload_silver
from etl_emendas_parlamentares.processamento.csv_parquet import processar_csv_para_parquet
from etl_emendas_parlamentares.processamento.silver_convenios import processar_silver_fato_convenios
from etl_emendas_parlamentares.processamento.silver_emendas import processar_silver_fato_emendas
from etl_emendas_parlamentares.processamento.silver_favorecidos import processar_silver_fato_favorecidos
from etl_emendas_parlamentares.scraping.pipeline_scraping import executar_pipeline_scraping


def run_raw() -> None:
    processar_csv_para_parquet()


def run_bronze() -> None:
    upload_bronze()


def run_silver() -> None:
    processar_silver_fato_emendas()
    processar_silver_fato_convenios()
    processar_silver_fato_favorecidos()
    upload_silver()


def run_gold() -> None:
    upload_gold()


def run_scraping() -> None:
    executar_pipeline_scraping()


def pipeline() -> None:
    """Executa o pipeline completo de ponta a ponta (Raw ➔ Bronze ➔ Silver ➔ Gold)."""
    run_raw()
    run_bronze()
    run_silver()
    run_gold()


if __name__ == "__main__":
    pipeline()
