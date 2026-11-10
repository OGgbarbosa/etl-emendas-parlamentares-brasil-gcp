"""Parser HTML, higienização com Trafilatura/BeautifulSoup e NER heurístico."""

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

import trafilatura
from bs4 import BeautifulSoup

from etl_emendas_parlamentares.scraping.fontes import FONTES_SCRAPING

MAPA_ESTADOS_UF: dict[str, str] = {
    "acre": "AC",
    "alagoas": "AL",
    "amapá": "AP",
    "amapa": "AP",
    "amazonas": "AM",
    "bahia": "BA",
    "ceará": "CE",
    "ceara": "CE",
    "distrito federal": "DF",
    "espírito santo": "ES",
    "espirito santo": "ES",
    "goiás": "GO",
    "goias": "GO",
    "maranhão": "MA",
    "maranhao": "MA",
    "mato grosso do sul": "MS",
    "mato grosso": "MT",
    "minas gerais": "MG",
    "pará": "PA",
    "para": "PA",
    "paraíba": "PB",
    "paraiba": "PB",
    "paraná": "PR",
    "parana": "PR",
    "pernambuco": "PE",
    "piauí": "PI",
    "piaui": "PI",
    "rio de janeiro": "RJ",
    "rio grande do norte": "RN",
    "rio grande do sul": "RS",
    "rondônia": "RO",
    "rondonia": "RO",
    "roraima": "RR",
    "santa catarina": "SC",
    "são paulo": "SP",
    "sao paulo": "SP",
    "sergipe": "SE",
    "tocantins": "TO",
}

SIGLAS_UF_VALIDAS: set[str] = {
    "AC",
    "AL",
    "AM",
    "AP",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MG",
    "MS",
    "MT",
    "PA",
    "PB",
    "PE",
    "PI",
    "PR",
    "RJ",
    "RN",
    "RO",
    "RR",
    "RS",
    "SC",
    "SE",
    "SP",
    "TO",
}

PADRAO_SIGLA_UF = re.compile(r"\b(AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO)\b")

PADRAO_PARLAMENTAR_NOMINAL = re.compile(
    r"\b(?:Deputad[oa]|Senador[a]?)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+"
    r"(?:\s+(?:de|da|do|dos|das)?\s*[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+){0,2})"
)

ATORES_INSTITUCIONAIS_MAPA: dict[str, str] = {
    "relator geral": "Relator Geral",
    "relator-geral": "Relator Geral",
    "comissão de saúde": "Comissão de Saúde",
    "comissão da saúde": "Comissão de Saúde",
    "comissão de educação": "Comissão de Educação",
    "comissão mista de orçamento": "Comissão Mista de Orçamento (CMO)",
    "comissão mista de planos": "Comissão Mista de Orçamento (CMO)",
    "bancada estadual": "Bancada Estadual",
}

MAPA_TAGS_TEMATICAS: dict[str, str] = {
    "emenda pix": "Emendas PIX",
    "emendas pix": "Emendas PIX",
    "transferência especial": "Emendas PIX",
    "transferências especiais": "Emendas PIX",
    "rp9": "RP9 (Relator)",
    "orçamento secreto": "RP9 (Relator)",
    "rp8": "RP8 (Comissão)",
    "rp7": "RP7 (Bancada)",
    "rp6": "RP6 (Individual)",
    "stf": "STF",
    "supremo tribunal federal": "STF",
    "cgu": "CGU",
    "controladoria-geral da união": "CGU",
    "siafi": "SIAFI",
    "transferegov": "Transferegov",
    "siconv": "SICONV",
    "restos a pagar": "Restos a Pagar",
    "saúde": "Saúde",
    "educação": "Educação",
    "assistência social": "Assistência Social",
    "urbanismo": "Urbanismo",
    "convênio": "Convênios",
    "convênios": "Convênios",
}


