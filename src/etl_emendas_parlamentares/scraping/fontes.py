"""Mapeamento de fontes de dados e notícias para Web Scraping e consumo no Vertex AI.

Fontes identificadas para extração de contexto jornalístico, dados públicos e
visões complementares sobre emendas parlamentares.
"""

from dataclasses import dataclass

# ==============================================================================
# FONTES JORNALÍSTICAS, INSTITUCIONAIS E DASHBOARDS MAPEADOS
# ==============================================================================

# 1. Folha de S.Paulo - Cobertura jornalística investigativa, contexto político e fiscal
# https://www1.folha.uol.com.br/folha-topicos/emenda-parlamentar/

# 2. Agência Brasil (EBC) - Noticiário oficial, liberações pelo Executivo e atos federais
# https://agenciabrasil.ebc.com.br/tags/emendas-parlamentares-0

# 3. Agência Senado - Tramitação legislativa, discursos, PECs e debates no Congresso
# https://www12.senado.leg.br/noticias/destaques/emendas-parlamentares/pag/1

# 4. Central das Emendas (FLAG: ##DASHBOARD) - Observatório com indicadores e dados analíticos
# https://www.centraldasemendas.info/dados

# 5. Portal da Transparência (CGU) - Regras oficiais, normas e orientações técnicas de repasses
# https://portaldatransparencia.gov.br/emendas

# 6. Transparência Brasil - Controle social, auditorias cívicas e investigações independentes
# https://www.transparencia.org.br/noticias/


@dataclass(frozen=True)
class FonteScraping:
    """Metadados e configuração técnica de cada fonte oficial de scraping."""

    id_fonte: str
    nome_amigavel: str
    url_base: str
    tabela_raw: str
    tipo_conteudo: str
    foco_analitico: str
    tags_padrao: tuple[str, ...]


FONTES_SCRAPING: dict[str, FonteScraping] = {
    "folha": FonteScraping(
        id_fonte="folha",
        nome_amigavel="Folha de S.Paulo",
        url_base="https://www1.folha.uol.com.br/folha-topicos/emenda-parlamentar/",
        tabela_raw="raw_scraping_folha",
        tipo_conteudo="Jornalismo Investigativo",
        foco_analitico="Decisões do STF, Emendas de Relator (RP9), apurações de desvios e impacto fiscal",
        tags_padrao=("STF", "Fiscalização", "Orçamento", "RP9"),
    ),
    "ebc": FonteScraping(
        id_fonte="ebc",
        nome_amigavel="Agência Brasil (EBC)",
        url_base="https://agenciabrasil.ebc.com.br/tags/emendas-parlamentares-0",
        tabela_raw="raw_scraping_ebc",
        tipo_conteudo="Noticiário Oficial",
        foco_analitico="Decretos federais, cronogramas de pagamento do Executivo e liberações orçamentárias",
        tags_padrao=("Executivo Federal", "Execução Orçamentária", "SIAFI"),
    ),
    "senado": FonteScraping(
        id_fonte="senado",
        nome_amigavel="Agência Senado",
        url_base="https://www12.senado.leg.br/noticias/destaques/emendas-parlamentares/pag/1",
        tabela_raw="raw_scraping_senado",
        tipo_conteudo="Noticiário Legislativo",
        foco_analitico="Tramitação de PECs, debates no Congresso, discursos e prestação de contas",
        tags_padrao=("Congresso Nacional", "LDO", "LOA", "Processo Legislativo"),
    ),
    "transp_brasil": FonteScraping(
        id_fonte="transp_brasil",
        nome_amigavel="Transparência Brasil",
        url_base="https://www.transparencia.org.br/noticias/",
        tabela_raw="raw_scraping_transp_brasil",
        tipo_conteudo="Auditoria Cívica",
        foco_analitico="Estudos de rastreabilidade, notas técnicas sobre Emendas PIX e controle social",
        tags_padrao=("Emendas PIX", "Rastreabilidade", "Controle Social", "Transparência"),
    ),
    "cgu": FonteScraping(
        id_fonte="cgu",
        nome_amigavel="Portal da Transparência (CGU)",
        url_base="https://portaldatransparencia.gov.br/emendas",
        tabela_raw="raw_scraping_cgu",
        tipo_conteudo="Normas & Regras Técnicas",
        foco_analitico="Manuais operacionais, portarias interministeriais e diretrizes de prestação de contas",
        tags_padrao=("CGU", "Normas Técnicas", "Prestação de Contas", "SIAFI"),
    ),
    "central_emendas": FonteScraping(
        id_fonte="central_emendas",
        nome_amigavel="Central das Emendas",
        url_base="https://www.centraldasemendas.info/dados",
        tabela_raw="raw_scraping_central_emendas",
        tipo_conteudo="Observatório Cívico",
        foco_analitico="Painéis analíticos e relatórios de monitoramento legislativo",
        tags_padrao=("Observatório Cívico", "Monitoramento", "Dados Abertos"),
    ),
}


def obter_fonte(id_fonte: str) -> FonteScraping:
    """Retorna a definição de uma fonte pelo seu identificador."""
    chave = id_fonte.strip().lower()
    if chave not in FONTES_SCRAPING:
        msg = f"Fonte de scraping '{id_fonte}' não cadastrada. Fontes válidas: {list(FONTES_SCRAPING.keys())}"
        raise KeyError(msg)
    return FONTES_SCRAPING[chave]


def listar_fontes() -> list[FonteScraping]:
    """Retorna a lista ordenada de todas as fontes oficiais mapeadas."""
    return list(FONTES_SCRAPING.values())
