"""Guardrails de Entrada (Input Guards) para proteção e validação de prompts de IA."""

import re
from dataclasses import dataclass

PADROES_INJECAO = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"esqueça\s+(todas\s+as\s+)?instruções\s+(anteriores)?",
    r"system\s*prompt",
    r"you\s+are\s+now",
    r"agora\s+você\s+é",
    r"drop\s+table",
    r"delete\s+from",
    r"insert\s+into",
    r"update\s+.*\s+set",
]

TERMOS_FORA_DO_ESCOPO = [
    "receita de bolo",
    "previsão do tempo",
    "horóscopo",
    "criptomoeda",
]


@dataclass
class ValidacaoEntrada:
    """Resultado da avaliação de guardrails de entrada."""

    valido: bool
    motivo: str = ""
    prompt_higienizado: str = ""


def validar_prompt_usuario(prompt: str) -> ValidacaoEntrada:
    """Valida o prompt do usuário contra injeções, abusos e perda de foco contextual.

    Args:
        prompt: Pergunta ou comando fornecido pelo usuário.

    Returns:
        ValidacaoEntrada: Status indicando se o prompt é aceito ou rejeitado.
    """
    if not prompt or not prompt.strip():
        return ValidacaoEntrada(valido=False, motivo="Prompt vazio ou em branco.")

    p_limpo = prompt.strip()

    # 1. Checagem de tamanho excessivo (DDoS / Token Overflow)
    if len(p_limpo) > 1000:
        return ValidacaoEntrada(
            valido=False,
            motivo="O prompt excede o limite máximo permitido de 1.000 caracteres.",
        )

    # 2. Detecção de Prompt Injection e SQL Malicioso
    for padrao in PADROES_INJECAO:
        if re.search(padrao, p_limpo, re.IGNORECASE):
            return ValidacaoEntrada(
                valido=False,
                motivo="Tentativa de injeção de prompt ou comando não autorizado detectada.",
            )

    # 3. Verificação de Escopo Temático (Apenas Orçamento & Emendas)
    p_lower = p_limpo.lower()
    for termo in TERMOS_FORA_DO_ESCOPO:
        if termo in p_lower:
            return ValidacaoEntrada(
                valido=False,
                motivo=f"A pergunta contém tema fora do escopo de emendas orçamentárias: '{termo}'.",
            )

    return ValidacaoEntrada(
        valido=True,
        motivo="Prompt aprovado pelos guardrails de entrada.",
        prompt_higienizado=p_limpo,
    )
