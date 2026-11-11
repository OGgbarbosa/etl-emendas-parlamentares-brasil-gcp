"""Testes unitários para a esteira de Web Scraping e Contexto Qualitativo (Camada Silver)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from etl_emendas_parlamentares.scraping.carga_silver_raw import (
    carregar_lote_raw_fonte,
    filtrar_respostas_ineditas,
    gerar_ddl_tabela_raw,
    salvar_parquet_raw_local,
)
from etl_emendas_parlamentares.scraping.client import (
    ScrapingHttpClient,
    calcular_hash_conteudo,
    criar_resposta_coleta,
)
from etl_emendas_parlamentares.scraping.fontes import (
    FONTES_SCRAPING,
    listar_fontes,
    obter_fonte,
)
from etl_emendas_parlamentares.scraping.parser import (
    extrair_artigo_limpo,
    extrair_entidades_texto,
    gerar_id_artigo,
)
from etl_emendas_parlamentares.scraping.pipeline_scraping import executar_pipeline_scraping
from etl_emendas_parlamentares.scraping.processar_contexto import (
    gerar_ddl_fato_noticias,
    materializar_fato_noticias_contexto,
    transformar_respostas_em_artigos,
)
from etl_emendas_parlamentares.scraping.spiders import (
    coletar_central_emendas,
    coletar_cgu,
    coletar_ebc,
    coletar_folha,
    coletar_senado,
    coletar_todas_as_fontes,
    coletar_transp_brasil,
)
from etl_emendas_parlamentares.scraping.spiders.spider_ebc import extrair_links_ebc
from etl_emendas_parlamentares.scraping.spiders.spider_folha import extrair_links_folha
from etl_emendas_parlamentares.scraping.spiders.spider_senado import extrair_links_senado
from etl_emendas_parlamentares.scraping.spiders.spider_transp_brasil import (
    extrair_links_transp_brasil,
)


def test_catalogo_fontes_completo() -> None:
    """Verifica se todas as 6 fontes oficiais estão mapeadas com suas tabelas raw_scraping_*."""
    fontes = listar_fontes()
    assert len(fontes) == 6
    chaves_esperadas = {"folha", "ebc", "senado", "transp_brasil", "cgu", "central_emendas"}
    assert set(FONTES_SCRAPING.keys()) == chaves_esperadas

    folha = obter_fonte("folha")
    assert folha.nome_amigavel == "Folha de S.Paulo"
    assert folha.tabela_raw == "raw_scraping_folha"

    with pytest.raises(KeyError):
        obter_fonte("fonte_inexistente")


def test_client_hash_e_headers_eticos() -> None:
    """Valida determinismo do hash SHA-256 e cabeçalhos éticos do cliente HTTP."""
    h1 = calcular_hash_conteudo("https://exemplo.gov.br/1", "<html>abc</html>")
    h2 = calcular_hash_conteudo("https://exemplo.gov.br/1", "<html>abc</html>")
    h3 = calcular_hash_conteudo("https://exemplo.gov.br/1", "<html>modificado</html>")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64

    client = ScrapingHttpClient(rate_limit_seconds=0.0)
    headers = client.obter_headers()
    assert "EmendasParlamentaresBot" in headers["User-Agent"]
    assert "pt-BR" in headers["Accept-Language"]


def test_client_coletar_url_mock() -> None:
    """Testa a coleta HTTP simulando resposta 200 com httpx."""
    client = ScrapingHttpClient(rate_limit_seconds=0.0)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><h1>Título</h1><p>Conteúdo de teste sobre emendas.</p></body></html>"
    mock_resp.url = "https://agenciabrasil.ebc.com.br/politica/noticia/2024-09/teste"

    with patch.object(client, "_executar_get", return_value=mock_resp):
        resultado = client.coletar_url("https://agenciabrasil.ebc.com.br/politica/noticia/2024-09/teste", "ebc")

    assert resultado is not None
    assert resultado.http_status == 200
    assert resultado.nome_fonte == "ebc"
    assert len(resultado.hash_conteudo) == 64


def test_parser_higienizacao_e_ner() -> None:
    """Verifica remoção de scripts/styles, extração de metadados, UFs, parlamentares e tags."""
    html_mock = """<!DOCTYPE html>
    <html>
    <head>
        <title>Título Fallback</title>
        <meta property="og:title" content="STF analisa rastreabilidade de Emendas PIX em São Paulo e Bahia" />
        <meta property="og:description" content="Relatório da CGU audita repasses via SIAFI e Transferegov." />
        <meta name="author" content="Repórter Oficial" />
        <meta property="article:published_time" content="2024-08-20T12:00:00-03:00" />
        <script>console.log("script malicioso que deve sumir");</script>
        <style>.oculto { display: none; }</style>
    </head>
    <body>
        <article>
            <h1>STF analisa rastreabilidade de Emendas PIX em São Paulo e Bahia</h1>
            <p>O Deputado João Silva e o Senador Carlos Souza debateram com o Relator Geral na Comissão de Saúde sobre os repasses para SP, BA e Minas Gerais.</p>
            <p>Os convênios de Saúde e Educação exigem prestação de contas rigorosa no SIAFI e controle da CGU.</p>
        </article>
    </body>
    </html>"""

    artigo = extrair_artigo_limpo(
        html_bruto=html_mock,
        url_artigo="https://www1.folha.uol.com.br/poder/2024/08/teste.shtml",
        id_fonte="folha",
    )

    assert artigo is not None
    assert artigo.nome_fonte == "Folha de S.Paulo"
    assert artigo.titulo == "STF analisa rastreabilidade de Emendas PIX em São Paulo e Bahia"
    assert artigo.subtitulo == "Relatório da CGU audita repasses via SIAFI e Transferegov."
    assert artigo.autor == "Repórter Oficial"
    assert str(artigo.data_publicacao) == "2024-08-20"
    assert "script malicioso" not in artigo.conteudo_texto
    assert artigo.qtd_palavras > 15
    assert set(artigo.ufs_mencionadas) >= {"SP", "BA", "MG"}
    assert "Relator Geral" in artigo.parlamentares_mencionados
    assert "Comissão de Saúde" in artigo.parlamentares_mencionados
    assert "Emendas PIX" in artigo.tags
    assert "STF" in artigo.tags
    assert "CGU" in artigo.tags
    assert len(artigo.id_artigo) == 64
    assert artigo.id_artigo == gerar_id_artigo("https://www1.folha.uol.com.br/poder/2024/08/teste.shtml")


def test_extracao_links_spiders() -> None:
    """Valida os seletores de extração de links para Folha, EBC, Senado e Transparência Brasil."""
    html_folha = '<a href="https://www1.folha.uol.com.br/poder/2024/08/materia.shtml">Link</a>'
    assert len(extrair_links_folha(html_folha, "https://www1.folha.uol.com.br")) == 1

    html_ebc = '<a href="/politica/noticia/2024-09/decreto-emendas">Link</a>'
    assert len(extrair_links_ebc(html_ebc, "https://agenciabrasil.ebc.com.br")) == 1

    html_senado = '<a href="/noticias/materias/2024/11/20/votacao-ldo">Link</a>'
    assert len(extrair_links_senado(html_senado, "https://www12.senado.leg.br")) == 1

    html_tb = '<a href="https://www.transparencia.org.br/noticias/estudo-pix/">Link</a>'
    assert len(extrair_links_transp_brasil(html_tb, "https://www.transparencia.org.br/noticias/")) == 1


def test_spiders_com_contingencia_sementes() -> None:
    """Verifica se todos os spiders retornam artigos íntegros mesmo quando a rede está indisponível."""
    client_offline = MagicMock(spec=ScrapingHttpClient)
    client_offline.coletar_url.return_value = None

    assert len(coletar_folha(client=client_offline, incluir_sementes=True)) >= 2
    assert len(coletar_ebc(client=client_offline, incluir_sementes=True)) >= 2
    assert len(coletar_senado(client=client_offline, incluir_sementes=True)) >= 2
    assert len(coletar_transp_brasil(client=client_offline, incluir_sementes=True)) >= 2
    assert len(coletar_cgu(client=client_offline, incluir_sementes=True)) >= 2
    assert len(coletar_central_emendas(client=client_offline, incluir_sementes=True)) >= 1

    mapa = coletar_todas_as_fontes(client=client_offline, incluir_sementes=True)
    assert len(mapa) == 6
    assert sum(len(v) for v in mapa.values()) >= 11


def test_idempotencia_e_carga_silver_raw(tmp_path: Path) -> None:
    """Testa filtro de idempotência por hash_conteudo e persistência Parquet/BigQuery."""
    r1 = criar_resposta_coleta("https://exemplo.com/a", "folha", "<html>A</html>")
    r2 = criar_resposta_coleta("https://exemplo.com/b", "folha", "<html>B</html>")

    ineditas = filtrar_respostas_ineditas([r1, r2], hashes_existentes={r1.hash_conteudo})
    assert len(ineditas) == 1
    assert ineditas[0].url_artigo == "https://exemplo.com/b"

    ddl_raw = gerar_ddl_tabela_raw("meu-projeto", "2_silver", "raw_scraping_folha")
    assert "CLUSTER BY dh_coleta, url_artigo" in ddl_raw
    assert "hash_conteudo STRING NOT NULL" in ddl_raw

    caminho_pq = salvar_parquet_raw_local("folha", [r1, r2], diretorio_local=tmp_path)
    assert caminho_pq is not None and caminho_pq.exists()
    df_lido = pd.read_parquet(caminho_pq)
    assert len(df_lido) == 2

    mock_bq = MagicMock()
    mock_bq.project = "meu-projeto"
    mock_bq.query.return_value.to_dataframe.return_value = pd.DataFrame({"hash_conteudo": [r1.hash_conteudo]})

    inseridos = carregar_lote_raw_fonte(
        id_fonte="folha",
        respostas=[r1, r2],
        client=mock_bq,
        diretorio_local=tmp_path,
    )
    assert inseridos == 1
    mock_bq.load_table_from_dataframe.assert_called_once()


def test_processar_contexto_e_pipeline_completo(tmp_path: Path) -> None:
    """Valida a transformação de bruto para fato_noticias_contexto com as 15 colunas exigidas."""
    ddl_fato = gerar_ddl_fato_noticias("meu-projeto", "2_silver", "fato_noticias_contexto")
    assert "CLUSTER BY data_publicacao, nome_fonte" in ddl_fato
    assert "parlamentares_mencionados ARRAY<STRING>" in ddl_fato
    assert "ufs_mencionadas ARRAY<STRING>" in ddl_fato

    client_offline = MagicMock(spec=ScrapingHttpClient)
    client_offline.coletar_url.return_value = None
    respostas_folha = coletar_folha(client=client_offline, incluir_sementes=True)

    artigos = transformar_respostas_em_artigos(respostas_folha)
    assert len(artigos) >= 2

    mock_bq = MagicMock()
    mock_bq.project = "meu-projeto"

    df_fato = materializar_fato_noticias_contexto(
        respostas_em_memoria=respostas_folha,
        client=mock_bq,
        diretorio_silver_local=tmp_path / "silver",
        diretorio_scraping_local=tmp_path / "scraping",
    )

    colunas_esperadas = {
        "id_artigo",
        "nome_fonte",
        "url_artigo",
        "titulo",
        "subtitulo",
        "autor",
        "data_publicacao",
        "dh_publicacao",
        "conteudo_texto",
        "lead_resumo",
        "tags",
        "parlamentares_mencionados",
        "ufs_mencionadas",
        "qtd_palavras",
        "dh_processamento",
    }
    assert set(df_fato.columns) == colunas_esperadas
    assert len(df_fato) >= 2

    # Execução do orquestrador com mocks
    mock_bq.query.return_value.to_dataframe.return_value = pd.DataFrame()
    with (
        patch("etl_emendas_parlamentares.scraping.carga_silver_raw.DIRETORIO_SCRAPING_LOCAL", tmp_path / "scraping"),
        patch("etl_emendas_parlamentares.scraping.processar_contexto.DIRETORIO_SILVER_LOCAL", tmp_path / "silver"),
        patch("etl_emendas_parlamentares.scraping.processar_contexto.DIRETORIO_SCRAPING_LOCAL", tmp_path / "scraping"),
    ):
        df_pipeline = executar_pipeline_scraping(
            client_http=client_offline,
            client_bq=mock_bq,
            incluir_sementes=True,
        )
    assert len(df_pipeline) >= 11
    assert set(df_pipeline["nome_fonte"].unique()) == {
        "Folha de S.Paulo",
        "Agência Brasil (EBC)",
        "Agência Senado",
        "Transparência Brasil",
        "Portal da Transparência (CGU)",
        "Central das Emendas",
    }


def test_extrair_entidades_isolado() -> None:
    """Testa isoladamente o NER heurístico de UFs, parlamentares e tags."""
    tags, parls, ufs = extrair_entidades_texto(
        "O Senador Marcos Pontes e a Deputada Tabata Amaral analisaram emendas PIX no estado do Ceará e em RR.",
        tags_iniciais=("Auditoria",),
    )
    assert "CE" in ufs
    assert "RR" in ufs
    assert "Emendas PIX" in tags
    assert "Auditoria" in tags
    assert any("Marcos Pontes" in p for p in parls)
    assert any("Tabata Amaral" in p for p in parls)
