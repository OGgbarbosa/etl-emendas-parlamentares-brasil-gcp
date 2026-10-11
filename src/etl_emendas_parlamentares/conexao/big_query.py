import os

from dotenv import load_dotenv
from google.cloud import bigquery, storage

#teste

# Carrega as variáveis do arquivo .env
load_dotenv()

def get_bigquery_client() -> bigquery.Client:
    """
    Cria e retorna um cliente do BigQuery autenticado.
    A autenticação é feita automaticamente através da variável 
    GOOGLE_APPLICATION_CREDENTIALS definida no .env ou pelas credenciais do GCP.
    """
    project_id = os.getenv("GCP_PROJECT_ID")
    return bigquery.Client(project=project_id) if project_id else bigquery.Client()


def get_storage_client() -> storage.Client:
    """Retorna o cliente autenticado do Google Cloud Storage."""
    project_id = os.getenv("GCP_PROJECT_ID")
    return storage.Client(project=project_id) if project_id else storage.Client()

if __name__ == "__main__":
    # Testando a conexão
    try:
        bq_client = get_bigquery_client()
        print(f"Conectado com sucesso ao GCP no projeto: {bq_client.project}")
        
        # Teste simples: listar os datasets
        datasets = list(bq_client.list_datasets())
        if datasets:
            print("Datasets encontrados:")
            for dataset in datasets:
                print(f"- {dataset.dataset_id}")
        else:
            print("Nenhum dataset encontrado no projeto.")
            
    except Exception as e:
        print(f"Erro ao conectar no GCP: {e}")