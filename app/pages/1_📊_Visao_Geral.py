"""Página 1: Visão Geral e KPIs Orçamentários Macro."""


def main() -> None:
    try:
        import streamlit as st
    except ImportError:
        return

    st.set_page_config(page_title="Visão Geral - Emendas", page_icon="📊", layout="wide")
    st.title("📊 Visão Geral do Orçamento de Emendas")
    st.info("Painel em construção. Conectará com `gold_execucao_parlamentar` e `fato_emendas`.")


if __name__ == "__main__":
    main()

