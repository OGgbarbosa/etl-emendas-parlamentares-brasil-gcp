"""Definições de tabelas Delta Live Tables (DLT) para a Camada Bronze."""

from pyspark import pipelines as dp

from etl_emendas_parlamentares.emendas import (
    ler_convenios,
    ler_emendas,
    ler_favorecidos,
)


@dp.table(
    comment="Tabela Bronze - Emendas Parlamentares (dados brutos do CSV)"
)
def bronze_emendas_parlamentares():
    """Ingestão do CSV EmendasParlamentares.csv para tabela Delta Bronze."""
    return ler_emendas()


@dp.table(
    comment="Tabela Bronze - Convênios de Emendas Parlamentares (dados brutos do CSV)"
)
def bronze_emendas_convenios():
    """Ingestão do CSV EmendasParlamentares_Convenios.csv para tabela Delta Bronze."""
    return ler_convenios()


@dp.table(
    comment="Tabela Bronze - Favorecidos de Emendas Parlamentares (dados brutos do CSV)"
)
def bronze_emendas_favorecidos():
    """Ingestão do CSV EmendasParlamentares_PorFavorecido.csv para tabela Delta Bronze."""
    return ler_favorecidos()
