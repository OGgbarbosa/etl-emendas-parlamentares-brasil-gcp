import io
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from etl_emendas_parlamentares.processamento.silver_favorecidos import (
    carregar_bronze_favorecidos,
    processar_silver_fato_favorecidos,
)


@pytest.fixture
def bronze_favorecidos_sample_df():
    return pl.DataFrame(
        {
            "codigo_da_emenda": [
                "20240001",
                "20240002",  # Outra emenda repassando para o mesmo favorecido F1
                "20240001",  # Mesma emenda repassando para F1 em outro mês
                "Sem informação",  # Deve ser expurgado
                None,  # Deve ser expurgado
                "20240003",
            ],
            "codigo_do_autor_da_emenda": ["100", "200", "100", "S/I", "300", "400"],
            "nome_do_autor_da_emenda": [
                "Deputado A",
                "Deputado B",
                "Deputado A",
                "Sem informação",
                "Deputado C",
                "Deputado D",
            ],
            "numero_da_emenda": ["1", "2", "1", "S/I", "3", "4"],
            "tipo_de_emenda": [
                "Individual",
                "Bancada",
                "Individual",
                "Individual",
                "Individual",
                "Comissão",
            ],
            "ano_mes": ["202405", "202405", "202406", "202401", "202402", "202407"],
            "codigo_do_favorecido": [
                "00123456000199",
                "00123456000199",
                "00123456000199",
                "11222333000144",
                "99888777000155",
                "33444555000166",
            ],
            "favorecido": [
                "HOSPITAL CENTRAL",
                "HOSPITAL CENTRAL",
                "HOSPITAL CENTRAL",
                "EMPRESA X",
                "EMPRESA Y",
                "PREFEITURA Z",
            ],
            "natureza_juridica": [
                "Associação Privada",
                "Associação Privada",
                "Associação Privada",
                "Sociedade Empresária",
                "Sociedade Empresária",
                "Órgão Público",
            ],
            "tipo_favorecido": [
                "Pessoa Jurídica",
                "Pessoa Jurídica",
                "Pessoa Jurídica",
                "Pessoa Jurídica",
                "Pessoa Jurídica",
                "Pessoa Jurídica",
            ],
            "uf_favorecido": ["SP", "SP", "SP", "-1", "RJ", "-1"],
            "municipio_favorecido": [
                "SÃO PAULO",
                "SÃO PAULO",
                "SÃO PAULO",
                "Sem informação",
                "RIO DE JANEIRO",
                "Sem informação",
            ],
            "valor_recebido": [
                "150000,00",
                "250000,50",
                "100000,00",
                "50000,00",
                "300000,00",
                "1.250.000,75",
            ],
        }
    )


@patch("etl_emendas_parlamentares.processamento.silver_favorecidos.get_storage_client")
def test_carregar_bronze_favorecidos_sucesso_gcs(mock_get_client, bronze_favorecidos_sample_df):
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True

    buffer = io.BytesIO()
    bronze_favorecidos_sample_df.write_parquet(buffer)
    conteudo_bytes = buffer.getvalue()

    def download_to_file(buf):
        buf.write(conteudo_bytes)

    mock_blob.download_to_file.side_effect = download_to_file
    mock_bucket.blob.return_value = mock_blob
    mock_client.bucket.return_value = mock_bucket
    mock_get_client.return_value = mock_client

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://bucket-teste"}):
        df = carregar_bronze_favorecidos()

    assert df.shape == bronze_favorecidos_sample_df.shape
    mock_blob.download_to_file.assert_called_once()


@patch("etl_emendas_parlamentares.processamento.silver_favorecidos.get_storage_client")
def test_carregar_bronze_favorecidos_fallback_parquet_local(mock_get_client, tmp_path, bronze_favorecidos_sample_df):
    mock_get_client.side_effect = Exception("Conexão falhou")

    pasta_bronze = tmp_path / "bronze"
    pasta_bronze.mkdir()
    arquivo_parquet = pasta_bronze / "EmendasParlamentares_PorFavorecido.parquet"
    bronze_favorecidos_sample_df.write_parquet(arquivo_parquet)

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://bucket-teste"}):
        df = carregar_bronze_favorecidos(origem_local=pasta_bronze)

    assert df.shape == bronze_favorecidos_sample_df.shape
    assert set(df.columns) == set(bronze_favorecidos_sample_df.columns)


