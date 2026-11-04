from pathlib import Path

import pytest

from etl_emendas_parlamentares.config.config import DIRETORIO_GOLD_SQL
from etl_emendas_parlamentares.ingestao.upload_gold import preparar_sql_query

VIEWS_ESPERADAS = [
    "view_ai_execucao_parlamentar.sql",
    "view_ai_distribuicao_geografica.sql",
    "view_ai_politicas_publicas.sql",
    "view_ai_ranking_favorecidos.sql",
    "view_ai_painel_convenios.sql",
]


@pytest.fixture
def diretorio_sql() -> Path:
    return Path(DIRETORIO_GOLD_SQL)


def test_existencia_arquivos_views_semanticas(diretorio_sql: Path):
    for nome_view in VIEWS_ESPERADAS:
        caminho = diretorio_sql / nome_view
        assert caminho.exists(), f"Arquivo da view semântica {nome_view} não encontrado em {diretorio_sql}"


@pytest.mark.parametrize("nome_view", VIEWS_ESPERADAS)
def test_estrutura_ddl_view_semantica(diretorio_sql: Path, nome_view: str):
    conteudo = (diretorio_sql / nome_view).read_text(encoding="utf-8")

    # Verifica declaração de view
    assert "CREATE OR REPLACE VIEW" in conteudo, f"{nome_view} deve conter CREATE OR REPLACE VIEW"

    # Verifica presença de descrições em nível de coluna e view
    assert "OPTIONS(description=" in conteudo, f"{nome_view} deve possuir OPTIONS(description=...)"

    # Verifica presença de labels para governança
    assert "labels=[" in conteudo, f"{nome_view} deve conter labels=[...] para catalogação"
    assert '("camada", "gold_semantica")' in conteudo
    assert '("consumidor", "vertex_ai_gemini")' in conteudo

    # Verifica coluna mandatória de narrativa para RAG
    assert "DS_RESUMO_SEMANTICO" in conteudo, f"{nome_view} deve conter a coluna DS_RESUMO_SEMANTICO"


def test_view_execucao_parlamentar_especificidades(diretorio_sql: Path):
    conteudo = (diretorio_sql / "view_ai_execucao_parlamentar.sql").read_text(encoding="utf-8")
    assert "3_gold.tbl_execucao_parlamentar" in conteudo
    assert "FL_AUTOR_IDENTIFICADO" in conteudo
    assert "TX_EXECUCAO" in conteudo
    assert "TX_LIQUIDACAO" in conteudo
    assert "VL_RESTOS_SALDO_A_PAGAR" in conteudo


def test_view_distribuicao_geografica_especificidades(diretorio_sql: Path):
    conteudo = (diretorio_sql / "view_ai_distribuicao_geografica.sql").read_text(encoding="utf-8")
    assert "3_gold.tbl_distribuicao_geografica" in conteudo
    assert "FL_MUNICIPIO_ESPECIFICO" in conteudo
    assert "DS_AMBITO_GEOGRAFICO" in conteudo
    assert "TKM_PAGO_POR_EMENDA" in conteudo


def test_view_politicas_publicas_especificidades(diretorio_sql: Path):
    conteudo = (diretorio_sql / "view_ai_politicas_publicas.sql").read_text(encoding="utf-8")
    assert "3_gold.tbl_politicas_publicas" in conteudo
    assert "DS_TENDENCIA_YOY" in conteudo
    assert "PC_REPRESENTATIVIDADE_PAGO" in conteudo
    assert "TX_CRESCIMENTO_YOY_PAGO" in conteudo


def test_view_ranking_favorecidos_especificidades(diretorio_sql: Path):
    conteudo = (diretorio_sql / "view_ai_ranking_favorecidos.sql").read_text(encoding="utf-8")
    assert "3_gold.tbl_ranking_favorecidos" in conteudo
    assert "FL_FAVORECIDO_MULTI_PARLAMENTAR" in conteudo
    assert "VL_RECEBIDO_ACUMULADO_ATE_ANO" in conteudo
    assert "VL_RECEBIDO_TOTAL_HISTORICO" in conteudo


def test_view_painel_convenios_especificidades(diretorio_sql: Path):
    conteudo = (diretorio_sql / "view_ai_painel_convenios.sql").read_text(encoding="utf-8")
    assert "3_gold.tbl_painel_convenios" in conteudo
    assert "FL_ANO_PUBLICACAO_VALIDO" in conteudo
    assert "VL_TOTAL_CONVENIADO" in conteudo
    assert "TKM_VALOR_POR_CONVENIO" in conteudo


@pytest.mark.parametrize("nome_view", VIEWS_ESPERADAS)
def test_portabilidade_sql_views_semanticas(diretorio_sql: Path, nome_view: str):
    conteudo = (diretorio_sql / nome_view).read_text(encoding="utf-8")
    query_ajustada = preparar_sql_query(
        conteudo_sql=conteudo,
        projeto_destino="meu-projeto-ia-teste",
        gold_dataset="gold_prod",
    )
    assert "meu-projeto-ia-teste" in query_ajustada
    assert "gold_prod" in query_ajustada
    assert "{PROJECT_ID}" not in query_ajustada
