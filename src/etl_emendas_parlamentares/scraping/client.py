"""Cliente HTTP resiliente e ético para a esteira de Web Scraping."""

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from etl_emendas_parlamentares.config.config import (
    SCRAPING_RATE_LIMIT_SECONDS,
    SCRAPING_TIMEOUT_SECONDS,
    SCRAPING_USER_AGENT,
)

logger = logging.getLogger(__name__)


@dataclass
class RespostaColeta:
    """Representa um registro bruto de coleta HTTP persistível em 2_silver.raw_scraping_<fonte>."""

    id_requisicao: str
    url_artigo: str
    nome_fonte: str
    dh_coleta: datetime
    http_status: int
    payload_bruto: str
    hash_conteudo: str

    def to_dict(self) -> dict[str, object]:
        """Converte o registro para dicionário compatível com o schema BigQuery."""
        return {
            "id_requisicao": self.id_requisicao,
            "url_artigo": self.url_artigo,
            "nome_fonte": self.nome_fonte,
            "dh_coleta": self.dh_coleta,
            "http_status": int(self.http_status),
            "payload_bruto": self.payload_bruto,
            "hash_conteudo": self.hash_conteudo,
        }


def calcular_hash_conteudo(url_artigo: str, payload_bruto: str) -> str:
    """Calcula o hash SHA-256 determinístico para controle de idempotência."""
    base = f"{url_artigo.strip()}||{payload_bruto.strip()}"
    return hashlib.sha256(base.encode("utf-8", errors="ignore")).hexdigest()


def criar_resposta_coleta(
    url_artigo: str,
    nome_fonte: str,
    payload_bruto: str,
    http_status: int = 200,
    dh_coleta: datetime | None = None,
) -> RespostaColeta:
    """Constrói uma instância estruturada de RespostaColeta com UUID e hash SHA-256."""
    timestamp = dh_coleta or datetime.now(timezone.utc)
    return RespostaColeta(
        id_requisicao=str(uuid.uuid4()),
        url_artigo=url_artigo.strip(),
        nome_fonte=nome_fonte.strip().lower(),
        dh_coleta=timestamp,
        http_status=http_status,
        payload_bruto=payload_bruto,
        hash_conteudo=calcular_hash_conteudo(url_artigo, payload_bruto),
    )


class ScrapingHttpClient:
    """Cliente HTTP síncrono com User-Agent ético, rate limiting cortês e retry exponencial."""

    def __init__(
        self,
        user_agent: str = SCRAPING_USER_AGENT,
        timeout: float = SCRAPING_TIMEOUT_SECONDS,
        rate_limit_seconds: float = SCRAPING_RATE_LIMIT_SECONDS,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.rate_limit_seconds = max(0.0, rate_limit_seconds)
        self._ultimo_request_ts: float = 0.0

    def obter_headers(self) -> dict[str, str]:
        """Retorna os cabeçalhos HTTP éticos e compatíveis com portais institucionais."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
        }

    def _aguardar_rate_limit(self) -> None:
        """Aplica pausa cortês entre requisições consecutivas."""
        if self.rate_limit_seconds <= 0:
            return
        decorrido = time.monotonic() - self._ultimo_request_ts
        if self._ultimo_request_ts > 0 and decorrido < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - decorrido)
        self._ultimo_request_ts = time.monotonic()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    )
    def _executar_get(self, url: str) -> httpx.Response:
        """Executa a chamada HTTP GET com suporte a redirecionamento e retry automático."""
        self._aguardar_rate_limit()
        with httpx.Client(
            headers=self.obter_headers(),
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            return client.get(url)

    def coletar_url(self, url: str, nome_fonte: str) -> RespostaColeta | None:
        """Realiza o download de uma URL e empacota o payload bruto em RespostaColeta."""
        try:
            logger.info("Coletando URL [%s]: %s", nome_fonte, url)
            resp = self._executar_get(url)
            texto = resp.text or ""
            if not texto.strip():
                logger.warning("Payload vazio retornado para URL [%s]: %s", nome_fonte, url)
                return None

            return criar_resposta_coleta(
                url_artigo=str(resp.url or url),
                nome_fonte=nome_fonte,
                payload_bruto=texto,
                http_status=resp.status_code,
            )
        except Exception as exc:
            logger.warning("Falha ao coletar URL [%s] %s: %s", nome_fonte, url, exc)
            return None
