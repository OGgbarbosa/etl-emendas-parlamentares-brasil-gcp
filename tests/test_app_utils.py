from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from app.utils.db import carregar_kpis_macro, carregar_tabela_gold
from app.utils.formatters import (
    formatar_documento,
    formatar_moeda,
    formatar_numero,
    formatar_percentual,
)
from app.utils.styles import renderizar_card_metrica, renderizar_hero


def test_formatar_moeda():
    assert formatar_moeda(1234567.89) == "R$ 1.234.567,89"
    assert formatar_moeda(0) == "R$ 0,00"
    assert formatar_moeda(None) == "R$ 0,00"
    assert formatar_moeda(float("nan")) == "R$ 0,00"
    assert formatar_moeda(-500.5) == "-R$ 500,50"


def test_formatar_moeda_abreviado():
    assert formatar_moeda(2_500_000_000, abreviado=True) == "R$ 2,50 Bi"
    assert formatar_moeda(45_600_000, abreviado=True) == "R$ 45,60 Mi"
    assert formatar_moeda(850_000, abreviado=True) == "R$ 850,00 Mil"
    assert formatar_moeda(350.50, abreviado=True) == "R$ 350,50"
    assert formatar_moeda(-1_200_000_000, abreviado=True) == "-R$ 1,20 Bi"


def test_formatar_percentual():
    assert formatar_percentual(85.456) == "85,46%"
    assert formatar_percentual(100.0, casas=1) == "100,0%"
    assert formatar_percentual(None) == "0,00%"
    assert formatar_percentual(float("nan")) == "0,00%"


def test_formatar_numero():
    assert formatar_numero(54321) == "54.321"
    assert formatar_numero(1000000) == "1.000.000"
    assert formatar_numero(None) == "0"
    assert formatar_numero(float("nan")) == "0"


def test_formatar_documento():
    # CNPJ com 14 dígitos
    assert formatar_documento("00000000000191") == "00.000.000/0001-91"
    # CPF com 11 dígitos mascarado
    assert formatar_documento("12345678901") == "***.456.789-**"
    # Texto genérico
    assert formatar_documento("PREFEITURA MUNICIPAL") == "PREFEITURA MUNICIPAL"
    assert formatar_documento(None) == "Não informado"


def test_styles_renderizacao():
    # Garante que as funções de renderização HTML não quebram
    with patch("streamlit.markdown") as mock_markdown:
        renderizar_hero("Título Teste", "Subtítulo Teste")
        mock_markdown.assert_called_once()

    with patch("streamlit.markdown") as mock_markdown:
        renderizar_card_metrica("Label", "R$ 100", "Sub")
        mock_markdown.assert_called_once()


@patch("app.utils.db.get_bigquery_client")
def test_carregar_tabela_gold_sucesso(mock_get_client):
    mock_client = MagicMock()
    mock_client.project = "test-project"
    mock_job = MagicMock()
    mock_df = pd.DataFrame({"col1": [1, 2], "col2": ["A", "B"]})
    mock_job.to_dataframe.return_value = mock_df
    mock_client.query.return_value = mock_job
    mock_get_client.return_value = mock_client

    df = carregar_tabela_gold(
        nome_tabela="tbl_teste",
        query_filtro="col1 > 0",
        colunas=["col1", "col2"],
    )

    assert not df.empty
    assert len(df) == 2
    mock_client.query.assert_called_once()
    sql_executada = mock_client.query.call_args[0][0]
    assert "SELECT col1, col2 FROM `test-project.3_gold.tbl_teste` WHERE col1 > 0" in sql_executada


@patch("app.utils.db.get_bigquery_client")
def test_carregar_kpis_macro_sucesso(mock_get_client):
    mock_client = MagicMock()
    mock_client.project = "test-project"

    df_macro = pd.DataFrame(
        [
            {
                "total_empenhado": 1000000.0,
                "total_liquidado": 800000.0,
                "total_pago": 700000.0,
                "total_restos_saldo": 200000.0,
                "qtd_parlamentares": 150,
            }
        ]
    )
    df_geo = pd.DataFrame([{"qtd_municipios": 450}])

    job1 = MagicMock()
    job1.to_dataframe.return_value = df_macro
    job2 = MagicMock()
    job2.to_dataframe.return_value = df_geo

    mock_client.query.side_effect = [job1, job2]
    mock_get_client.return_value = mock_client

    kpis = carregar_kpis_macro()

    assert kpis["total_empenhado"] == 1000000.0
    assert kpis["total_pago"] == 700000.0
    assert kpis["qtd_municipios"] == 450
    assert kpis["qtd_parlamentares"] == 150


def test_skill_frontend_design_instalada():
    caminho_skill = Path(".agents/skills/frontend-design/SKILL.md")
    caminho_lic = Path(".agents/skills/frontend-design/LICENSE.txt")
    assert caminho_skill.exists(), "SKILL.md deve existir no diretório .agents/skills/frontend-design"
    assert caminho_lic.exists(), "LICENSE.txt deve existir no diretório .agents/skills/frontend-design"

    conteudo = caminho_skill.read_text(encoding="utf-8")
    assert "name: frontend-design" in conteudo
    assert "description:" in conteudo
