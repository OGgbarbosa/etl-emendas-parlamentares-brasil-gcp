"""Módulo para leitura e ingestão de dados de Emendas Parlamentares."""

from etl_emendas_parlamentares.processamento.normalizar import (
    normalizar_colunas,
    sanitizar_nome_coluna,
)

__all__ = ["normalizar_colunas", "sanitizar_nome_coluna"]
