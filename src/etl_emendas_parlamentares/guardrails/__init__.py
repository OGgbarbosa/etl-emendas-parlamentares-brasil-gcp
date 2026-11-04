"""Módulo de Guardrails do Observatório de Emendas Parlamentares.

Fornece defesas multicamadas para validação de entrada, prevenção de injeção de prompt,
integridade de saída (anti-NaN, anti-alucinação) e governança orçamentária para IA.
"""

from .input_guards import ValidacaoEntrada, validar_prompt_usuario
from .output_guards import ValidacaoSaida, validar_resposta_ia
from .sql_guards import validar_consulta_sql

__all__ = [
    "ValidacaoEntrada",
    "ValidacaoSaida",
    "validar_consulta_sql",
    "validar_prompt_usuario",
    "validar_resposta_ia",
]
