from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from etl_emendas_parlamentares.ingestao.upload_gold import (
    executar_script_gold,
    garantir_dataset_existe,
    ordenar_scripts_gold,
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
    sql = "SELECT * FROM `{PROJECT_ID}.2_silver.fato_emendas`"
    resultado = preparar_sql_query(
        conteudo_sql=sql,
        projeto_destino="meu-projeto-prod",
        silver_dataset="silver_custom",
        gold_dataset="gold_custom",
    )
    assert "meu-projeto-prod" in resultado
    assert "silver_custom" in resultado
    assert "{PROJECT_ID}" not in resultado


def test_ordenar_scripts_gold():
    scripts = [
        Path("sql/gold/view_ai_execucao_parlamentar.sql"),
        Path("sql/gold/gold_execucao_parlamentar.sql"),
        Path("sql/gold/view_ai_distribuicao_geografica.sql"),
        Path("sql/gold/gold_distribuicao_geografica.sql"),
    ]

    ordenados = ordenar_scripts_gold(scripts, incluir_views_semanticas=True)
    nomes = [s.name for s in ordenados]
    assert nomes == [
        "gold_distribuicao_geografica.sql",
        "gold_execucao_parlamentar.sql",
        "view_ai_distribuicao_geografica.sql",
        "view_ai_execucao_parlamentar.sql",
    ]

    somente_tabelas = ordenar_scripts_gold(scripts, incluir_views_semanticas=False)
    nomes_tabelas = [s.name for s in somente_tabelas]
    assert nomes_tabelas == [
        "gold_distribuicao_geografica.sql",
        "gold_execucao_parlamentar.sql",
    ]


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
    (pasta_sql / "view_ai_teste.sql").write_text("SELECT 2;", encoding="utf-8")
    (pasta_sql / "gold_teste.sql").write_text("SELECT 1;", encoding="utf-8")

    resultado = upload_gold(diretorio_sql=pasta_sql)

    assert len(resultado) == 2
    # Garante que gold_teste roda antes de view_ai_teste
    assert resultado[0] == "gold_teste.sql"
    assert resultado[1] == "view_ai_teste.sql"
    assert mock_client.query.call_count == 2
