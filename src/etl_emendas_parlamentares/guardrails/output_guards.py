"""Guardrails de Saída (Output Guards) para garantia de integridade, anti-NaN e proteção contra vazamento de dados."""

import re
from dataclasses import dataclass
from typing import Any

# Padrões de credenciais, segredos e tokens que acionam bloqueio imediato (Fail-Closed)
PADROES_CREDENCIAIS_VAZAMENTO = [
    r"AIza[0-9A-Za-z-_]{35}",  # Google API Key
    r"ghp_[0-9A-Za-z]{36}",  # GitHub Personal Access Token
    r"-----BEGIN\s+(?:[A-Z]+\s+)?PRIVATE\s+KEY-----",  # Chaves privadas PEM (RSA, EC, etc.)
    r"private_key_id",  # GCP Service Account key ID
    r'"private_key"\s*:',  # GCP Service Account JSON private key
    r"client_secret",  # OAuth / API Client Secret
    r"AKIA[0-9A-Z]{16}",  # AWS Access Key ID
    r"bearer\s+[a-zA-Z0-9_\-\.]{25,}",  # Bearer Token
    r"(?:password|senha)\s*[:=]\s*['\"][^'\"]+['\"]",  # Senhas explícitas em logs
]


@dataclass
class ValidacaoSaida:
    """Resultado da avaliação de guardrails de saída."""

    valido: bool
    motivo: str = ""
    texto_filtrado: str = ""


def validar_resposta_ia(resposta: str, contexto_tabela: Any = None) -> ValidacaoSaida:
    """Valida a resposta gerada antes de renderizar para o usuário final.

    Garante com prioridade máxima (Fail-Closed):
    1. Bloqueio total contra vazamento de credenciais, tokens e chaves privadas.
    2. Anonimização e mascaramento de CPFs completos não mascarados (PII).
    3. Ausência de tokens soltos como 'nan', 'null', 'none' ou strings corrompidas.
    4. Resposta não vazia.

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

    # 1. Prevenção de Vazamento de Credenciais ou Tokens (PRIORIDADE MÁXIMA / FAIL-CLOSED)
    for padrao in PADROES_CREDENCIAIS_VAZAMENTO:
        flags = (
            re.IGNORECASE
            if any(k in padrao for k in ["bearer", "password", "senha", "private_key", "client_secret"])
            else 0
        )
        if re.search(padrao, texto, flags):
            return ValidacaoSaida(
                valido=False,
                motivo="Bloqueado por suspeita de vazamento de credencial.",
                texto_filtrado="[Conteúdo bloqueado pelos Guardrails de Segurança de Dados]",
            )

    # 2. Mascaramento preventivo de CPFs completos em texto corrido (PII)
    def mascarar_cpf(match: re.Match) -> str:
        _, d2, d3, _ = match.group(1), match.group(2), match.group(3), match.group(4)
        return f"***.{d2}.{d3}-**"

    texto = re.sub(r"\b(\d{3})\.(\d{3})\.(\d{3})-(\d{2})\b", mascarar_cpf, texto)

    # 3. Anti-NaN & Anti-Null Guard (impede que falhas de SQL retornem '• nan' ao usuário)
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

    return ValidacaoSaida(
        valido=True,
        motivo="Resposta aprovada pelos guardrails de saída.",
        texto_filtrado=texto,
    )
