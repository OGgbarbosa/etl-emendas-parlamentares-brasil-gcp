import polars as pl

from etl_emendas_parlamentares.processamento.reconciliacao import (
    calcular_reconciliacao,
    extrair_valor_numerico,
    logar_relatorio_reconciliacao,
)


def test_extrair_valor_numerico_float():
    df = pl.DataFrame({"valor": [100.50, 200.25, None]})
    assert extrair_valor_numerico(df, "valor") == 300.75


def test_extrair_valor_numerico_string_ptbr():
    df = pl.DataFrame({"valor": ["1.000,50", "2.500,25", None]})
    assert extrair_valor_numerico(df, "valor") == 3500.75


def test_calcular_reconciliacao_com_sentinela():
    df_bronze = pl.DataFrame(
        {
            "codigo_da_emenda": ["20240001", "20240002", "Sem informação"],
            "valor_empenhado": ["1000,00", "2000,00", "500,00"],
        }
    )
    df_silver = pl.DataFrame(
        {
            "codigo_da_emenda": [20240001, 20240002, -1],
            "codigo_emenda_informado": [True, True, False],
            "valor_empenhado": [1000.00, 2000.00, 500.00],
        }
    )

    metricas = calcular_reconciliacao(
        df_bronze=df_bronze,
        df_silver=df_silver,
        entidade="fato_teste",
        col_valor_bronze="valor_empenhado",
        col_valor_silver="valor_empenhado",
        nome_metrica="Valor Empenhado",
    )

    assert metricas.linhas_bronze == 3
    assert metricas.linhas_silver == 3
    assert metricas.linhas_descartadas == 0
    assert metricas.pct_linhas_descartadas == 0.0
    assert metricas.linhas_com_sentinela == 1
    assert metricas.pct_linhas_sentinela == 33.33
    assert metricas.valor_bronze == 3500.00
    assert metricas.valor_silver == 3500.00
    assert metricas.valor_descartado == 0.0
    assert metricas.pct_preservacao_financeira == 100.0


def test_logar_relatorio_reconciliacao(caplog):
    df_b = pl.DataFrame({"codigo": ["A", "B"], "vl": [100.0, 200.0]})
    df_s = pl.DataFrame({"codigo": ["A", "B"], "codigo_emenda_informado": [True, True], "vl": [100.0, 200.0]})

    m = calcular_reconciliacao(df_b, df_s, "fato_teste", "vl", "vl", "Valor")
    with caplog.at_level("INFO"):
        logar_relatorio_reconciliacao([m])

    assert "RELATÓRIO DE AUDITORIA E RECONCILIAÇÃO" in caplog.text
    assert "fato_teste" in caplog.text
