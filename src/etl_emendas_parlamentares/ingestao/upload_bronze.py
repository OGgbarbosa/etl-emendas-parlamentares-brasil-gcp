import glob
import io
import os
from pathlib import Path

from dotenv import load_dotenv

from etl_emendas_parlamentares.conexao.big_query import get_storage_client
from etl_emendas_parlamentares.processamento.csv_parquet import processar_csv_para_parquet

load_dotenv()

ARQUIVOS_ALVO = [
    "EmendasParlamentares.csv",
    "EmendasParlamentares_Convenios.csv",
    "EmendasParlamentares_PorFavorecido.csv",
]

def upload_buffer_para_gcs(buffer: io.BytesIO, destino_gcs: str, content_type: str = "application/octet-stream") -> str:
    """Faz upload de um buffer de memória para o Google Cloud Storage.

    Args:
        buffer: Buffer com os dados (ex: Parquet serializado).
        destino_gcs: Caminho do arquivo dentro do bucket (ex: '0_raw/EmendasParlamentares.parquet').
        content_type: Tipo MIME do arquivo.

    Returns:
        URI completa no GCS (ex: 'gs://meu-bucket/0_raw/...').
    """
    raw_bucket = os.getenv("GCS_BUCKET_NAME", "")
    bucket_name = raw_bucket.replace("gs://", "").strip("/")

    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destino_gcs)

    print(f"-> Fazendo upload para gs://{bucket_name}/{destino_gcs}...")
    buffer.seek(0)
    blob.upload_from_file(buffer, content_type=content_type)

    uri_gcs = f"gs://{bucket_name}/{destino_gcs}"
    print(f"-> Upload finalizado com sucesso: {uri_gcs}")
    return uri_gcs


def ingerir_arquivos_bronze(pasta_origem: str | None = None, prefixo_destino: str = "0_raw") -> list[str]:
    """Lê os CSVs com Polars, converte para Parquet e faz upload para a camada 0_raw no GCS."""
    if not pasta_origem:
        pasta_origem = "database" if os.path.exists("database") and glob.glob("database/*.csv") else "database_sample"

    print("\n=======================================================")
    print(f"Iniciando ingestão da camada Bronze no GCS ({prefixo_destino})")
    print(f"Pasta de origem local: {pasta_origem}")
    print("=======================================================\n")

    uris_enviadas = []
    for nome_arquivo in ARQUIVOS_ALVO:
        caminho_csv = os.path.join(pasta_origem, nome_arquivo)
        if not os.path.exists(caminho_csv):
            print(f"[AVISO] Arquivo {caminho_csv} não encontrado, pulando...")
            continue

        nome_base = Path(nome_arquivo).stem
        destino_gcs = f"{prefixo_destino}/{nome_base}.parquet"

        print(f"\n[1/2] Processando {nome_arquivo} com Polars...")
        buffer_parquet = processar_csv_para_parquet(caminho_csv)

        tamanho_mb = buffer_parquet.getbuffer().nbytes / (1024 * 1024)
        print(f"[2/2] Enviando para o Cloud Storage ({tamanho_mb:.2f} MB)...")
        uri = upload_buffer_para_gcs(buffer_parquet, destino_gcs)
        uris_enviadas.append(uri)

    print(f"\n[SUCESSO] Ingestão concluída! Total de {len(uris_enviadas)} arquivos enviados para {prefixo_destino}.")
    return uris_enviadas


if __name__ == "__main__":
    ingerir_arquivos_bronze()
