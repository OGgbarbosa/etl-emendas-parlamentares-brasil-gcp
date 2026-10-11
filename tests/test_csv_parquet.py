from etl_emendas_parlamentares.processamento.csv_parquet import processar_csv_para_parquet


def test_processar_csv_para_parquet(tmp_path):
    # Executa processamento apontando para database_sample e salvando em pasta temporaria
    arquivos = processar_csv_para_parquet(
        pasta_origem="database_sample",
        pasta_destino=tmp_path,
    )

    assert len(arquivos) == 3
    nomes_arquivos = [arq.name for arq in arquivos]
    assert "EmendasParlamentares.parquet" in nomes_arquivos
    assert "EmendasParlamentares_Convenios.parquet" in nomes_arquivos
    assert "EmendasParlamentares_PorFavorecido.parquet" in nomes_arquivos

    for arq in arquivos:
        assert arq.exists()
        assert arq.stat().st_size > 0
