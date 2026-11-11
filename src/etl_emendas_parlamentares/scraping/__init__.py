"""Módulo de Web Scraping e coleta de fontes jornalísticas/institucionais."""

from etl_emendas_parlamentares.scraping.client import (
    RespostaColeta,
    ScrapingHttpClient,
    calcular_hash_conteudo,
    criar_resposta_coleta,
)
from etl_emendas_parlamentares.scraping.fontes import (
    FONTES_SCRAPING,
    FonteScraping,
    listar_fontes,
    obter_fonte,
)
from etl_emendas_parlamentares.scraping.parser import (
    ArtigoProcessado,
    extrair_artigo_limpo,
    extrair_entidades_texto,
    gerar_id_artigo,
)
from etl_emendas_parlamentares.scraping.pipeline_scraping import executar_pipeline_scraping

__all__ = [
    "FONTES_SCRAPING",
    "ArtigoProcessado",
    "FonteScraping",
    "RespostaColeta",
    "ScrapingHttpClient",
    "calcular_hash_conteudo",
    "criar_resposta_coleta",
    "executar_pipeline_scraping",
    "extrair_artigo_limpo",
    "extrair_entidades_texto",
    "gerar_id_artigo",
    "listar_fontes",
    "obter_fonte",
]
