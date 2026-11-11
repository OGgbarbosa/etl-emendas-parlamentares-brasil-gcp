"""Módulos coletores (spiders) para cada fonte mapeada da esteira de Web Scraping."""

from etl_emendas_parlamentares.scraping.client import RespostaColeta, ScrapingHttpClient
from etl_emendas_parlamentares.scraping.spiders.spider_cgu import (
    coletar_central_emendas,
    coletar_cgu,
)
from etl_emendas_parlamentares.scraping.spiders.spider_ebc import coletar_ebc
from etl_emendas_parlamentares.scraping.spiders.spider_folha import coletar_folha
from etl_emendas_parlamentares.scraping.spiders.spider_senado import coletar_senado
from etl_emendas_parlamentares.scraping.spiders.spider_transp_brasil import coletar_transp_brasil

__all__ = [
    "coletar_central_emendas",
    "coletar_cgu",
    "coletar_ebc",
    "coletar_folha",
    "coletar_senado",
    "coletar_todas_as_fontes",
    "coletar_transp_brasil",
]


def coletar_todas_as_fontes(
    client: ScrapingHttpClient | None = None,
    max_artigos_por_fonte: int = 5,
    incluir_sementes: bool = True,
) -> dict[str, list[RespostaColeta]]:
    """Executa todos os 6 spiders oficiais e retorna o mapa de coletas por fonte."""
    http = client or ScrapingHttpClient()
    return {
        "folha": coletar_folha(client=http, max_artigos=max_artigos_por_fonte, incluir_sementes=incluir_sementes),
        "ebc": coletar_ebc(client=http, max_artigos=max_artigos_por_fonte, incluir_sementes=incluir_sementes),
        "senado": coletar_senado(client=http, max_artigos=max_artigos_por_fonte, incluir_sementes=incluir_sementes),
        "transp_brasil": coletar_transp_brasil(
            client=http, max_artigos=max_artigos_por_fonte, incluir_sementes=incluir_sementes
        ),
        "cgu": coletar_cgu(client=http, incluir_sementes=incluir_sementes),
        "central_emendas": coletar_central_emendas(client=http, incluir_sementes=incluir_sementes),
    }
