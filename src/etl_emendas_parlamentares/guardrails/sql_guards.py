"""Guardrails para validação de integridade em consultas e views semânticas BigQuery."""

import re


def validar_consulta_sql(sql: str) -> bool:
    """Garante que a consulta gerada para BigQuery seja estritamente somente-leitura (DQL).

    Args:
        sql: Query SQL a ser executada.

    Returns:
        bool: True se for leitura segura, False se contiver comandos perigosos.
    """
    if not sql or not sql.strip():
        return False

    comandos_proibidos = [
        r"\bDROP\b",
        r"\bDELETE\b",
        r"\bUPDATE\b",
        r"\bINSERT\b",
        r"\bALTER\b",
        r"\bTRUNCATE\b",
        r"\bGRANT\b",
        r"\bREVOKE\b",
    ]

    for cmd in comandos_proibidos:
        if re.search(cmd, sql, re.IGNORECASE):
            return False

    # Deve iniciar com SELECT ou WITH
    return bool(re.match(r"^\s*(SELECT|WITH)\b", sql, re.IGNORECASE))
