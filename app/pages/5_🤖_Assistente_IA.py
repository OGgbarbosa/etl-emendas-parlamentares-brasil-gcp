"""Página 5: Assistente e Chatbot em Linguagem Natural com Vertex AI."""


def main() -> None:
    try:
        import streamlit as st
    except ImportError:
        return

    st.set_page_config(page_title="Assistente IA - Emendas", page_icon="🤖", layout="wide")
    st.title("🤖 Assistente IA de Consulta às Emendas")
    st.info("Painel em construção. Conectará com o Agente Gemini no Google Vertex AI.")


if __name__ == "__main__":
    main()

