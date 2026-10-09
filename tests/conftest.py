import pathlib

import pytest


@pytest.fixture
def project_root():
    """Retorna o caminho raiz do projeto."""
    return pathlib.Path(__file__).parent.parent
