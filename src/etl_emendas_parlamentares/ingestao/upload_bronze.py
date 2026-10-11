import io
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from etl_emendas_parlamentares.conexao.big_query import get_storage_client
from etl_emendas_parlamentares.config.config import BRONZE_PREFIX, DIRETORIO_BRONZE_LOCAL

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _upload_arquivo_para_gcs(
    client,
    bucket_name: str,
    caminho_arquivo: Path | str,
    destino_gcs: str,
    content_type: str = "application/octet-stream",
) -> str:
    """Função auxiliar interna para upload de um arquivo local para o Cloud Storage via streaming."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destino_gcs)

    logger.info("Iniciando upload de '%s' para gs://%s/%s...", caminho_arquivo, bucket_name, destino_gcs)
    blob.upload_from_filename(str(caminho_arquivo), content_type=content_type)

    uri_gcs = f"gs://{bucket_name}/{destino_gcs}"
    logger.info("Upload finalizado com sucesso: %s", uri_gcs)
    return uri_gcs


def _upload_buffer_para_gcs(
    client,
    bucket_name: str,
    buffer: io.BytesIO,
    destino_gcs: str,
    content_type: str = "application/octet-stream",
) -> str:
    """Função auxiliar interna para upload de um buffer de memória para o Cloud Storage."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destino_gcs)

    logger.info("Iniciando upload de buffer para gs://%s/%s...", bucket_name, destino_gcs)
    buffer.seek(0)
    blob.upload_from_file(buffer, content_type=content_type)

    uri_gcs = f"gs://{bucket_name}/{destino_gcs}"
    logger.info("Upload finalizado com sucesso: %s", uri_gcs)
    return uri_gcs


def upload_bronze(
    origem_local: str | Path = DIRETORIO_BRONZE_LOCAL,
    prefixo_destino: str = BRONZE_PREFIX,
    dados: dict[str, io.BytesIO] | None = None,
) -> list[str]:
    """Realiza o upload dos dados para a camada Bronze no Google Cloud Storage.

    Pode ser executada sem argumentos para subir os arquivos .parquet gerados
    pelo primeiro passo (csv_parquet), ou receber os buffers diretamente.

    Args:
        origem_local: Diretório local onde os arquivos Parquet foram armazenados
                      (padrão: DIRETORIO_BRONZE_LOCAL = 'data/bronze').
        prefixo_destino: Prefixo/diretório de destino no bucket (padrão: BRONZE_PREFIX = '1_bronze').
        dados: Dicionário opcional de buffers em memória {nome_arquivo: buffer}.

    Returns:
        Lista de URIs dos arquivos enviados para o GCS.
    """
    uris_enviadas: list[str] = []

    try:
        bucket_name = os.getenv("GCS_BUCKET_NAME", "").replace("gs://", "").strip("/")
        if not bucket_name:
            raise ValueError("Nome do bucket GCS não configurado na variável de ambiente GCS_BUCKET_NAME.")

        client = get_storage_client()

        # Caso 1: Upload a partir de buffers em memória fornecidos
        if dados is not None:
            logger.info(
                "Iniciando upload de %d buffer(s) em memória para a camada Bronze (gs://%s/%s)...",
                len(dados),
                bucket_name,
                prefixo_destino,
            )
            for nome_arquivo, buffer in dados.items():
                destino_gcs = f"{prefixo_destino}/{nome_arquivo}"
                tamanho_mb = buffer.getbuffer().nbytes / (1024 * 1024)
                logger.info("Enviando '%s' (%.2f MB)...", nome_arquivo, tamanho_mb)
                uri = _upload_buffer_para_gcs(client, bucket_name, buffer, destino_gcs)
                uris_enviadas.append(uri)

        # Caso 2: Upload a partir dos arquivos salvos em disco
        else:
            caminho_origem = Path(origem_local)
            if not caminho_origem.exists():
                logger.warning(
                    "Diretório local '%s' não existe. Certifique-se de executar processar_csv_para_parquet() primeiro.",
                    caminho_origem,
                )
                return uris_enviadas

            arquivos_parquet = list(caminho_origem.glob("*.parquet"))
            if not arquivos_parquet:
                logger.warning(
                    "Nenhum arquivo .parquet encontrado em '%s'. Certifique-se de executar processar_csv_para_parquet() primeiro.",
                    caminho_origem,
                )
                return uris_enviadas

            logger.info(
                "Iniciando upload de %d arquivo(s) de '%s' para a camada Bronze (gs://%s/%s)...",
                len(arquivos_parquet),
                caminho_origem,
                bucket_name,
                prefixo_destino,
            )

            for arquivo in arquivos_parquet:
                destino_gcs = f"{prefixo_destino}/{arquivo.name}"
                tamanho_mb = arquivo.stat().st_size / (1024 * 1024)
                logger.info("Enviando '%s' (%.2f MB)...", arquivo.name, tamanho_mb)
                uri = _upload_arquivo_para_gcs(client, bucket_name, arquivo, destino_gcs)
                uris_enviadas.append(uri)

        logger.info(
            "Upload da camada Bronze finalizado com sucesso. Total de %d arquivo(s) enviado(s).",
            len(uris_enviadas),
        )

    except Exception:
        logger.exception("Erro durante o upload dos dados para a camada Bronze no GCS.")
        raise

    return uris_enviadas


if __name__ == "__main__":
    upload_bronze()
