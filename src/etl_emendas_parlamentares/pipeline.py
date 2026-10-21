from etl_emendas_parlamentares.ingestao.upload_bronze import upload_bronze
from etl_emendas_parlamentares.ingestao.upload_silver import upload_silver
from etl_emendas_parlamentares.processamento.csv_parquet import processar_csv_para_parquet
from etl_emendas_parlamentares.processamento.silver_convenios import processar_silver_fato_convenios
from etl_emendas_parlamentares.processamento.silver_emendas import processar_silver_fato_emendas
from etl_emendas_parlamentares.processamento.silver_favorecidos import processar_silver_fato_favorecidos


def run_raw() -> None:
    processar_csv_para_parquet()


def run_bronze() -> None:
    upload_bronze()


def run_silver() -> None:
    processar_silver_fato_emendas()
    processar_silver_fato_convenios()
    processar_silver_fato_favorecidos()
    upload_silver()


def pipeline() -> None:
    """Executa o pipeline completo de ponta a ponta."""
    run_raw()
    run_bronze()
    run_silver()


if __name__ == "__main__":
    pipeline()
