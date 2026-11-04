"""Funções utilitárias de formatação monetária, numérica e textual."""

import math
import re


def formatar_moeda(valor: float | None, abreviado: bool = False) -> str:
    """Formata valores numéricos para o padrão monetário brasileiro (BRL).

    Args:
        valor: Valor numérico a ser formatado.
        abreviado: Se True, formata grandezas em Bi, Mi ou Mil (ex: R$ 1,23 Bi).

    Returns:
        str: String formatada (ex: R$ 1.234.567,89 ou R$ 1,23 Bi).
    """
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "R$ 0,00"

    v = float(valor)
    sinal = "-" if v < 0 else ""
    abs_v = abs(v)

    if abreviado:
        if abs_v >= 1_000_000_000:
            return f"{sinal}R$ {abs_v / 1_000_000_000:.2f}".replace(".", ",") + " Bi"
        if abs_v >= 1_000_000:
            return f"{sinal}R$ {abs_v / 1_000_000:.2f}".replace(".", ",") + " Mi"
        if abs_v >= 1_000:
            return f"{sinal}R$ {abs_v / 1_000:.2f}".replace(".", ",") + " Mil"
        return f"{sinal}R$ {abs_v:.2f}".replace(".", ",")

    # Formatação completa com separador de milhar '.' e decimal ','
    partes = f"{abs_v:,.2f}".split(".")
    inteiro = partes[0].replace(",", ".")
    decimal = partes[1]
    return f"{sinal}R$ {inteiro},{decimal}"


def formatar_percentual(valor: float | None, casas: int = 2) -> str:
    """Formata valores em percentual com vírgula decimal."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "0,00%"

    v = float(valor)
    return f"{v:.{casas}f}".replace(".", ",") + "%"


def formatar_numero(valor: float | None) -> str:
    """Formata inteiros com separador de milhar brasileiro."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "0"

    v = round(float(valor))
    return f"{v:,}".replace(",", ".")


def formatar_documento(doc: str | None) -> str:
    """Aplica máscara de CNPJ ou CPF quando aplicável."""
    if not doc:
        return "Não informado"

    numeros = re.sub(r"\D", "", str(doc))

    # CNPJ (14 dígitos)
    if len(numeros) == 14:
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"

    # CPF (11 dígitos) - com mascaramento de privacidade
    if len(numeros) == 11:
        return f"***.{numeros[3:6]}.{numeros[6:9]}-**"

    return str(doc).strip()
