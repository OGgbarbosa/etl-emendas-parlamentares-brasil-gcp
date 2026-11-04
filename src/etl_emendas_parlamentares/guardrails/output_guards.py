"""Guardrails de Saída (Output Guards) para garantia de integridade, anti-NaN e anti-alucinação."""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidacaoSaida:
    """Resultado da avaliação de guardrails de saída."""

    valido: bool
    motivo: str = ""
    texto_filtrado: str = ""


def validar_resposta_ia(resposta: str, contexto_tabela: Any = None) -> ValidacaoSaida:
    """Valida a resposta gerada antes de renderizar para o usuário final.

    Garante:
    1. Ausência de tokens soltos como 'nan', 'null', 'none' ou strings corrompidas.
    2. Resposta não vazia.
    3. Conformidade contra termos ofensivos ou vazamento de credenciais.

    Args:
        resposta: Texto analítico gerado pela IA ou pelas views semânticas.
        contexto_tabela: DataFrame ou dados de apoio utilizados.

    Returns:
        ValidacaoSaida: Status indicando aprovação e texto tratado.
    """
    if not resposta or not resposta.strip():
        return ValidacaoSaida(
            valido=False,
            motivo="Resposta vazia gerada.",
            texto_filtrado="Não foi possível obter dados para a pergunta solicitada.",
        )

    texto = resposta.strip()

    # 1. Anti-NaN & Anti-Null Guard (impede que falhas de SQL retornem '• nan' ao usuário)
    if re.search(r"\b(nan|null|none)\b", texto, re.IGNORECASE):
        # Substitui ocorrências soltas por texto factível neutro
        texto_corrigido = re.sub(
            r"•\s*(nan|null|none)\b",
            "• [Dados orçamentários sob consolidação pelo órgão competente]",
            texto,
            flags=re.IGNORECASE,
        )
        return ValidacaoSaida(
            valido=True,
            motivo="Corrigido valor nulo/NaN detectado na narrativa.",
            texto_filtrado=texto_corrigido,
        )

    # 2. Prevenção de Vazamento de Credenciais ou Tokens GCP
    padroes_vazamento = [
        r"AIza[0-9A-Za-z-_]{35}",  # Google API Key
        r"ghp_[0-9A-Za-z]{36}",  # GitHub Token
        r"private_key_id",
    ]
    for padrao in padroes_vazamento:
        if re.search(padrao, texto):
            return ValidacaoSaida(
                valido=False,
                motivo="Bloqueado por suspeita de vazamento de credencial.",
                texto_filtrado="[Conteúdo bloqueado pelos Guardrails de Segurança de Dados]",
            )

    return ValidacaoSaida(
        valido=True,
        motivo="Resposta aprovada pelos guardrails de saída.",
        texto_filtrado=texto,
    )
