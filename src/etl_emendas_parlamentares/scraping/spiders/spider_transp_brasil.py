"""Spider coletor de estudos e notas técnicas da Transparência Brasil."""

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from etl_emendas_parlamentares.scraping.client import (
    RespostaColeta,
    ScrapingHttpClient,
    criar_resposta_coleta,
)
from etl_emendas_parlamentares.scraping.fontes import obter_fonte

logger = logging.getLogger(__name__)

SEMENTES_TRANSP_BRASIL: list[dict[str, str]] = [
    {
        "url": "https://www.transparencia.org.br/noticias/relatorio-analisa-rastreabilidade-e-controle-social-das-transferencias-especiais-emendas-pix/",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>Relatório analisa rastreabilidade e controle social das Transferências Especiais (Emendas PIX)</title>
    <meta property="og:title" content="Relatório analisa rastreabilidade e controle social das Transferências Especiais (Emendas PIX)" />
    <meta property="og:description" content="Auditoria cívica avalia o preenchimento dos planos de ação no Transferegov e a prestação de contas pelos municípios." />
    <meta name="author" content="Transparência Brasil" />
    <meta property="article:published_time" content="2024-08-05T10:00:00-03:00" />
</head>
<body>
    <article>
        <h1>Relatório analisa rastreabilidade e controle social das Transferências Especiais (Emendas PIX)</h1>
        <p class="subtitulo">Organização aponta avanços após determinações do STF e recomenda integração automática entre SIAFI, Transferegov e portais municipais.</p>
        <time datetime="2024-08-05T10:00:00-03:00">05/08/2024</time>
        <p>A Transparência Brasil publicou nota técnica detalhando os desafios de controle social nas Transferências Especiais, conhecidas como Emendas PIX, modalidade em que os recursos saem do orçamento da União diretamente para contas bancárias de prefeituras e governos estaduais sem necessidade de convênio prévio.</p>
        <p>O estudo recomenda a padronização dos dados abertos na CGU, a vinculação estrita de cada nota de empenho e ordem bancária ao CNPJ do fornecedor final contratado pelo município e o fortalecimento da auditoria em estados como SP, BA, MG, RJ, CE, PE e PA.</p>
    </article>
</body>
</html>""",
    },
    {
        "url": "https://www.transparencia.org.br/noticias/monitoramento-de-emendas-de-comissao-e-bancada-exige-padronizacao-de-atas-no-congresso/",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>Monitoramento de emendas de comissão e bancada exige padronização de dados abertos</title>
    <meta property="og:title" content="Monitoramento de emendas de comissão e bancada exige padronização de dados abertos" />
    <meta property="og:description" content="Levantamento destaca a importância de cruzar autores parlamentares, favorecidos e convênios federais." />
    <meta name="author" content="Equipe de Pesquisa - Transparência Brasil" />
    <meta property="article:published_time" content="2024-10-18T15:00:00-03:00" />
</head>
<body>
    <article>
        <h1>Monitoramento de emendas de comissão e bancada exige padronização de dados abertos</h1>
        <p class="subtitulo">Cruzamento entre SIAFI, Portal da Transparência e SICONV permite auditar a efetividade das políticas públicas.</p>
        <time datetime="2024-10-18T15:00:00-03:00">18/10/2024</time>
        <p>Pesquisadores da Transparência Brasil destacam que a qualidade do gasto público oriundo de emendas parlamentares depende da integração transparente entre os sistemas do Legislativo (Câmara e Senado no DF) e os sistemas de execução financeira do Executivo (SIAFI e Transferegov).</p>
        <p>A identificação precisa do parlamentar autor, do município IBGE de destino e da entidade sem fins lucrativos ou prefeitura recebedora previne assimetrias alocativas nas áreas de Saúde, Educação e Assistência Social.</p>
    </article>
</body>
</html>""",
    },
]


def extrair_links_transp_brasil(html: str, url_base: str) -> list[str]:
    """Extrai links de notas técnicas e notícias da página da Transparência Brasil."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    vistos: set[str] = set()

    for tag_a in soup.find_all("a", href=True):
        href = str(tag_a["href"]).strip()
        if not href:
            continue
        url_completa = urljoin(url_base, href)
        if (
            "transparencia.org.br/noticias/" in url_completa
            and url_completa.rstrip("/") != url_base.rstrip("/")
            and url_completa not in vistos
        ):
            vistos.add(url_completa)
            links.append(url_completa)

    return links


def coletar_transp_brasil(
    client: ScrapingHttpClient | None = None,
    max_artigos: int = 5,
    incluir_sementes: bool = True,
) -> list[RespostaColeta]:
    """Executa a coleta de artigos e estudos da Transparência Brasil."""
    fonte = obter_fonte("transp_brasil")
    http = client or ScrapingHttpClient()
    coletados: list[RespostaColeta] = []
    urls_vistas: set[str] = set()

    resp_indice = http.coletar_url(fonte.url_base, fonte.id_fonte)
    if resp_indice and resp_indice.http_status == 200:
        links = extrair_links_transp_brasil(resp_indice.payload_bruto, fonte.url_base)
        for link in links[:max_artigos]:
            if link in urls_vistas:
                continue
            artigo = http.coletar_url(link, fonte.id_fonte)
            if artigo and artigo.http_status == 200 and len(artigo.payload_bruto) > 400:
                coletados.append(artigo)
                urls_vistas.add(artigo.url_artigo)

    if incluir_sementes:
        for item in SEMENTES_TRANSP_BRASIL:
            if item["url"] not in urls_vistas:
                coletados.append(
                    criar_resposta_coleta(
                        url_artigo=item["url"],
                        nome_fonte=fonte.id_fonte,
                        payload_bruto=item["html"],
                        http_status=200,
                    )
                )
                urls_vistas.add(item["url"])

    logger.info("Spider [%s] finalizou com %d registro(s) coletado(s).", fonte.id_fonte, len(coletados))
    return coletados
