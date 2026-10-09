# ETL Emendas Parlamentares Brasil - GCP

Projeto de ingestão e processamento de dados de Emendas Parlamentares direcionado para o Google Cloud Platform (GCP) com BigQuery, Cloud Storage e processamento em Polars/Python.

## Stack & Ferramentas
- Gerenciador de pacotes e ambientes: `uv`
- Linter & Formatador: `ruff`
- Testes automatizados: `pytest`
- Nuvem: Google Cloud Platform (GCP)
  - BigQuery: Data Warehouse
  - Google Cloud Storage (GCS): Camada Raw / Landing
- Processamento: Python com `polars` / `pandas`
