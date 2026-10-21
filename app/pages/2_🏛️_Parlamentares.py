"""Página 2: Análise por Autor e Parlamentar."""


def main() -> None:
    try:
        import streamlit as st
    except ImportError:
        return

    st.set_page_config(page_title="Parlamentares - Emendas", page_icon="🏛️", layout="wide")
    st.title("🏛️ Execução por Parlamentar")
    st.info("Painel em construção. Conectará com `gold_execucao_parlamentar`.")


if __name__ == "__main__":
    main()

