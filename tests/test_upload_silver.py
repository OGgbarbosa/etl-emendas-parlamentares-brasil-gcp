from unittest.mock import MagicMock, patch

from etl_emendas_parlamentares.config.config import SILVER_DATASET
from etl_emendas_parlamentares.ingestao.upload_silver import (
    carregar_tabela_nativa_bigquery,
    garantir_dataset_existe,
    upload_silver,
)


@patch("etl_emendas_parlamentares.ingestao.upload_silver.get_bigquery_client")
def test_garantir_dataset_existe_ja_existente(mock_get_client):
    mock_client = MagicMock()
    mock_client.project = "meu-projeto"
    mock_get_client.return_value = mock_client

    garantir_dataset_existe(mock_client, "2_silver")
    mock_client.get_dataset.assert_called_once()
    mock_client.create_dataset.assert_not_called()


@patch("etl_emendas_parlamentares.ingestao.upload_silver.get_bigquery_client")
def test_garantir_dataset_cria_quando_nao_existe(mock_get_client):
    mock_client = MagicMock()
    mock_client.project = "meu-projeto"
    mock_get_client.return_value = mock_client
    mock_client.get_dataset.side_effect = Exception("Dataset not found")

    garantir_dataset_existe(mock_client, "2_silver")
    mock_client.create_dataset.assert_called_once()


@patch("etl_emendas_parlamentares.ingestao.upload_silver.garantir_dataset_existe")
@patch("etl_emendas_parlamentares.ingestao.upload_silver.get_bigquery_client")
def test_carregar_tabela_nativa_bigquery(mock_get_client, mock_garantir, tmp_path):
    mock_client = MagicMock()
    mock_client.project = "meu-projeto"
    mock_job = MagicMock()
    mock_client.load_table_from_file.return_value = mock_job
    mock_get_client.return_value = mock_client

    arquivo_parquet = tmp_path / "dim_emenda.parquet"
    arquivo_parquet.write_bytes(b"parquet fake")

    tabela_id = carregar_tabela_nativa_bigquery(
        caminho_parquet=arquivo_parquet,
        nome_tabela="dim_emenda",
        dataset_id=SILVER_DATASET,
    )

    assert tabela_id == f"meu-projeto.{SILVER_DATASET}.dim_emenda"
    mock_client.load_table_from_file.assert_called_once()
    mock_job.result.assert_called_once()


@patch("etl_emendas_parlamentares.ingestao.upload_silver.carregar_tabela_nativa_bigquery")
def test_upload_silver(mock_carregar, tmp_path):
    mock_carregar.side_effect = lambda caminho_parquet, nome_tabela, dataset_id: f"projeto.{dataset_id}.{nome_tabela}"

    (tmp_path / "dim_emenda.parquet").write_bytes(b"dados")

    tabelas = upload_silver(origem_local=tmp_path)

    assert len(tabelas) == 1
    assert tabelas[0] == f"projeto.{SILVER_DATASET}.dim_emenda"
    mock_carregar.assert_called_once()
