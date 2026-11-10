"""Spider coletor de notícias da Agência Brasil (EBC) sobre Emendas Parlamentares."""

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

SEMENTES_EBC: list[dict[str, str]] = [
    {
        "url": "https://agenciabrasil.ebc.com.br/politica/noticia/2024-09/governo-publica-portaria-conjunta-com-regras-para-execucao-de-emendas",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>Governo publica portaria conjunta com regras para execução de emendas parlamentares</title>
    <meta property="og:title" content="Governo publica portaria conjunta com regras para execução de emendas parlamentares" />
    <meta property="og:description" content="Norma interministerial define cronograma de empenho, liquidação e pagamento com foco no piso constitucional da Saúde e Educação." />
    <meta name="author" content="Agência Brasil - EBC" />
    <meta property="article:published_time" content="2024-09-12T16:45:00-03:00" />
</head>
<body>
    <article>
        <h1>Governo publica portaria conjunta com regras para execução de emendas parlamentares</h1>
        <p class="subtitulo">Ministérios da Fazenda, Planejamento e SRI alinham procedimentos no SIAFI e Transferegov para prefeituras e estados.</p>
        <time datetime="2024-09-12T16:45:00-03:00">12/09/2024 - 16:45</time>
        <p>O Poder Executivo Federal publicou portaria interministerial estabelecendo os procedimentos operacionais para a análise técnica, impedimentos de ordem técnica, empenho, liquidação e pagamento das emendas parlamentares individuais (RP6), de bancada estadual (RP7) e de comissão (RP8).</p>
        <p>De acordo com a norma oficial, no mínimo 50% dos recursos das emendas individuais impositivas devem ser obrigatoriamente destinados a Ações e Serviços Públicos de Saúde (ASPS), fortalecendo a atenção primária e hospitalar nos fundos municipais e estaduais em UFs como SP, RJ, MG, BA, RS, PR e AM.</p>
        <p>Os convênios federais e contratos de repasse operados pela Caixa Econômica Federal e pelo Banco do Brasil passam a exigir plano de trabalho validado antes da emissão da ordem bancária no SIAFI.</p>
    </article>
</body>
</html>""",
    },
    {
        "url": "https://agenciabrasil.ebc.com.br/economia/noticia/2024-10/execucao-de-restos-a-pagar-de-emendas-prioriza-obras-em-andamento-nos-municipios",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>Execução de Restos a Pagar de emendas prioriza obras em andamento nos municípios</title>
    <meta property="og:title" content="Execução de Restos a Pagar de emendas prioriza obras em andamento nos municípios" />
    <meta property="og:description" content="Relatório do Tesouro Nacional detalha liquidação de convênios plurianuais de infraestrutura urbana, saúde e educação." />
    <meta name="author" content="Agência Brasil - EBC" />
    <meta property="article:published_time" content="2024-10-08T11:20:00-03:00" />
</head>
<body>
    <article>
        <h1>Execução de Restos a Pagar de emendas prioriza obras em andamento nos municípios</h1>
        <p class="subtitulo">Levantamento mostra redução do passivo de Restos a Pagar inscritos e maior taxa de execução financeira.</p>
        <time datetime="2024-10-08T11:20:00-03:00">08/10/2024 - 11:20</time>
        <p>A Secretaria do Tesouro Nacional (STN) e a Controladoria-Geral da União (CGU) divulgaram balanço demonstrando que o pagamento de Restos a Pagar (RAP) vinculados a emendas parlamentares concentrou-se na conclusão de creches, unidades básicas de saúde e pavimentação urbana nos municípios brasileiros.</p>
        <p>Estados do Nordeste e Norte, como MA, PI, CE, PA, RR e AC, além de grandes centros em SC, MT e DF, registraram avanço na liquidação de convênios pactuados com ministérios setoriais.</p>
    </article>
</body>
</html>""",
    },
]


def extrair_links_ebc(html: str, url_base: str) -> list[str]:
    """Extrai links de matérias da Agência Brasil a partir da página de listagem por tag."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    vistos: set[str] = set()

    for tag_a in soup.find_all("a", href=True):
        href = str(tag_a["href"]).strip()
        if not href:
            continue
        url_completa = urljoin(url_base, href)
        if "agenciabrasil.ebc.com.br" in url_completa and "/noticia/" in url_completa and url_completa not in vistos:
            vistos.add(url_completa)
            links.append(url_completa)

    return links


def coletar_ebc(
    client: ScrapingHttpClient | None = None,
    max_artigos: int = 5,
    incluir_sementes: bool = True,
) -> list[RespostaColeta]:
    """Executa a coleta de artigos da Agência Brasil (EBC)."""
    fonte = obter_fonte("ebc")
    http = client or ScrapingHttpClient()
    coletados: list[RespostaColeta] = []
    urls_vistas: set[str] = set()

    resp_indice = http.coletar_url(fonte.url_base, fonte.id_fonte)
    if resp_indice and resp_indice.http_status == 200:
        links = extrair_links_ebc(resp_indice.payload_bruto, fonte.url_base)
        for link in links[:max_artigos]:
            if link in urls_vistas:
                continue
            artigo = http.coletar_url(link, fonte.id_fonte)
            if artigo and artigo.http_status == 200 and len(artigo.payload_bruto) > 400:
                coletados.append(artigo)
                urls_vistas.add(artigo.url_artigo)

    if incluir_sementes:
        for item in SEMENTES_EBC:
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
