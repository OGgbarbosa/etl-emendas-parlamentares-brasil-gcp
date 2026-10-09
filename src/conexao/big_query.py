import os
from google.cloud import bigquery
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

def get_bigquery_client() -> bigquery.Client:
    """
    Cria e retorna um cliente do BigQuery autenticado.
    A autenticação é feita automaticamente através da variável 
    GOOGLE_APPLICATION_CREDENTIALS definida no .env
    """
    project_id = os.getenv("GCP_PROJECT_ID")
    
    # Inicializa o cliente do BigQuery
    client = bigquery.Client(project=project_id)
    return client

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