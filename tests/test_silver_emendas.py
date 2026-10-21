import io
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from etl_emendas_parlamentares.processamento.silver_emendas import (
    carregar_bronze_emendas,
    processar_silver_fato_emendas,
)


@pytest.fixture
def bronze_sample_df():
    return pl.DataFrame(
        {
            "codigo_da_emenda": [
                "20240001",
                "20240001",  # Mesma emenda com outra ação (dotação distinta)
                "Sem informação",  # Deve ser expurgado
                "20240002",
                "20240003",
            ],
            "tipo_de_emenda": ["Individual", "Individual", "Individual", "Bancada", "Individual"],
            "ano_da_emenda": ["2024", "2024", "2024", "2023", "2023"],
            "numero_da_emenda": ["1", "1", "99", "2", "3"],
            "possui_apoiador_solicitante": ["Sim", "Sim", "Sim", "Não", "Não"],
            "codigo_do_autor_da_emenda": ["100", "100", "100", "200", "300"],
            "nome_do_autor_da_emenda": ["Deputado A", "Deputado A", "Deputado A", "Deputado B", "Deputado C"],
            "codigo_funcao": ["10", "12", "10", "MU", "12"],
            "nome_funcao": ["Saúde", "Educação", "Saúde", "Múltiplo", "Educação"],
            "codigo_subfuncao": ["301", "361", "301", "MU", "361"],
            "nome_subfuncao": [
                "Atenção Básica",
                "Ensino Fundamental",
                "Atenção Básica",
                "Múltiplo",
                "Ensino Fundamental",
            ],
            "codigo_programa": ["5000", "6000", "5000", "MU", "6000"],
            "nome_programa": ["Prog A", "Prog B", "Prog A", "Prog B", "Prog C"],
            "codigo_acao": ["10A1", "20B2", "10A1", "20B2", "30C3"],
            "nome_acao": ["Ação 1", "Ação 2", "Ação 1", "Ação 2", "Ação 3"],
            "codigo_plano_orcamentario": ["0000", "0001", "0000", "0001", "0002"],
            "nome_plano_orcamentario": ["Plano 1", "Plano 2", "Plano 1", "Plano 2", "Plano 3"],
            "uf": ["SÃO PAULO", "SÃO PAULO", "SÃO PAULO", "Múltiplo", "Sem informação"],
            "codigo_municipio_ibge": ["3550308", "3550308", "Sem informação", "Sem informação", "Sem informação"],
            "localidade_de_aplicacao_do_recurso": [
                "São Paulo",
                "São Paulo",
                "São Paulo",
                "Brasil - Nacional",
                "Acre (UF)",
            ],
            "municipio": ["São Paulo", "São Paulo", "São Paulo", None, None],
            "codigo_uf_ibge": ["3500000", "3500000", "3500000", "-1", "-1"],
            "regiao": ["Sudeste", "Sudeste", "Sudeste", "Nacional", "Norte"],
            "valor_empenhado": ["100000,00", "200000,00", "50000,00", "300000,50", "400000,00"],
            "valor_liquidado": ["80000,00", "150000,00", "0,00", "250000,00", "350000,00"],
            "valor_pago": ["50000,00", "100000,00", "0,00", "200000,00", "300000,00"],
            "valor_restos_a_pagar_inscritos": ["50000,00", "100000,00", "0,00", "100000,00", "100000,00"],
            "valor_restos_a_pagar_cancelados": ["0,00", "0,00", "0,00", "0,00", "0,00"],
            "valor_restos_a_pagar_pagos": ["0,00", "0,00", "0,00", "0,00", "0,00"],
        }
    )


@patch("etl_emendas_parlamentares.processamento.silver_emendas.get_storage_client")
def test_carregar_bronze_emendas_sucesso_gcs(mock_get_client, bronze_sample_df):
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True

    buffer = io.BytesIO()
    bronze_sample_df.write_parquet(buffer)
    conteudo_bytes = buffer.getvalue()

    def download_to_file(buf):
        buf.write(conteudo_bytes)

    mock_blob.download_to_file.side_effect = download_to_file
    mock_bucket.blob.return_value = mock_blob
    mock_client.bucket.return_value = mock_bucket
    mock_get_client.return_value = mock_client

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://bucket-teste"}):
        df = carregar_bronze_emendas()

    assert df.shape == bronze_sample_df.shape
    mock_blob.download_to_file.assert_called_once()


