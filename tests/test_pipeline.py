from unittest.mock import patch

from etl_emendas_parlamentares.pipeline import pipeline, run_bronze, run_raw, run_silver


@patch("etl_emendas_parlamentares.pipeline.processar_csv_para_parquet")
def test_run_raw(mock_processar):
    run_raw()
    mock_processar.assert_called_once()


@patch("etl_emendas_parlamentares.pipeline.upload_bronze")
def test_run_bronze(mock_upload_bronze):
    run_bronze()
    mock_upload_bronze.assert_called_once()


@patch("etl_emendas_parlamentares.pipeline.upload_silver")
@patch("etl_emendas_parlamentares.pipeline.processar_silver_fato_favorecidos")
@patch("etl_emendas_parlamentares.pipeline.processar_silver_fato_convenios")
@patch("etl_emendas_parlamentares.pipeline.processar_silver_fato_emendas")
def test_run_silver(
    mock_processar_emenda,
    mock_processar_convenios,
    mock_processar_favorecidos,
    mock_upload_silver,
):
    run_silver()
    mock_processar_emenda.assert_called_once()
    mock_processar_convenios.assert_called_once()
    mock_processar_favorecidos.assert_called_once()
    mock_upload_silver.assert_called_once()


@patch("etl_emendas_parlamentares.pipeline.run_silver")
@patch("etl_emendas_parlamentares.pipeline.run_bronze")
@patch("etl_emendas_parlamentares.pipeline.run_raw")
def test_pipeline_completo(mock_raw, mock_bronze, mock_silver):
    pipeline()
    mock_raw.assert_called_once()
    mock_bronze.assert_called_once()
    mock_silver.assert_called_once()
