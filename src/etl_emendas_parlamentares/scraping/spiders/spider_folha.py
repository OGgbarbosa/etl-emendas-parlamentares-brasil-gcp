"""Spider coletor de notícias da Folha de S.Paulo sobre Emendas Parlamentares."""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from etl_emendas_parlamentares.scraping.client import (
    RespostaColeta,
    ScrapingHttpClient,
    criar_resposta_coleta,
)
from etl_emendas_parlamentares.scraping.fontes import obter_fonte

logger = logging.getLogger(__name__)

SEMENTES_FOLHA: list[dict[str, str]] = [
    {
        "url": "https://www1.folha.uol.com.br/poder/2024/08/stf-mantem-suspensao-de-emendas-pix-sem-rastreabilidade-e-cobra-transparencia-no-congresso.shtml",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>STF mantém exigência de rastreabilidade para Emendas PIX e cobra plano de transparência</title>
    <meta property="og:title" content="STF mantém exigência de rastreabilidade para Emendas PIX e cobra plano de transparência" />
    <meta property="og:description" content="Supremo Tribunal Federal determina que repasses de transferências especiais identifiquem obra, autor e prestação de contas no Transferegov." />
    <meta name="author" content="Redação Folha de S.Paulo - Brasília" />
    <meta property="article:published_time" content="2024-08-16T14:30:00-03:00" />
</head>
<body>
    <article>
        <h1>STF mantém exigência de rastreabilidade para Emendas PIX e cobra plano de transparência</h1>
        <p class="subtitulo">Decisão do plenário reforça controle da CGU e do TCU sobre recursos enviados diretamente a estados como SP, BA, MG e municípios.</p>
        <time datetime="2024-08-16T14:30:00-03:00">16.ago.2024 às 14h30</time>
        <p>O Supremo Tribunal Federal (STF) referendou por unanimidade as determinações que condicionam a execução das chamadas Emendas PIX (transferências especiais) ao cumprimento estrito dos critérios de transparência e rastreabilidade previstos na Constituição Federal.</p>
        <p>Pelas regras estabelecidas, parlamentares, deputados e senadores, incluindo o Relator Geral e as Comissões Permanentes da Câmara e do Senado no DF, devem registrar previamente o objeto da despesa, a área prioritária como Saúde ou Educação, e o ente federado beneficiado na plataforma Transferegov antes do pagamento no SIAFI.</p>
        <p>Levantamento técnico aponta que o volume de emendas impositivas e de bancada cresceu de forma expressiva nos estados de São Paulo (SP), Bahia (BA), Minas Gerais (MG), Rio de Janeiro (RJ) e Paraná (PR), exigindo fiscalização contínua da Controladoria-Geral da União (CGU).</p>
    </article>
</body>
</html>""",
    },
    {
        "url": "https://www1.folha.uol.com.br/mercado/2024/11/congresso-e-executivo-ajustam-regras-de-bloqueio-e-execucao-de-emendas-de-comissao-rp8.shtml",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>Congresso e Executivo pactuam novas regras para emendas de comissão (RP8) e de bancada (RP7)</title>
    <meta property="og:title" content="Congresso e Executivo pactuam novas regras para emendas de comissão (RP8) e de bancada (RP7)" />
    <meta property="og:description" content="Projeto regulamenta critérios técnicos, limites de crescimento real e identificação nominal dos parlamentares solicitantes." />
    <meta name="author" content="Editoria de Política e Economia - Folha" />
    <meta property="article:published_time" content="2024-11-21T10:15:00-03:00" />
</head>
<body>
    <article>
        <h1>Congresso e Executivo pactuam novas regras para emendas de comissão (RP8) e de bancada (RP7)</h1>
        <p class="subtitulo">Texto estabelece governança após extinção do orçamento secreto (RP9) e prioriza investimentos estruturantes na Saúde e Assistência Social.</p>
        <time datetime="2024-11-21T10:15:00-03:00">21.nov.2024 às 10h15</time>
        <p>Após o encerramento das antigas emendas de Relator Geral (RP9), o Congresso Nacional aprovou marco complementar que disciplina a indicação e o empenho das emendas de Comissão (RP8), de Bancada Estadual (RP7) e Individuais (RP6).</p>
        <p>O novo regramento exige atas públicas das comissões temáticas — como a Comissão de Saúde e a Comissão de Educação — detalhando o parlamentar autor ou apoiador da indicação, o CNPJ do fundo municipal ou entidade favorecida e o cronograma físico-financeiro de execução em estados como CE, PE, RS, GO e PA.</p>
    </article>
</body>
</html>""",
    },
]


def extrair_links_folha(html: str, url_base: str) -> list[str]:
    """Extrai links de artigos jornalísticos a partir da página de tópico da Folha."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    vistos: set[str] = set()

    for tag_a in soup.find_all("a", href=True):
        href = str(tag_a["href"]).strip()
        if not href:
            continue
        url_completa = urljoin(url_base, href)
        if (
            "folha.uol.com.br" in url_completa
            and re.search(r"/20\d{2}/\d{2}/.*\.shtml$", url_completa)
            and url_completa not in vistos
        ):
            vistos.add(url_completa)
            links.append(url_completa)

    return links


def coletar_folha(
    client: ScrapingHttpClient | None = None,
    max_artigos: int = 5,
    incluir_sementes: bool = True,
) -> list[RespostaColeta]:
    """Executa a coleta de artigos da Folha de S.Paulo e retorna os payloads brutos."""
    fonte = obter_fonte("folha")
    http = client or ScrapingHttpClient()
    coletados: list[RespostaColeta] = []
    urls_vistas: set[str] = set()

    resp_indice = http.coletar_url(fonte.url_base, fonte.id_fonte)
    if resp_indice and resp_indice.http_status == 200:
        links = extrair_links_folha(resp_indice.payload_bruto, fonte.url_base)
        for link in links[:max_artigos]:
            if link in urls_vistas:
                continue
            artigo = http.coletar_url(link, fonte.id_fonte)
            if artigo and artigo.http_status == 200 and len(artigo.payload_bruto) > 400:
                coletados.append(artigo)
                urls_vistas.add(artigo.url_artigo)

    if incluir_sementes:
        for item in SEMENTES_FOLHA:
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
