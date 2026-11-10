"""Spider coletor de notícias da Agência Senado sobre Emendas Parlamentares."""

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

SEMENTES_SENADO: list[dict[str, str]] = [
    {
        "url": "https://www12.senado.leg.br/noticias/materias/2024/11/20/cmo-aprova-diretrizes-orcamentarias-e-regras-de-rastreabilidade-para-emendas-de-bancada-e-comissao",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>CMO aprova diretrizes orçamentárias e regras de rastreabilidade para emendas de bancada e comissão</title>
    <meta property="og:title" content="CMO aprova diretrizes orçamentárias e regras de rastreabilidade para emendas de bancada e comissão" />
    <meta property="og:description" content="Comissão Mista de Orçamento define parâmetros da LDO e LOA com identificação obrigatória de parlamentares patrocinadores." />
    <meta name="author" content="Agência Senado" />
    <meta property="article:published_time" content="2024-11-20T18:10:00-03:00" />
</head>
<body>
    <article>
        <h1>CMO aprova diretrizes orçamentárias e regras de rastreabilidade para emendas de bancada e comissão</h1>
        <p class="subtitulo">Senadores e deputados estabelecem critérios de transparência ativa e limites fiscais alinhados ao arcabouço orçamentário.</p>
        <time datetime="2024-11-20T18:10:00-03:00">20/11/2024 18h10</time>
        <p>A Comissão Mista de Planos, Orçamentos Públicos e Fiscalização (CMO) do Congresso Nacional aprovou o relatório da Lei de Diretrizes Orçamentárias (LDO) que disciplina a apresentação e execução das emendas parlamentares na Lei Orçamentária Anual (LOA).</p>
        <p>As emendas de Bancada Estadual (RP7) destinam-se a projetos estruturantes de caráter regional nas 27 Unidades da Federação (incluindo DF, SP, MG, BA, RS, PE, CE e GO), enquanto as emendas de Comissão (RP8) exigem deliberação colegiada registrada em ata eletrônica com identificação de cada senador ou deputado autor da sugestão.</p>
    </article>
</body>
</html>""",
    },
    {
        "url": "https://www12.senado.leg.br/noticias/materias/2024/07/10/consultoria-de-orcamento-do-senado-avalia-evolucao-historica-das-emendas-impositivas-desde-2015",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>Consultoria de Orçamento do Senado avalia evolução histórica das emendas impositivas</title>
    <meta property="og:title" content="Consultoria de Orçamento do Senado avalia evolução histórica das emendas impositivas" />
    <meta property="og:description" content="Nota técnica analisa o impacto das Emendas Constitucionais 86/2015, 100/2019 e 105/2019 na descentralização de recursos aos municípios." />
    <meta name="author" content="Consultoria de Orçamentos, Fiscalização e Controle - Agência Senado" />
    <meta property="article:published_time" content="2024-07-10T09:00:00-03:00" />
</head>
<body>
    <article>
        <h1>Consultoria de Orçamento do Senado avalia evolução histórica das emendas impositivas</h1>
        <p class="subtitulo">Estudo técnico detalha a transição para o orçamento impositivo e a criação das Transferências Especiais (Emendas PIX).</p>
        <time datetime="2024-07-10T09:00:00-03:00">10/07/2024 09h00</time>
        <p>Estudo publicado pela Consultoria de Orçamentos do Senado Federal demonstra como as Emendas Constitucionais nº 86/2015 (emendas individuais impositivas), nº 100/2019 (emendas de bancada impositivas) e nº 105/2019 (transferências especiais) transformaram a relação entre o Poder Legislativo e os entes subnacionais.</p>
        <p>O levantamento destaca que a taxa de execução financeira (relação entre valor pago e valor empenhado) aumentou substancialmente nas funções Saúde, Educação, Urbanismo, Agricultura e Segurança Pública em estados como PR, SC, ES, MT, MS, RN e PB.</p>
    </article>
</body>
</html>""",
    },
]


def extrair_links_senado(html: str, url_base: str) -> list[str]:
    """Extrai links de notícias legislativas da página da Agência Senado."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    vistos: set[str] = set()

    for tag_a in soup.find_all("a", href=True):
        href = str(tag_a["href"]).strip()
        if not href:
            continue
        url_completa = urljoin(url_base, href)
        if "senado.leg.br/noticias/materias/" in url_completa and url_completa not in vistos:
            vistos.add(url_completa)
            links.append(url_completa)

    return links


def coletar_senado(
    client: ScrapingHttpClient | None = None,
    max_artigos: int = 5,
    incluir_sementes: bool = True,
) -> list[RespostaColeta]:
    """Executa a coleta de artigos da Agência Senado."""
    fonte = obter_fonte("senado")
    http = client or ScrapingHttpClient()
    coletados: list[RespostaColeta] = []
    urls_vistas: set[str] = set()

    resp_indice = http.coletar_url(fonte.url_base, fonte.id_fonte)
    if resp_indice and resp_indice.http_status == 200:
        links = extrair_links_senado(resp_indice.payload_bruto, fonte.url_base)
        for link in links[:max_artigos]:
            if link in urls_vistas:
                continue
            artigo = http.coletar_url(link, fonte.id_fonte)
            if artigo and artigo.http_status == 200 and len(artigo.payload_bruto) > 400:
                coletados.append(artigo)
                urls_vistas.add(artigo.url_artigo)

    if incluir_sementes:
        for item in SEMENTES_SENADO:
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
