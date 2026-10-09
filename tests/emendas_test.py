import pytest

from etl_emendas_parlamentares.emendas import sanitizar_nome_coluna


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("Código da Emenda", "codigo_da_emenda"),
        ("Possui Apoiador/Solicitante? ", "possui_apoiador_solicitante"),
        ("Localidade de aplicação do recurso", "localidade_de_aplicacao_do_recurso"),
        ("Valor Restos A Pagar Pagos", "valor_restos_a_pagar_pagos"),
        ("   Espaços   Extras   ", "espacos_extras"),
        ("Coluna-Com-Hífen", "coluna_com_hifen"),
    ],
)
def test_sanitizar_nome_coluna(entrada, esperado):
    """Testa se a normalização de colunas remove acentos e caracteres especiais para Delta Lake."""
    assert sanitizar_nome_coluna(entrada) == esperado
