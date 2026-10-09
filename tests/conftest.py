import pathlib

import pytest

# Este arquivo centraliza configurações e fixtures do Pytest.
# Toda a lógica legada do Databricks e PySpark foi removida pois
# o projeto agora foca no GCP com Polars.

@pytest.fixture
def project_root():
    """Retorna o caminho raiz do projeto."""
    return pathlib.Path(__file__).parent.parent