@patch("etl_emendas_parlamentares.processamento.silver_favorecidos.get_storage_client")
def test_carregar_bronze_favorecidos_fallback_csv_local(mock_get_client, tmp_path):
    mock_get_client.side_effect = Exception("Sem conexao")

    pasta_vazia = tmp_path / "bronze_vazia"
    pasta_vazia.mkdir()

    pasta_csv = tmp_path / "database"
    pasta_csv.mkdir()
    arquivo_csv = pasta_csv / "EmendasParlamentares_PorFavorecido.csv"
    arquivo_csv.write_text(
        "Código da Emenda;Código do Favorecido;Valor Recebido\n20240001;00123456000199;100000,00\n",
        encoding="latin1",
    )

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://bucket-teste"}):
        df = carregar_bronze_favorecidos(origem_local=pasta_vazia, diretorio_csv=pasta_csv)

    assert df.shape == (1, 3)
    assert "codigo_da_emenda" in df.columns
    assert "codigo_do_favorecido" in df.columns
    assert "valor_recebido" in df.columns


@patch("etl_emendas_parlamentares.processamento.silver_favorecidos.get_storage_client")
def test_carregar_bronze_favorecidos_falha_total(mock_get_client, tmp_path):
    mock_get_client.side_effect = Exception("Erro GCS")
    pasta_vazia = tmp_path / "vazia"
    pasta_vazia.mkdir()

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": ""}), pytest.raises(FileNotFoundError):
        carregar_bronze_favorecidos(origem_local=pasta_vazia, diretorio_csv=pasta_vazia)


@patch("etl_emendas_parlamentares.processamento.silver_favorecidos.carregar_bronze_favorecidos")
def test_processar_silver_fato_favorecidos(mock_carregar, tmp_path, bronze_favorecidos_sample_df):
    mock_carregar.return_value = bronze_favorecidos_sample_df

    pasta_silver = tmp_path / "silver"
    arquivo_gerado = processar_silver_fato_favorecidos(pasta_destino=pasta_silver)

    assert arquivo_gerado.exists()
    assert arquivo_gerado.name == "fato_favorecidos.parquet"

    df_resultado = pl.read_parquet(arquivo_gerado)

    # 1. Filtro: expurga 'Sem informação' e nulos em codigo_da_emenda
    assert "Sem informação" not in df_resultado["codigo_da_emenda"].to_list()
    assert df_resultado["codigo_da_emenda"].null_count() == 0

    # 2. Total de registros válidos (4 linhas preservadas, sem perda de relações)
    assert df_resultado.shape[0] == 4

    # 3. 15 colunas esperadas
    assert df_resultado.shape[1] == 15
    assert "data_referencia" in df_resultado.columns
    assert "dt_atualizacao" in df_resultado.columns
    assert "_source_file" in df_resultado.columns

    # 4. Tipagem
    assert df_resultado.schema["codigo_da_emenda"] == pl.Int64
    assert df_resultado.schema["codigo_do_autor_da_emenda"] == pl.Int64
    assert df_resultado.schema["codigo_do_favorecido"] == pl.String
    assert df_resultado.schema["numero_da_emenda"] == pl.Int64
    assert df_resultado.schema["data_referencia"] == pl.Date
    assert df_resultado.schema["valor_recebido"] == pl.Float64

    # 5. Validação da data_referencia (ano_mes '202405' -> '2024-05-01')
    datas = df_resultado["data_referencia"].to_list()
    assert any(str(d) == "2024-05-01" for d in datas)
    assert any(str(d) == "2024-06-01" for d in datas)

    # 6. Conversão de valores monetários
    val_row_c4 = df_resultado.filter(pl.col("codigo_da_emenda") == 20240003)
    assert val_row_c4["valor_recebido"][0] == 1250000.75

    val_row_f1_b = df_resultado.filter(pl.col("codigo_da_emenda") == 20240002)
    assert val_row_f1_b["valor_recebido"][0] == 250000.50

    # 7. Preservação de UF e Município originais
    assert val_row_c4["uf_favorecido"][0] == "-1"
    assert val_row_c4["municipio_favorecido"][0] == "Sem informação"
    assert val_row_f1_b["uf_favorecido"][0] == "SP"
    assert val_row_f1_b["municipio_favorecido"][0] == "SÃO PAULO"
