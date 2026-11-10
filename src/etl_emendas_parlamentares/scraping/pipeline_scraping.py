"""Orquestrador geral da esteira de Web Scraping (Coleta ➔ Silver Raw ➔ Fato Notícias Contexto)."""

import logging
import sys
from pathlib import Path

_src_dir = str(Path(__file__).resolve().parent.parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import pandas as pd
from google.cloud import bigquery

from etl_emendas_parlamentares.scraping.carga_silver_raw import (
    carregar_lote_raw_fonte,
    garantir_tabelas_raw_existem,
)
from etl_emendas_parlamentares.scraping.client import RespostaColeta, ScrapingHttpClient
from etl_emendas_parlamentares.scraping.processar_contexto import materializar_fato_noticias_contexto
from etl_emendas_parlamentares.scraping.spiders import coletar_todas_as_fontes

logger = logging.getLogger(__name__)


def executar_pipeline_scraping(
    client_http: ScrapingHttpClient | None = None,
    client_bq: bigquery.Client | None = None,
    max_artigos_por_fonte: int = 4,
    incluir_sementes: bool = True,
    diretorio_scraping_local: str | Path | None = None,
    diretorio_silver_local: str | Path | None = None,
) -> pd.DataFrame:
    """Executa a esteira completa de Web Scraping (Fontes ➔ raw_scraping_* ➔ fato_noticias_contexto)."""
    logger.info("=== Iniciando Pipeline de Web Scraping & Contexto Qualitativo ===")

    try:
        garantir_tabelas_raw_existem(client=client_bq)
    except Exception as exc:
        logger.warning("Não foi possível validar tabelas brutas no início (continuando com fallback): %s", exc)

    mapa_coletas = coletar_todas_as_fontes(
        client=client_http,
        max_artigos_por_fonte=max_artigos_por_fonte,
        incluir_sementes=incluir_sementes,
    )

    todas_respostas: list[RespostaColeta] = []
    total_inseridos_bq = 0

    for id_fonte, lista_respostas in mapa_coletas.items():
        todas_respostas.extend(lista_respostas)
        inseridos = carregar_lote_raw_fonte(
            id_fonte=id_fonte,
            respostas=lista_respostas,
            client=client_bq,
            diretorio_local=diretorio_scraping_local,
        )
        total_inseridos_bq += inseridos

    df_fato = materializar_fato_noticias_contexto(
        respostas_em_memoria=todas_respostas,
        client=client_bq,
        diretorio_silver_local=diretorio_silver_local,
        diretorio_scraping_local=diretorio_scraping_local,
    )

    logger.info(
        "=== Pipeline de Scraping concluído! Coletados: %d | Novos em Raw BQ: %d | Artigos em Fato: %d ===",
        len(todas_respostas),
        total_inseridos_bq,
        len(df_fato),
    )
    return df_fato


if __name__ == "__main__":
    executar_pipeline_scraping()
