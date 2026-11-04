CREATE OR REPLACE VIEW `project-f2711ebc-82b0-49cb-b84.3_gold.view_ai_ranking_favorecidos` (
    DT_ANO OPTIONS(description="Ano civil de repasse financeiro efetivo das emendas ao favorecido. Tipo: INT64."),
    CD_FAVORECIDO OPTIONS(description="Identificador fiscal ou código único do beneficiário (CNPJ para pessoas jurídicas, CPF mascarado para físicas, ou código de órgão público)."),
    DS_FAVORECIDO OPTIONS(description="Razão social, nome de fantasia ou denominação oficial da entidade beneficiária."),
    DS_TIPO_FAVORECIDO OPTIONS(description="Tipo de entidade recebedora: PESSOA JURÍDICA, PESSOA FÍSICA, FUNDO DE SAÚDE, PREFEITURA, etc."),
    DS_NATUREZA_JURIDICA OPTIONS(description="Classificação jurídica formal da entidade (ex.: Município, Associação Privada, Sociedade Empresária)."),
    SG_UF_FAVORECIDO OPTIONS(description="Unidade Federativa de domicílio ou sede do favorecido."),
    FL_FAVORECIDO_MULTI_PARLAMENTAR OPTIONS(description="Flag booleana indicando se o favorecido recebeu repasses de múltiplos parlamentares distintos no mesmo ano (TRUE) ou de um único autor (FALSE)."),
    VL_RECEBIDO_ANO OPTIONS(description="Valor total em reais efetivamente transferido ao favorecido no ano em questão. Unidade: Reais (BRL). Aditivo entre favorecidos e anos."),
    VL_RECEBIDO_ACUMULADO_ATE_ANO OPTIONS(description="Valor acumulado histórico recebido por este favorecido desde o início da série até o ano desta linha. Regra para IA: Métrica de janela analítica. NÃO USE SUM() sobre esta coluna entre múltiplos anos."),
    VL_RECEBIDO_TOTAL_HISTORICO OPTIONS(description="Valor total absoluto recebido por este favorecido em toda a série histórica (todos os anos consolidados). Regra para IA: Métrica escalar estática. NUNCA aplique SUM() sobre esta coluna ao consolidar períodos."),
    QTD_PARLAMENTARES_DISTINTOS_ANO OPTIONS(description="Quantidade de parlamentares diferentes que destinaram recursos pagos a este favorecido no ano."),
    QTD_EMENDAS_DISTINTAS_ANO OPTIONS(description="Quantidade de emendas diferentes que geraram pagamentos para este favorecido no ano."),
    TKM_RECEBIDO_POR_PARLAMENTAR OPTIONS(description="Ticket médio recebido por parlamentar vinculado no ano (VL_RECEBIDO_ANO / QTD_PARLAMENTARES_DISTINTOS_ANO)."),
    QTD_MESES_COM_REPASSE OPTIONS(description="Número de meses distintos do ano em que houve repasses ao favorecido (indicador de recorrência)."),
    QTD_TRANSFERENCIAS_RECEBIDAS OPTIONS(description="Quantidade total de ordens bancárias ou transferências efetuadas ao favorecido no ano."),
    DT_PRIMEIRO_RECEBIMENTO_ANO OPTIONS(description="Data da primeira transferência registrada para o favorecido neste exercício fiscal."),
    DT_ULTIMO_RECEBIMENTO_ANO OPTIONS(description="Data da última transferência registrada para o favorecido neste exercício fiscal."),
    DT_PRIMEIRO_RECEBIMENTO_HISTORICO OPTIONS(description="Data da primeiríssima transferência recebida pelo favorecido em toda a base de dados."),
    DT_ULTIMO_RECEBIMENTO_HISTORICO OPTIONS(description="Data da mais recente transferência recebida pelo favorecido em toda a base de dados."),
    DH_PROCESSAMENTO OPTIONS(description="Timestamp UTC de materialização do Data Mart Gold de origem."),
    DS_RESUMO_SEMANTICO OPTIONS(description="Narrativa em linguagem natural formatada para indexação vetorial e RAG no Vertex AI. Sintetiza beneficiário, localização, montante recebido e relação com parlamentares.")
)
OPTIONS(
    description="[Visão Semântica p/ IA] Ranking e perfil analítico dos recebedores diretos de recursos de emendas parlamentares (entidades públicas, privadas e ONGs). Grão da linha: [DT_ANO, CD_FAVORECIDO, DS_FAVORECIDO, DS_TIPO_FAVORECIDO, DS_NATUREZA_JURIDICA, SG_UF_FAVORECIDO]. Responde perguntas sobre maiores fornecedores, entidades beneficiadas, recorrência e concentração entre parlamentares.",
    labels=[("camada", "gold_semantica"), ("consumidor", "vertex_ai_gemini"), ("dominio", "ranking_favorecidos")]
)
AS
SELECT 
    DT_ANO,
    CD_FAVORECIDO,
    DS_FAVORECIDO,
    DS_TIPO_FAVORECIDO,
    DS_NATUREZA_JURIDICA,
    SG_UF_FAVORECIDO,
    (QTD_PARLAMENTARES_DISTINTOS_ANO > 1) AS FL_FAVORECIDO_MULTI_PARLAMENTAR,
    VL_RECEBIDO_ANO,
    VL_RECEBIDO_ACUMULADO_ATE_ANO,
    VL_RECEBIDO_TOTAL_HISTORICO,
    QTD_PARLAMENTARES_DISTINTOS_ANO,
    QTD_EMENDAS_DISTINTAS_ANO,
    TKM_RECEBIDO_POR_PARLAMENTAR,
    QTD_MESES_COM_REPASSE,
    QTD_TRANSFERENCIAS_RECEBIDAS,
    DT_PRIMEIRO_RECEBIMENTO_ANO,
    DT_ULTIMO_RECEBIMENTO_ANO,
    DT_PRIMEIRO_RECEBIMENTO_HISTORICO,
    DT_ULTIMO_RECEBIMENTO_HISTORICO,
    DH_PROCESSAMENTO,
    CONCAT(
        'No ano de ', CAST(DT_ANO AS STRING), ', o favorecido ', DS_FAVORECIDO, 
        ' (Doc/Código: ', CD_FAVORECIDO, ', Tipo: ', DS_TIPO_FAVORECIDO, 
        ', UF: ', SG_UF_FAVORECIDO, ', Natureza: ', DS_NATUREZA_JURIDICA, 
        ') recebeu R$ ', FORMAT("%'.2f", VL_RECEBIDO_ANO), ' em ', 
        CAST(QTD_TRANSFERENCIAS_RECEBIDAS AS STRING), ' transferência(s) ao longo de ', 
        CAST(QTD_MESES_COM_REPASSE AS STRING), ' mês(es). Os repasses originaram-se de ', 
        CAST(QTD_PARLAMENTARES_DISTINTOS_ANO AS STRING), ' parlamentar(es) e ', 
        CAST(QTD_EMENDAS_DISTINTAS_ANO AS STRING), ' emenda(s). No total histórico acumulado em toda a base, o beneficiário soma R$ ', 
        FORMAT("%'.2f", VL_RECEBIDO_TOTAL_HISTORICO), '.'
    ) AS DS_RESUMO_SEMANTICO
FROM `project-f2711ebc-82b0-49cb-b84.3_gold.tbl_ranking_favorecidos`;
