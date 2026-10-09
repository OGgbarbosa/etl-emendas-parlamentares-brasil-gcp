import io
import os
from datetime import datetime, timezone

import polars as pl


def processar_csv_para_parquet(caminho_csv: str) -> io.BytesIO:
    """Lê o CSV, adiciona metadados da Bronze e serializa em memória como Parquet."""
    print(f"Lendo arquivo local: {caminho_csv}...")
    
    # infer_schema_length=10000 evita falhas de inferência em arquivos heterogêneos
    df = pl.read_csv(caminho_csv, infer_schema_length=10000, encoding='latin1')

    # Inclusão de colunas de auditoria indispensáveis para a camada Bronze
    nome_arquivo = os.path.basename(caminho_csv)
    df_bronze = df.with_columns([
        pl.lit(datetime.now(timezone.utc)).alias("_ingestion_timestamp"),
        pl.lit(nome_arquivo).alias("_source_file")
    ])

    # Gravação em buffer de memória (evita criar arquivo temporário em disco)
    buffer = io.BytesIO()
    df_bronze.write_parquet(buffer, compression="snappy")
    buffer.seek(0)
    
    print(f"Processamento concluído: {df_bronze.shape[0]} linhas e {df_bronze.shape[1]} colunas.")
    return buffer

if __name__ == "__main__":
    import glob
    
    # Busca todos os arquivos CSV na pasta database
    arquivos_csv = glob.glob("database/*.csv")
    
    if not arquivos_csv:
        print("Nenhum arquivo CSV encontrado na pasta 'database'.")
    else:
        for caminho in arquivos_csv:
            try:
                buffer = processar_csv_para_parquet(caminho)
                tamanho_mb = buffer.getbuffer().nbytes / (1024 * 1024)
                print(f"-> Sucesso! Arquivo processado em memória ({tamanho_mb:.2f} MB).\n")
            except Exception as e:
                print(f"-> Erro ao processar {caminho}: {e}\n")