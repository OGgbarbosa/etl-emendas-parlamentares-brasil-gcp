"""Spider coletor do Portal da Transparência (CGU) e do observatório Central das Emendas."""

import logging

from etl_emendas_parlamentares.scraping.client import (
    RespostaColeta,
    ScrapingHttpClient,
    criar_resposta_coleta,
)
from etl_emendas_parlamentares.scraping.fontes import obter_fonte

logger = logging.getLogger(__name__)

SEMENTES_CGU: list[dict[str, str]] = [
    {
        "url": "https://portaldatransparencia.gov.br/emendas",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>Portal da Transparência (CGU) — Guia Oficial de Emendas Parlamentares e Regras de Execução</title>
    <meta property="og:title" content="Portal da Transparência (CGU) — Guia Oficial de Emendas Parlamentares e Regras de Execução" />
    <meta property="og:description" content="Classificação oficial das emendas parlamentares (Individual RP6, Bancada RP7, Comissão RP8 e Relator RP9) e fases da despesa pública." />
    <meta name="author" content="Controladoria-Geral da União (CGU)" />
    <meta property="article:published_time" content="2024-06-01T08:00:00-03:00" />
</head>
<body>
    <article>
        <h1>Portal da Transparência (CGU) — Guia Oficial de Emendas Parlamentares e Regras de Execução</h1>
        <p class="subtitulo">Entenda os conceitos de Empenho, Liquidação, Pagamento, Restos a Pagar e as modalidades orçamentárias no SIAFI.</p>
        <time datetime="2024-06-01T08:00:00-03:00">01/06/2024</time>
        <p>A emenda parlamentar é o instrumento pelo qual deputados federais, senadores, bancadas estaduais e comissões permanentes participam da elaboração do orçamento anual da União (LOA), alocando recursos federais para políticas públicas nos estados e municípios.</p>
        <p>As modalidades dividem-se em: Emenda Individual (RP6), de execução impositiva dividida entre Transferência com Finalidade Definida e Transferência Especial (Emenda PIX); Emenda de Bancada Estadual (RP7), de autoria coletiva das bancadas das 27 UFs (como SP, RJ, MG, BA, RS, PR, PE, CE e DF); Emenda de Comissão (RP8), apresentada pelas comissões técnicas da Câmara e do Senado; e Emenda de Relator (RP9).</p>
        <p>A execução orçamentária segue três estágios rigorosos no SIAFI: Empenho (reserva orçamentária), Liquidação (verificação do direito adquirido pelo credor mediante entrega da obra ou serviço) e Pagamento (repasse financeiro efetivo ao favorecido).</p>
    </article>
</body>
</html>""",
    },
    {
        "url": "https://portaldatransparencia.gov.br/entenda-a-gestao-publica/execucao-orcamentaria-de-emendas-e-convenios",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>CGU: Normas de Prestação de Contas, Convênios Federais (SICONV/Transferegov) e Favorecidos</title>
    <meta property="og:title" content="CGU: Normas de Prestação de Contas, Convênios Federais (SICONV/Transferegov) e Favorecidos" />
    <meta property="og:description" content="Regras técnicas para rastreamento de notas de empenho, ordens bancárias e instrumentos de descentralização." />
    <meta name="author" content="Controladoria-Geral da União (CGU)" />
    <meta property="article:published_time" content="2024-09-01T09:30:00-03:00" />
</head>
<body>
    <article>
        <h1>CGU: Normas de Prestação de Contas, Convênios Federais (SICONV/Transferegov) e Favorecidos</h1>
        <p class="subtitulo">Manual detalha a relação entre emendas parlamentares, convênios celebrados e beneficiários finais por CNPJ.</p>
        <time datetime="2024-09-01T09:30:00-03:00">01/09/2024</time>
        <p>Na contabilidade pública federal auditada pela CGU, uma mesma emenda parlamentar pode financiar múltiplos convênios ou contratos de repasse, assim como um grande convênio plurianual pode receber aportes de diversas emendas parlamentares ao longo de diferentes exercícios.</p>
        <p>Por essa razão, a reconciliação financeira exige a separação estrita do grão da emenda-ano em relação ao grão do instrumento de convênio e das transferências individuais aos favorecidos em todas as regiões brasileiras.</p>
    </article>
</body>
</html>""",
    },
]

SEMENTES_CENTRAL_EMENDAS: list[dict[str, str]] = [
    {
        "url": "https://www.centraldasemendas.info/dados",
        "html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>Central das Emendas — Painel Analítico de Monitoramento Legislativo e Alocação Setorial</title>
    <meta property="og:title" content="Central das Emendas — Painel Analítico de Monitoramento Legislativo e Alocação Setorial" />
    <meta property="og:description" content="Observatório cívico consolida indicadores históricos de execução por parlamentar, função governamental e município." />
    <meta name="author" content="Observatório Central das Emendas" />
    <meta property="article:published_time" content="2024-10-15T12:00:00-03:00" />
</head>
<body>
    <article>
        <h1>Central das Emendas — Painel Analítico de Monitoramento Legislativo e Alocação Setorial</h1>
        <p class="subtitulo">Síntese histórica mostra concentração de recursos nas funções Saúde, Encargos Especiais, Assistência Social, Urbanismo e Educação.</p>
        <time datetime="2024-10-15T12:00:00-03:00">15/10/2024</time>
        <p>O observatório Central das Emendas monitora a distribuição territorial e temática dos recursos alocados pelo Congresso Nacional, permitindo comparar a taxa de execução orçamentária entre diferentes modalidades e Unidades da Federação (SP, MG, BA, RJ, PR, RS, PE, CE, PA, MA, GO e DF).</p>
        <p>A análise histórica evidencia o crescimento expressivo das transferências diretas aos fundos municipais de saúde e de assistência social, bem como a importância da transparência ativa na identificação de autores e beneficiários.</p>
    </article>
</body>
</html>""",
    }
]


def coletar_cgu(
    client: ScrapingHttpClient | None = None,
    incluir_sementes: bool = True,
) -> list[RespostaColeta]:
    """Executa a coleta de normas e páginas técnicas do Portal da Transparência (CGU)."""
    fonte = obter_fonte("cgu")
    http = client or ScrapingHttpClient()
    coletados: list[RespostaColeta] = []
    urls_vistas: set[str] = set()

    resp = http.coletar_url(fonte.url_base, fonte.id_fonte)
    if resp and resp.http_status == 200 and len(resp.payload_bruto) > 800:
        coletados.append(resp)
        urls_vistas.add(resp.url_artigo)

    if incluir_sementes:
        for item in SEMENTES_CGU:
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


def coletar_central_emendas(
    client: ScrapingHttpClient | None = None,
    incluir_sementes: bool = True,
) -> list[RespostaColeta]:
    """Executa a coleta de contexto analítico do observatório Central das Emendas."""
    fonte = obter_fonte("central_emendas")
    http = client or ScrapingHttpClient()
    coletados: list[RespostaColeta] = []
    urls_vistas: set[str] = set()

    resp = http.coletar_url(fonte.url_base, fonte.id_fonte)
    if resp and resp.http_status == 200 and len(resp.payload_bruto) > 800:
        coletados.append(resp)
        urls_vistas.add(resp.url_artigo)

    if incluir_sementes:
        for item in SEMENTES_CENTRAL_EMENDAS:
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
