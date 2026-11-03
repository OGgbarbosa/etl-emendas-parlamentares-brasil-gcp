"""Módulo de auditoria e reconciliação de integridade entre as camadas Bronze e Silver.

Gera métricas automatizadas de contagem de registros, expurgos, uso de valores sentinela
e reconciliação contábil-financeira para validação e auditoria contínua do pipeline.
"""

import logging
from dataclasses import dataclass

import polars as pl

logger = logging.getLogger(__name__)


@dataclass
class MetricasReconciliacao:
    """Estrutura de dados contendo as métricas de auditoria entre Bronze e Silver."""

    entidade: str
    linhas_bronze: int
    linhas_silver: int
    linhas_descartadas: int
    pct_linhas_descartadas: float
    linhas_com_sentinela: int
    pct_linhas_sentinela: float
    metrica_financeira: str
    valor_bronze: float
    valor_silver: float
    valor_descartado: float
    pct_valor_descartado: float
    pct_preservacao_financeira: float


def extrair_valor_numerico(df: pl.DataFrame, coluna: str) -> float:
    """Extrai com segurança a soma de uma coluna monetária (em string ou float)."""
    if coluna not in df.columns:
        return 0.0

    serie = df[coluna]
    if serie.dtype == pl.Float64 or serie.dtype == pl.Float32:
        return float(serie.fill_null(0.0).sum())

    # Tratamento caso venha em formato string monetária PT-BR (ex: "1.250,50")
    total = (
        serie.cast(pl.Utf8)
        .str.replace_all(r"\.", "")
        .str.replace(",", ".")
        .cast(pl.Float64, strict=False)
        .fill_null(0.0)
        .sum()
    )
    return float(total)


def calcular_reconciliacao(
    df_bronze: pl.DataFrame,
    df_silver: pl.DataFrame,
    entidade: str,
    col_valor_bronze: str,
    col_valor_silver: str,
    nome_metrica: str,
) -> MetricasReconciliacao:
    """Calcula indicadores de reconciliação quantitativa e financeira entre Bronze e Silver."""
    linhas_bronze = len(df_bronze)
    linhas_silver = len(df_silver)
    linhas_descartadas = max(0, linhas_bronze - linhas_silver)
    pct_linhas_descartadas = (linhas_descartadas / linhas_bronze * 100.0) if linhas_bronze > 0 else 0.0

    linhas_com_sentinela = 0
    if "codigo_emenda_informado" in df_silver.columns:
        linhas_com_sentinela = len(df_silver.filter(~pl.col("codigo_emenda_informado")))
    elif "codigo_da_emenda" in df_silver.columns:
        linhas_com_sentinela = len(df_silver.filter(pl.col("codigo_da_emenda") == -1))
    pct_linhas_sentinela = (linhas_com_sentinela / linhas_silver * 100.0) if linhas_silver > 0 else 0.0

    valor_bronze = extrair_valor_numerico(df_bronze, col_valor_bronze)
    valor_silver = extrair_valor_numerico(df_silver, col_valor_silver)
    valor_descartado = max(0.0, valor_bronze - valor_silver)
    pct_valor_descartado = (valor_descartado / valor_bronze * 100.0) if valor_bronze > 0 else 0.0
    pct_preservacao = (valor_silver / valor_bronze * 100.0) if valor_bronze > 0 else 100.0

    return MetricasReconciliacao(
        entidade=entidade,
        linhas_bronze=linhas_bronze,
        linhas_silver=linhas_silver,
        linhas_descartadas=linhas_descartadas,
        pct_linhas_descartadas=round(pct_linhas_descartadas, 2),
        linhas_com_sentinela=linhas_com_sentinela,
        pct_linhas_sentinela=round(pct_linhas_sentinela, 2),
        metrica_financeira=nome_metrica,
        valor_bronze=round(valor_bronze, 2),
        valor_silver=round(valor_silver, 2),
        valor_descartado=round(valor_descartado, 2),
        pct_valor_descartado=round(pct_valor_descartado, 2),
        pct_preservacao_financeira=round(pct_preservacao, 2),
    )


def logar_relatorio_reconciliacao(metricas: list[MetricasReconciliacao]) -> None:
    """Emite log estruturado do relatório de reconciliação de integridade entre camadas."""
    sep = "=" * 115
    logger.info(sep)
    logger.info("RELATÓRIO DE AUDITORIA E RECONCILIAÇÃO DE INTEGRIDADE (BRONZE ➔ SILVER)")
    logger.info(sep)
    logger.info(
        f"{'Entidade':<14} | {'Linhas Bronze':<13} | {'Linhas Silver':<13} | "
        f"{'Sentinelas (-1)':<15} | {'Preservação %':<13} | {'Métrica':<15} | {'Valor Silver (R$)'}"
    )
    logger.info("-" * 115)

    for m in metricas:
        sentinela_info = f"{m.linhas_com_sentinela:,} ({m.pct_linhas_sentinela}%)"
        logger.info(
            f"{m.entidade:<14} | {m.linhas_bronze:<13,} | {m.linhas_silver:<13,} | "
            f"{sentinela_info:<15} | {m.pct_preservacao_financeira:>12.2f}% | "
            f"{m.metrica_financeira:<15} | R$ {m.valor_silver:,.2f}"
        )
    logger.info(sep)