@dataclass
class ArtigoProcessado:
    """Estrutura tipada correspondente à tabela 2_silver.fato_noticias_contexto."""

    id_artigo: str
    nome_fonte: str
    url_artigo: str
    titulo: str
    subtitulo: str
    autor: str
    data_publicacao: date
    dh_publicacao: datetime
    conteudo_texto: str
    lead_resumo: str
    tags: list[str]
    parlamentares_mencionados: list[str]
    ufs_mencionadas: list[str]
    qtd_palavras: int
    dh_processamento: datetime

    def to_dict(self) -> dict[str, object]:
        """Converte o artigo processado para dicionário compatível com BigQuery / Parquet."""
        return {
            "id_artigo": self.id_artigo,
            "nome_fonte": self.nome_fonte,
            "url_artigo": self.url_artigo,
            "titulo": self.titulo,
            "subtitulo": self.subtitulo,
            "autor": self.autor,
            "data_publicacao": self.data_publicacao,
            "dh_publicacao": self.dh_publicacao,
            "conteudo_texto": self.conteudo_texto,
            "lead_resumo": self.lead_resumo,
            "tags": self.tags,
            "parlamentares_mencionados": self.parlamentares_mencionados,
            "ufs_mencionadas": self.ufs_mencionadas,
            "qtd_palavras": int(self.qtd_palavras),
            "dh_processamento": self.dh_processamento,
        }


def gerar_id_artigo(url_artigo: str) -> str:
    """Gera o hash SHA-256 único baseado na URL canônica do artigo."""
    return hashlib.sha256(url_artigo.strip().encode("utf-8", errors="ignore")).hexdigest()


def extrair_entidades_texto(
    texto: str,
    tags_iniciais: tuple[str, ...] = (),
) -> tuple[list[str], list[str], list[str]]:
    """Extrai heurísticamente (tags, parlamentares_mencionados, ufs_mencionadas) do texto."""
    texto_limpo = texto or ""
    texto_lower = texto_limpo.lower()

    # 1. UFs mencionadas (por sigla em caixa alta ou nome do estado)
    ufs_encontradas: set[str] = set()
    for match_uf in PADRAO_SIGLA_UF.findall(texto_limpo):
        if match_uf in SIGLAS_UF_VALIDAS:
            ufs_encontradas.add(match_uf)

    for nome_estado, sigla in MAPA_ESTADOS_UF.items():
        if re.search(rf"\b{re.escape(nome_estado)}\b", texto_lower):
            ufs_encontradas.add(sigla)

    # 2. Parlamentares e atores institucionais mencionados
    parlamentares_encontrados: set[str] = set()
    for match_parl in PADRAO_PARLAMENTAR_NOMINAL.findall(texto_limpo):
        nome_norm = " ".join(match_parl.split())
        if len(nome_norm) > 2:
            parlamentares_encontrados.add(nome_norm)

    for chave_inst, rotulo_inst in ATORES_INSTITUCIONAIS_MAPA.items():
        if chave_inst in texto_lower:
            parlamentares_encontrados.add(rotulo_inst)

    # 3. Tags temáticas
    tags_encontradas: set[str] = set(tags_iniciais)
    for termo, tag_canonica in MAPA_TAGS_TEMATICAS.items():
        if termo in texto_lower:
            tags_encontradas.add(tag_canonica)

    return (
        sorted(tags_encontradas),
        sorted(parlamentares_encontrados),
        sorted(ufs_encontradas),
    )


def _parsear_data_iso(valor: str | None, fallback: datetime) -> tuple[date, datetime]:
    """Tenta converter string ISO/data em (date, datetime UTC)."""
    if not valor:
        return fallback.date(), fallback

    texto = valor.strip()
    try:
        dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.date(), dt
    except ValueError:
        pass

    match_data_br = re.search(r"(\d{2})/(\d{2})/(\d{4})", texto)
    if match_data_br:
        dia, mes, ano = map(int, match_data_br.groups())
        try:
            dt = datetime(ano, mes, dia, tzinfo=timezone.utc)
            return dt.date(), dt
        except ValueError:
            pass

    match_data_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if match_data_iso:
        ano, mes, dia = map(int, match_data_iso.groups())
        try:
            dt = datetime(ano, mes, dia, tzinfo=timezone.utc)
            return dt.date(), dt
        except ValueError:
            pass

    return fallback.date(), fallback


