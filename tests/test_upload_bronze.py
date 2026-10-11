import io
from unittest.mock import MagicMock, patch

import pytest

from etl_emendas_parlamentares.config.config import BRONZE_PREFIX
from etl_emendas_parlamentares.ingestao.upload_bronze import (
    _upload_arquivo_para_gcs,
    _upload_buffer_para_gcs,
    upload_bronze,
)


def test_upload_buffer_para_gcs():
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    buffer = io.BytesIO(b"conteudo de teste")
    destino = f"{BRONZE_PREFIX}/teste.parquet"

    uri = _upload_buffer_para_gcs(mock_client, "teste-bucket", buffer, destino)

    assert uri == f"gs://teste-bucket/{BRONZE_PREFIX}/teste.parquet"
    mock_client.bucket.assert_called_once_with("teste-bucket")
    mock_bucket.blob.assert_called_once_with(destino)
    mock_blob.upload_from_file.assert_called_once()


def test_upload_arquivo_para_gcs(tmp_path):
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    arquivo_teste = tmp_path / "teste.parquet"
    arquivo_teste.write_bytes(b"conteudo parquet")
    destino = f"{BRONZE_PREFIX}/teste.parquet"

    uri = _upload_arquivo_para_gcs(mock_client, "teste-bucket", arquivo_teste, destino)

    assert uri == f"gs://teste-bucket/{BRONZE_PREFIX}/teste.parquet"
    mock_client.bucket.assert_called_once_with("teste-bucket")
    mock_bucket.blob.assert_called_once_with(destino)
    mock_blob.upload_from_filename.assert_called_once_with(str(arquivo_teste), content_type="application/octet-stream")


@patch("etl_emendas_parlamentares.ingestao.upload_bronze.get_storage_client")
@patch("etl_emendas_parlamentares.ingestao.upload_bronze._upload_arquivo_para_gcs")
@patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://teste-bucket"})
def test_upload_bronze_de_disco(mock_upload_arquivo, mock_get_client, tmp_path):
    mock_upload_arquivo.side_effect = lambda client, bucket, arq, dest: f"gs://{bucket}/{dest}"

    (tmp_path / "EmendasParlamentares.parquet").write_bytes(b"dados 1")
    (tmp_path / "EmendasParlamentares_Convenios.parquet").write_bytes(b"dados 2")

    uris = upload_bronze(origem_local=tmp_path)

    assert len(uris) == 2
    assert any(f"gs://teste-bucket/{BRONZE_PREFIX}/EmendasParlamentares.parquet" in u for u in uris)
    assert any(f"gs://teste-bucket/{BRONZE_PREFIX}/EmendasParlamentares_Convenios.parquet" in u for u in uris)
    assert mock_upload_arquivo.call_count == 2


@patch("etl_emendas_parlamentares.ingestao.upload_bronze.get_storage_client")
@patch("etl_emendas_parlamentares.ingestao.upload_bronze._upload_buffer_para_gcs")
@patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://teste-bucket"})
def test_upload_bronze_com_dados(mock_upload_buffer, mock_get_client):
    mock_upload_buffer.side_effect = lambda client, bucket, buf, dest: f"gs://{bucket}/{dest}"

    dados = {
        "arquivo1.parquet": io.BytesIO(b"dados 1"),
        "arquivo2.parquet": io.BytesIO(b"dados 2"),
    }

    uris = upload_bronze(dados=dados)

    assert len(uris) == 2
    assert uris[0] == f"gs://teste-bucket/{BRONZE_PREFIX}/arquivo1.parquet"
    assert uris[1] == f"gs://teste-bucket/{BRONZE_PREFIX}/arquivo2.parquet"
    assert mock_upload_buffer.call_count == 2


@patch("etl_emendas_parlamentares.ingestao.upload_bronze.get_storage_client")
@patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://teste-bucket"})
def test_upload_bronze_diretorio_vazio(mock_get_client, tmp_path):
    # Pasta temporária sem nenhum arquivo .parquet
    uris = upload_bronze(origem_local=tmp_path)
    assert uris == []


@patch("etl_emendas_parlamentares.ingestao.upload_bronze.get_storage_client")
@patch("etl_emendas_parlamentares.ingestao.upload_bronze._upload_buffer_para_gcs")
@patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://teste-bucket"})
def test_upload_bronze_erro(mock_upload_buffer, mock_get_client):
    mock_upload_buffer.side_effect = RuntimeError("Falha de rede")

    dados = {"falha.parquet": io.BytesIO(b"dados")}

    with pytest.raises(RuntimeError, match="Falha de rede"):
        upload_bronze(dados=dados)