@patch("etl_emendas_parlamentares.processamento.silver_emendas.get_storage_client")
def test_carregar_bronze_emendas_fallback_parquet_local(mock_get_client, tmp_path, bronze_sample_df):
    mock_get_client.side_effect = Exception("Conexão falhou")

    pasta_bronze = tmp_path / "bronze"
    pasta_bronze.mkdir()
    arquivo_parquet = pasta_bronze / "EmendasParlamentares.parquet"
    bronze_sample_df.write_parquet(arquivo_parquet)

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://bucket-teste"}):
        df = carregar_bronze_emendas(origem_local=pasta_bronze)

    assert df.shape == bronze_sample_df.shape
    assert set(df.columns) == set(bronze_sample_df.columns)


@patch("etl_emendas_parlamentares.processamento.silver_emendas.get_storage_client")
def test_carregar_bronze_emendas_fallback_csv_local(mock_get_client, tmp_path):
    mock_get_client.side_effect = Exception("Sem conexao")

    pasta_vazia = tmp_path / "bronze_vazia"
    pasta_vazia.mkdir()

    pasta_csv = tmp_path / "database"
    pasta_csv.mkdir()
    arquivo_csv = pasta_csv / "EmendasParlamentares.csv"
    arquivo_csv.write_text(
        "Código da Emenda;Ano da Emenda;Tipo de Emenda\n20240001;2024;Individual\n",
        encoding="latin1",
    )

    with patch.dict("os.environ", {"GCS_BUCKET_NAME": "gs://bucket-teste"}):
        df = carregar_bronze_emendas(origem_local=pasta_vazia, diretorio_csv=pasta_csv)

    assert df.shape == (1, 3)
    assert "codigo_da_emenda" in df.columns
    assert "ano_da_emenda" in df.columns
    assert "tipo_de_emenda" in df.columns


@patch("etl_emendas_parlamentares.processamento.silver_emendas.carregar_bronze_emendas")
def test_processar_silver_fato_emendas(mock_carregar, tmp_path, bronze_sample_df):
    mock_carregar.return_value = bronze_sample_df

    pasta_silver = tmp_path / "silver"
    arquivo_gerado = processar_silver_fato_emendas(pasta_destino=pasta_silver)

    assert arquivo_gerado.exists()
    assert arquivo_gerado.name == "fato_emendas.parquet"

    df_resultado = pl.read_parquet(arquivo_gerado)

    # 1. Filtra 'Sem informação'
    assert "Sem informação" not in df_resultado["codigo_da_emenda"].to_list()

    # 2. Preserva dotações distintas da mesma emenda (4 linhas válidas no total)
    assert df_resultado.shape[0] == 4
    linhas_20240001 = df_resultado.filter(pl.col("codigo_da_emenda") == 20240001)
    assert len(linhas_20240001) == 2

    # 3. 32 colunas (24 de negócio + 6 métricas financeiras + 2 de auditoria)
    assert df_resultado.shape[1] == 32
    assert "codigo_municipio_ibge" in df_resultado.columns
    assert "municipio" in df_resultado.columns
    assert "valor_empenhado" in df_resultado.columns
    assert "valor_pago" in df_resultado.columns
    assert "dt_atualizacao" in df_resultado.columns
    assert "_source_file" in df_resultado.columns

    # 4. Tipagem
    assert df_resultado.schema["codigo_da_emenda"] == pl.Int64
    assert df_resultado.schema["ano_emenda"] == pl.Int64
    assert df_resultado.schema["numero_emenda"] == pl.Int64
    assert df_resultado.schema["codigo_funcao"] == pl.Int64
    assert df_resultado.schema["codigo_municipio_ibge"] == pl.Int64
    assert df_resultado.schema["codigo_uf_ibge"] == pl.Int64
    assert df_resultado.schema["valor_empenhado"] == pl.Float64
    assert df_resultado.schema["valor_pago"] == pl.Float64

    # 5. Tratamento de 'MU' como null
    emenda_20240002 = df_resultado.filter(pl.col("codigo_da_emenda") == 20240002)
    assert emenda_20240002["codigo_funcao"][0] is None
    assert emenda_20240002["codigo_subfuncao"][0] is None
    assert emenda_20240002["codigo_programa"][0] is None

    # 6. Mapeamento de UFs e Estado
    emenda_20240001_row = df_resultado.filter(pl.col("codigo_da_emenda") == 20240001)
    assert emenda_20240001_row["Estado"][0] == "SÃO PAULO"
    assert emenda_20240001_row["uf"][0] == "SP"
    assert emenda_20240002["uf"][0] == "MULT"
    assert emenda_20240002["codigo_municipio_ibge"][0] == -14

    emenda_20240003 = df_resultado.filter(pl.col("codigo_da_emenda") == 20240003)
    assert emenda_20240003["uf"][0] == "NACI"
    assert emenda_20240003["codigo_municipio_ibge"][0] == -1

    # 7. Valores monetários convertidos
    assert emenda_20240002["valor_empenhado"][0] == 300000.50
    assert emenda_20240003["valor_pago"][0] == 300000.00
