import io
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from etl_emendas_parlamentares.processamento.silver_convenios import (
    carregar_bronze_convenios,
    processar_silver_fato_convenios,
)


@pytest.fixture
def bronze_convenios_sample_df():
    return pl.DataFrame(
        {
            "codigo_da_emenda": [
                "20240001",
                "20240002",  # Mesmo convênio C1 com outra emenda (N:N)
                "20240001",  # Linha duplicada exata para o par (C1, 20240001)
                "Sem informação",  # Deve ser expurgado
                None,  # Deve ser expurgado
                "20240003",
            ],
            "numero_convenio": [
                "C1",
                "C1",
                "C1",
                "C2",
                "C3",
                "C4",
            ],
            "codigo_funcao": ["10", "10", "10", "15", "12", "6"],
            "nome_funcao": ["Saúde", "Saúde", "Saúde", "Urbanismo", "Educação", "Segurança"],
            "codigo_subfuncao": ["301", "301", "301", "451", "361", "182"],
            "nome_subfuncao": ["Atenção Básica", "Atenção Básica", "Atenção Básica", "Infra", "Ensino", "Polícia"],
            "localidade_do_gasto": [
                "XINGUARA - PA",
                "XINGUARA - PA",
                "XINGUARA - PA",
                "BRASIL - Nacional",
                "Acre (UF)",
                "Região Nordeste",
            ],
            "tipo_de_emenda": [
                "Individual",
                "Bancada",
                "Individual",
                "Individual",
                "Individual",
                "Comissão",
            ],
            "data_publicacao_convenio": [
                "15/05/2024",
                "15/05/2024",
                "15/05/2024",
                "01/01/2024",
                "10/02/2024",
                "20/06/2024",
            ],
            "convenente": [
                "MUNICIPIO DE XINGUARA",
                "MUNICIPIO DE XINGUARA",
                "MUNICIPIO DE XINGUARA",
                "ORGAO NACIONAL",
                "GOVERNO DO ACRE",
                "SECRETARIA NORDESTE",
            ],
            "objeto_convenio": [
                "Reforma de posto de saúde",
                "Reforma de posto de saúde",
                "Reforma de posto de saúde",
                "Objeto nacional",
                "Objeto estadual",
                "Objeto regional",
            ],
            "valor_convenio": [
                "500000,00",
                "750000,50",
                "500000,00",
                "1000000,00",
                "250000,00",
                "1.200.000,00",
            ],
        }
    )


@patch("etl_emendas_parlamentares.processamento.silver_convenios.get_storage_client")
def test_carregar_bronze_convenios_sucesso_gcs(mock_get_client, bronze_convenios_sample_df):
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True

    buffer = io.BytesIO()
    bronze_convenios_sample_df.write_parquet(buffer)
    conteudo_bytes = buffer.getvalue()

    def download_to_file(buf):
        buf.write(conteudo_bytes)

    mock_blob.download_to_file.side_effect = download_to_file
    mock_bucket.blob.return_value = mock_blob
    mock_client.bucket.return_value = mock_bucket
    mock_get_client.return_value = mock_client

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://bucket-teste"}):
        df = carregar_bronze_convenios()

    assert df.shape == bronze_convenios_sample_df.shape
    mock_blob.download_to_file.assert_called_once()


@patch("etl_emendas_parlamentares.processamento.silver_convenios.get_storage_client")
def test_carregar_bronze_convenios_fallback_parquet_local(mock_get_client, tmp_path, bronze_convenios_sample_df):
    mock_get_client.side_effect = Exception("Conexão falhou")

    pasta_bronze = tmp_path / "bronze"
    pasta_bronze.mkdir()
    arquivo_parquet = pasta_bronze / "EmendasParlamentares_Convenios.parquet"
    bronze_convenios_sample_df.write_parquet(arquivo_parquet)

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://bucket-teste"}):
        df = carregar_bronze_convenios(origem_local=pasta_bronze)

    assert df.shape == bronze_convenios_sample_df.shape
    assert set(df.columns) == set(bronze_convenios_sample_df.columns)


