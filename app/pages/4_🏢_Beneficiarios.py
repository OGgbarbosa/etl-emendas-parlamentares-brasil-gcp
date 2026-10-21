"""Página 4: Maiores Favorecidos e Entidades Recebedoras."""


def main() -> None:
    try:
        import streamlit as st
    except ImportError:
        return

    st.set_page_config(page_title="Beneficiários - Emendas", page_icon="🏢", layout="wide")
    st.title("🏢 Maiores Beneficiários e Fornecedores")
    st.info("Painel em construção. Conectará com `gold_ranking_favorecidos`.")


if __name__ == "__main__":
    main()

