"""Módulo para padronização e processamento de dados de Emendas Parlamentares."""

import re
import unicodedata


def sanitizar_nome_coluna(nome: str) -> str:
    """Normaliza o nome da coluna para padrão snake_case sem acentos/especiais."""
    # Remove acentuação
    nfkd = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Substitui caracteres especiais/espaços por underscore
    substituido = re.sub(r"[^a-zA-Z0-9]", "_", sem_acento)
    # Remove underscores duplicados e limpa pontas
    limpo = re.sub(r"_+", "_", substituido).strip("_").lower()
    return limpo or "coluna"
