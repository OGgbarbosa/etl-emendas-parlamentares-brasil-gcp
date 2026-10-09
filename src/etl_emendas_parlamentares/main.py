import argparse

from databricks.sdk.runtime import spark

from etl_emendas_parlamentares import emendas


def main():
    """Ponto de entrada do job de ingestão Bronze.

    Lê os 3 CSVs do Volume raw e salva como tabelas Delta
    na camada Bronze do catálogo datalake_emendas.
    """
    parser = argparse.ArgumentParser(
        description="Job de ingestão Bronze - Emendas Parlamentares",
    )
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    # Define o catálogo e schema padrão
    spark.sql(f"USE CATALOG `{args.catalog}`")
    spark.sql(f"USE SCHEMA `{args.schema}`")

    # Ingestão dos 3 arquivos CSV para tabelas Delta na camada Bronze
    tabelas = {
        "emendas_parlamentares": emendas.ler_emendas,
        "emendas_convenios": emendas.ler_convenios,
        "emendas_favorecidos": emendas.ler_favorecidos,
    }

    for nome_tabela, funcao_leitura in tabelas.items():
        print(f"-> Ingerindo tabela: {args.catalog}.{args.schema}.{nome_tabela} ...")
        df = funcao_leitura()
        (
            df.write
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable(nome_tabela)
        )
        print(f"   [OK] {nome_tabela} — {df.count()} linhas salvas.")

    print("[OK] Ingestão Bronze concluída com sucesso!")


if __name__ == "__main__":
    main()