def extrair_artigo_limpo(
    html_bruto: str,
    url_artigo: str,
    id_fonte: str,
    dh_coleta: datetime | None = None,
) -> ArtigoProcessado | None:
    """Extrai texto higienizado, metadados e entidades de um HTML bruto."""
    if not html_bruto or not html_bruto.strip():
        return None

    timestamp_ref = dh_coleta or datetime.now(timezone.utc)
    if timestamp_ref.tzinfo is None:
        timestamp_ref = timestamp_ref.replace(tzinfo=timezone.utc)

    fonte_cfg = FONTES_SCRAPING.get(id_fonte.strip().lower())
    nome_amigavel = fonte_cfg.nome_amigavel if fonte_cfg else id_fonte
    tags_padrao = fonte_cfg.tags_padrao if fonte_cfg else ()

    soup = BeautifulSoup(html_bruto, "html.parser")

    # Extração de título
    meta_og_title = soup.find("meta", attrs={"property": "og:title"})
    tag_h1 = soup.find("h1")
    tag_title = soup.find("title")
    titulo = ""
    if meta_og_title and meta_og_title.get("content"):
        titulo = str(meta_og_title["content"]).strip()
    elif tag_h1 and tag_h1.get_text(strip=True):
        titulo = tag_h1.get_text(" ", strip=True)
    elif tag_title and tag_title.get_text(strip=True):
        titulo = tag_title.get_text(" ", strip=True)
    else:
        titulo = f"Publicação {nome_amigavel}"

    # Extração de subtítulo / linha-fina
    meta_desc = soup.find("meta", attrs={"property": "og:description"}) or soup.find(
        "meta", attrs={"name": "description"}
    )
    tag_sub = soup.find(class_=re.compile(r"subtitulo|subtitle|resumo|lead", re.IGNORECASE))
    subtitulo = ""
    if meta_desc and meta_desc.get("content"):
        subtitulo = str(meta_desc["content"]).strip()
    elif tag_sub and tag_sub.get_text(strip=True):
        subtitulo = tag_sub.get_text(" ", strip=True)

    # Extração de autor
    meta_author = soup.find("meta", attrs={"name": "author"})
    autor = str(meta_author["content"]).strip() if (meta_author and meta_author.get("content")) else nome_amigavel

    # Extração de data de publicação
    meta_pub = soup.find("meta", attrs={"property": "article:published_time"})
    tag_time = soup.find("time")
    str_data: str | None = None
    if meta_pub and meta_pub.get("content"):
        str_data = str(meta_pub["content"])
    elif tag_time:
        str_data = str(tag_time.get("datetime") or tag_time.get_text(strip=True))

    data_pub, dh_pub = _parsear_data_iso(str_data, timestamp_ref)

    # Extração limpa do corpo de texto (Trafilatura com fallback BeautifulSoup higienizado)
    texto_trafilatura = trafilatura.extract(
        html_bruto,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )

    if texto_trafilatura and len(texto_trafilatura.strip()) >= 80:
        conteudo_texto = " ".join(texto_trafilatura.split())
    else:
        for tag_indesejada in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
            tag_indesejada.decompose()
        container = soup.find("article") or soup.find("main") or soup.body or soup
        paragrafos = [p.get_text(" ", strip=True) for p in container.find_all("p") if p.get_text(strip=True)]
        if paragrafos:
            conteudo_texto = " ".join(paragrafos)
        else:
            conteudo_texto = " ".join(container.get_text(" ", strip=True).split())

    if not conteudo_texto:
        return None

    # Lead resumo (primeiros 360 caracteres sem cortar palavra ao meio)
    if len(conteudo_texto) <= 360:
        lead_resumo = conteudo_texto
    else:
        corte = conteudo_texto[:360].rsplit(" ", 1)[0]
        lead_resumo = f"{corte}..."

    palavras = conteudo_texto.split()
    qtd_palavras = len(palavras)

    texto_completo_ner = f"{titulo} {subtitulo} {conteudo_texto}"
    tags, parlamentares, ufs = extrair_entidades_texto(texto_completo_ner, tags_iniciais=tags_padrao)

    return ArtigoProcessado(
        id_artigo=gerar_id_artigo(url_artigo),
        nome_fonte=nome_amigavel,
        url_artigo=url_artigo.strip(),
        titulo=titulo,
        subtitulo=subtitulo,
        autor=autor,
        data_publicacao=data_pub,
        dh_publicacao=dh_pub,
        conteudo_texto=conteudo_texto,
        lead_resumo=lead_resumo,
        tags=tags,
        parlamentares_mencionados=parlamentares,
        ufs_mencionadas=ufs,
        qtd_palavras=qtd_palavras,
        dh_processamento=datetime.now(timezone.utc),
    )
