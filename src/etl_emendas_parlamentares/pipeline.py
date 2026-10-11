from etl_emendas_parlamentares.ingestao.upload_bronze import upload_bronze
from etl_emendas_parlamentares.processamento.csv_parquet import processar_csv_para_parquet


def run_raw() -> None:
    processar_csv_para_parquet()


def run_bronze() -> None:
    upload_bronze()


def pipeline() -> None:
    """Executa o pipeline completo de ponta a ponta."""
    run_raw()
    run_bronze()


if __name__ == "__main__":
    pipeline()
