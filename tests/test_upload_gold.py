from unittest.mock import MagicMock, patch

import pytest

from etl_emendas_parlamentares.ingestao.upload_gold import (
    executar_script_gold,
    garantir_dataset_existe,
    preparar_sql_query,
    upload_gold,
)


def test_garantir_dataset_existe_sucesso():
    mock_client = MagicMock()
    mock_client.project = "test-project"
    garantir_dataset_existe(mock_client, "3_gold")
    mock_client.get_dataset.assert_called_once()
    mock_client.create_dataset.assert_not_called()


def test_garantir_dataset_existe_cria_quando_ausente():
    mock_client = MagicMock()
    mock_client.project = "test-project"
    mock_client.get_dataset.side_effect = Exception("Not found")

    garantir_dataset_existe(mock_client, "3_gold")
    mock_client.create_dataset.assert_called_once()


def test_preparar_sql_query():
    sql = "SELECT * FROM `project-f2711ebc-82b0-49cb-b84.2_silver.fato_emendas`"
    resultado = preparar_sql_query(
        conteudo_sql=sql,
        projeto_destino="meu-projeto-prod",
        silver_dataset="silver_custom",
        gold_dataset="gold_custom",
    )
    assert "meu-projeto-prod" in resultado
    assert "silver_custom" in resultado
    assert "project-f2711ebc-82b0-49cb-b84" not in resultado


def test_executar_script_gold_sucesso(tmp_path):
    arquivo_sql = tmp_path / "teste_mart.sql"
    arquivo_sql.write_text("CREATE OR REPLACE TABLE `3_gold.tbl_teste` AS SELECT 1;", encoding="utf-8")

    mock_client = MagicMock()
    mock_client.project = "test-proj"
    mock_job = MagicMock()
    mock_client.query.return_value = mock_job

    nome = executar_script_gold(arquivo_sql, client=mock_client)

    assert nome == "teste_mart.sql"
    mock_client.query.assert_called_once()
    mock_job.result.assert_called_once()


def test_executar_script_gold_arquivo_nao_encontrado():
    with pytest.raises(FileNotFoundError):
        executar_script_gold("caminho_inexistente/mart.sql")


def test_upload_gold_diretorio_inexistente(tmp_path):
    caminho = tmp_path / "pasta_inexistente"
    resultado = upload_gold(diretorio_sql=caminho)
    assert resultado == []


def test_upload_gold_diretorio_vazio(tmp_path):
    pasta_vazia = tmp_path / "sql_gold_vazia"
    pasta_vazia.mkdir()
    resultado = upload_gold(diretorio_sql=pasta_vazia)
    assert resultado == []


@patch("etl_emendas_parlamentares.ingestao.upload_gold.get_bigquery_client")
def test_upload_gold_execucao_completa(mock_get_client, tmp_path):
    mock_client = MagicMock()
    mock_client.project = "test-project"
    mock_job = MagicMock()
    mock_client.query.return_value = mock_job
    mock_get_client.return_value = mock_client

    pasta_sql = tmp_path / "gold"
    pasta_sql.mkdir()
    (pasta_sql / "mart1.sql").write_text("SELECT 1;", encoding="utf-8")
    (pasta_sql / "mart2.sql").write_text("SELECT 2;", encoding="utf-8")

    resultado = upload_gold(diretorio_sql=pasta_sql)

    assert len(resultado) == 2
    assert "mart1.sql" in resultado
    assert "mart2.sql" in resultado
    assert mock_client.query.call_count == 2
