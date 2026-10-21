"""Página 3: Distribuição Geográfica e Territorial."""


def main() -> None:
    try:
        import streamlit as st
    except ImportError:
        return

    st.set_page_config(page_title="Mapa Brasil - Emendas", page_icon="🗺️", layout="wide")
    st.title("🗺️ Distribuição Geográfica de Recursos")
    st.info("Painel em construção. Conectará com `gold_distribuicao_geografica`.")


if __name__ == "__main__":
    main()