@patch("etl_emendas_parlamentares.processamento.silver_convenios.get_storage_client")
def test_carregar_bronze_convenios_fallback_csv_local(mock_get_client, tmp_path):
    mock_get_client.side_effect = Exception("Sem conexao")

    pasta_vazia = tmp_path / "bronze_vazia"
    pasta_vazia.mkdir()

    pasta_csv = tmp_path / "database"
    pasta_csv.mkdir()
    arquivo_csv = pasta_csv / "EmendasParlamentares_Convenios.csv"
    arquivo_csv.write_text(
        "Código da Emenda;Número Convênio;Valor Convênio\n20240001;C1;100000,00\n",
        encoding="latin1",
    )

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://bucket-teste"}):
        df = carregar_bronze_convenios(origem_local=pasta_vazia, diretorio_csv=pasta_csv)

    assert df.shape == (1, 3)
    assert "codigo_da_emenda" in df.columns
    assert "numero_convenio" in df.columns
    assert "valor_convenio" in df.columns


@patch("etl_emendas_parlamentares.processamento.silver_convenios.get_storage_client")
def test_carregar_bronze_convenios_falha_total(mock_get_client, tmp_path):
    mock_get_client.side_effect = Exception("Erro GCS")
    pasta_vazia = tmp_path / "vazia"
    pasta_vazia.mkdir()

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": ""}), pytest.raises(FileNotFoundError):
        carregar_bronze_convenios(origem_local=pasta_vazia, diretorio_csv=pasta_vazia)


@patch("etl_emendas_parlamentares.processamento.silver_convenios.carregar_bronze_convenios")
def test_processar_silver_fato_convenios(mock_carregar, tmp_path, bronze_convenios_sample_df):
    mock_carregar.return_value = bronze_convenios_sample_df

    pasta_silver = tmp_path / "silver"
    arquivo_gerado = processar_silver_fato_convenios(pasta_destino=pasta_silver)

    assert arquivo_gerado.exists()
    assert arquivo_gerado.name == "fato_convenios.parquet"

    df_resultado = pl.read_parquet(arquivo_gerado)

    # 1. Filtro: expurga 'Sem informação' e nulos em codigo_da_emenda
    assert "Sem informação" not in df_resultado["codigo_da_emenda"].to_list()
    assert df_resultado["codigo_da_emenda"].null_count() == 0

    # 2. Deduplicação N:N:
    # C1 com 20240001 e C1 com 20240002 são AMBAS preservadas!
    # A duplicata exata de (C1, 20240001) é removida.
    # Total de linhas sobreviventes: (C1, 20240001), (C1, 20240002), (C4, 20240003) = 3 linhas
    assert df_resultado.shape[0] == 3
    c1_rows = df_resultado.filter(pl.col("numero_convenio") == "C1")
    assert c1_rows.shape[0] == 2
    assert set(c1_rows["codigo_da_emenda"].to_list()) == {20240001, 20240002}

    # 3. 15 colunas esperadas
    assert df_resultado.shape[1] == 15
    assert "localidade_classificada" in df_resultado.columns
    assert "dt_atualizacao" in df_resultado.columns
    assert "_source_file" in df_resultado.columns

    # 4. Tipagem
    assert df_resultado.schema["codigo_da_emenda"] == pl.Int64
    assert df_resultado.schema["codigo_funcao"] == pl.Int64
    assert df_resultado.schema["codigo_subfuncao"] == pl.Int64
    assert df_resultado.schema["numero_convenio"] == pl.String
    assert df_resultado.schema["data_publicacao_convenio"] == pl.Date
    assert df_resultado.schema["valor_convenio"] == pl.Float64

    # 5. Classificação de localidade
    c1_row = df_resultado.filter(pl.col("codigo_da_emenda") == 20240001)
    assert c1_row["localidade_classificada"][0] == "PA"

    c4_row = df_resultado.filter(pl.col("codigo_da_emenda") == 20240003)
    assert c4_row["localidade_classificada"][0] in ("Regional", "REGIONAL")

    # 6. Conversão de valor monetário para Float64
    assert c1_row["valor_convenio"][0] == 500000.0
    c1_row_b = df_resultado.filter(pl.col("codigo_da_emenda") == 20240002)
    assert c1_row_b["valor_convenio"][0] == 750000.50
    assert c4_row["valor_convenio"][0] == 1200000.0
