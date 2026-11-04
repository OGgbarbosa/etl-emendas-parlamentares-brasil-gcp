CREATE OR REPLACE VIEW `project-f2711ebc-82b0-49cb-b84.3_gold.view_ai_distribuicao_geografica` (
    DT_ANO OPTIONS(description="Ano de referência do orçamento da emenda parlamentar (exercício fiscal). Tipo: INT64."),
    SG_REGIAO OPTIONS(description="Grande região geográfica brasileira de destino (NORTE, NORDESTE, SUDESTE, SUL, CENTRO-OESTE ou NACIONAL)."),
    SG_UF OPTIONS(description="Sigla da Unidade Federativa de destino dos recursos (ex.: SP, BA, NACI para âmbito nacional)."),
    DS_MUNICIPIO OPTIONS(description="Nome do município beneficiado ou classificação territorial ('ESTADUAL', 'NACIONAL')."),
    CD_MUNICIPIO_IBGE OPTIONS(description="Código numérico de 7 dígitos do IBGE para o município. Sentinela: -1 indica destinação estadual, nacional ou sem município discriminado."),
    DS_AMBITO_GEOGRAFICO OPTIONS(description="Classificação da esfera do destino: MUNICIPAL (município específico), ESTADUAL (governo estadual ou múltiplos municípios do estado) ou NACIONAL_REGIONAL."),
    FL_MUNICIPIO_ESPECIFICO OPTIONS(description="Flag booleana indicando se o recurso foi destinado especificamente a um município com código IBGE individualizado (TRUE) ou se é de âmbito estadual/nacional/genérico (FALSE)."),
    QTD_EMENDAS OPTIONS(description="Quantidade de emendas orçamentárias distintas destinadas a este território no ano."),
    QTD_CONVENIOS OPTIONS(description="Quantidade total de convênios federais pactuados para as emendas desta localidade no ano."),
    VL_EMPENHADO OPTIONS(description="Valor total empenhado (reservado) para esta localidade no exercício. Unidade: Reais (BRL). Aditivo entre linhas."),
    VL_LIQUIDADO OPTIONS(description="Valor total liquidado (atestado/entregue) para esta localidade. Unidade: Reais (BRL). Aditivo entre linhas."),
    VL_PAGO OPTIONS(description="Valor total efetivamente transferido/pago para a localidade no ano. Unidade: Reais (BRL). Aditivo entre linhas."),
    VL_CONVENIO OPTIONS(description="Valor total pactuado em convênios federais para esta localidade (sem duplicação N:N). Unidade: Reais (BRL)."),
    TKM_PAGO_POR_EMENDA OPTIONS(description="Ticket médio pago por emenda destinada à localidade (VL_PAGO / QTD_EMENDAS). Regra para IA: NUNCA tire média de médias; recalcule com ROUND(SAFE_DIVIDE(SUM(VL_PAGO), SUM(QTD_EMENDAS)), 2)."),
    TX_EXECUCAO OPTIONS(description="Taxa de execução percentual (VL_PAGO / VL_EMPENHADO * 100). Regra para IA: NUNCA use AVG(TX_EXECUCAO) ao agrupar; recalcule com ROUND(SAFE_DIVIDE(SUM(VL_PAGO), SUM(VL_EMPENHADO)) * 100, 2)."),
    DH_PROCESSAMENTO OPTIONS(description="Timestamp UTC de materialização do Data Mart Gold de origem."),
    DS_RESUMO_SEMANTICO OPTIONS(description="Narrativa em linguagem natural formatada para indexação vetorial e RAG no Vertex AI. Sintetiza localidade, região, âmbito, volume financeiro e convênios.")
)
OPTIONS(
    description="[Visão Semântica p/ IA] Distribuição geográfica consolidada dos repasses de emendas parlamentares e convênios federais. Grão da linha: [DT_ANO, SG_REGIAO, SG_UF, DS_MUNICIPIO, CD_MUNICIPIO_IBGE, DS_AMBITO_GEOGRAFICO]. Responde perguntas sobre recursos por estado, município, região e âmbito de governo.",
    labels=[("camada", "gold_semantica"), ("consumidor", "vertex_ai_gemini"), ("dominio", "distribuicao_geografica")]
)
AS
SELECT 
    DT_ANO,
    SG_REGIAO,
    SG_UF,
    DS_MUNICIPIO,
    CD_MUNICIPIO_IBGE,
    DS_AMBITO_GEOGRAFICO,
    (CD_MUNICIPIO_IBGE > 0) AS FL_MUNICIPIO_ESPECIFICO,
    QTD_EMENDAS,
    QTD_CONVENIOS,
    VL_EMPENHADO,
    VL_LIQUIDADO,
    VL_PAGO,
    VL_CONVENIO,
    TKM_PAGO_POR_EMENDA,
    TX_EXECUCAO,
    DH_PROCESSAMENTO,
    CONCAT(
        'No ano de ', CAST(DT_ANO AS STRING), ', a localidade ', DS_MUNICIPIO, 
        ' (UF: ', SG_UF, ', Região: ', SG_REGIAO, ', Âmbito: ', DS_AMBITO_GEOGRAFICO, 
        ', IBGE: ', CAST(CD_MUNICIPIO_IBGE AS STRING), ') recebeu ', 
        CAST(QTD_EMENDAS AS STRING), ' emenda(s) parlamentar(es) e ', 
        CAST(QTD_CONVENIOS AS STRING), ' convênio(s). Total empenhado: R$ ', 
        FORMAT("%'.2f", VL_EMPENHADO), '; Total liquidado: R$ ', 
        FORMAT("%'.2f", VL_LIQUIDADO), '; Total pago: R$ ', 
        FORMAT("%'.2f", VL_PAGO), ' (Taxa de Execução: ', 
        IFNULL(CAST(TX_EXECUCAO AS STRING), '0.00'), '%). Valor pactuado em convênios: R$ ', 
        FORMAT("%'.2f", VL_CONVENIO), '.'
    ) AS DS_RESUMO_SEMANTICO
FROM `project-f2711ebc-82b0-49cb-b84.3_gold.tbl_distribuicao_geografica`;
