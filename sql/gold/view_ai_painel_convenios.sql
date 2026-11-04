CREATE OR REPLACE VIEW `project-f2711ebc-82b0-49cb-b84.3_gold.view_ai_painel_convenios` (
    DT_ANO OPTIONS(description="Ano de publicação/celebração do convênio federal. Sentinela: -1 indica convênio com data não informada na fonte original. Tipo: INT64."),
    SG_UF OPTIONS(description="Sigla da Unidade Federativa da localidade do convenente ou execução do instrumento."),
    DS_CONVENENTE OPTIONS(description="Nome do ente público ou privado convenente (órgão executor, prefeitura ou entidade que assinou o convênio)."),
    DS_FUNCAO OPTIONS(description="Área funcional de governo vinculada ao convênio (ex.: Saúde, Educação, Urbanismo)."),
    FL_ANO_PUBLICACAO_VALIDO OPTIONS(description="Flag booleana indicando se o convênio possui ano de publicação conhecido (TRUE) ou sentinela -1 (FALSE)."),
    QTD_CONVENIOS OPTIONS(description="Quantidade de instrumentos de convênios únicos celebrados no ano/UF/função/convenente (grão deduplicado, sem inflação por repetição de emenda)."),
    QTD_EMENDAS_VINCULADAS OPTIONS(description="Quantidade de emendas parlamentares distintas associadas a esses convênios."),
    VL_TOTAL_CONVENIADO OPTIONS(description="Valor monetário global pactuado nos convênios (com deduplicação estrita de instrumentos). Unidade: Reais (BRL). Aditivo entre convenentes e funções."),
    TKM_VALOR_POR_CONVENIO OPTIONS(description="Ticket médio pactuado por instrumento de convênio (VL_TOTAL_CONVENIADO / QTD_CONVENIOS). Regra para IA: NUNCA tire média de médias; recalcule com ROUND(SAFE_DIVIDE(SUM(VL_TOTAL_CONVENIADO), SUM(QTD_CONVENIOS)), 2)."),
    DH_PROCESSAMENTO OPTIONS(description="Timestamp UTC de materialização do Data Mart Gold de origem."),
    DS_RESUMO_SEMANTICO OPTIONS(description="Narrativa em linguagem natural formatada para indexação vetorial e RAG no Vertex AI. Sintetiza convenente, estado, função governamental, total conveniado e ticket médio.")
)
OPTIONS(
    description="[Visão Semântica p/ IA] Painel consolidado de instrumentos de convênios federais firmados a partir de emendas parlamentares. Grão da linha: [DT_ANO, SG_UF, DS_CONVENENTE, DS_FUNCAO]. Responde perguntas sobre órgãos e prefeituras que mais celebraram convênios, descentralização de recursos e ticket médio contratado.",
    labels=[("camada", "gold_semantica"), ("consumidor", "vertex_ai_gemini"), ("dominio", "painel_convenios")]
)
AS
SELECT 
    DT_ANO,
    SG_UF,
    DS_CONVENENTE,
    DS_FUNCAO,
    (DT_ANO > 0) AS FL_ANO_PUBLICACAO_VALIDO,
    QTD_CONVENIOS,
    QTD_EMENDAS_VINCULADAS,
    VL_TOTAL_CONVENIADO,
    TKM_VALOR_POR_CONVENIO,
    DH_PROCESSAMENTO,
    CONCAT(
        'No ano de ', CASE WHEN DT_ANO > 0 THEN CAST(DT_ANO AS STRING) ELSE 'Não informado' END, 
        ', o convenente ', DS_CONVENENTE, ' (UF: ', SG_UF, ', Área: ', DS_FUNCAO, 
        ') pactuou ', CAST(QTD_CONVENIOS AS STRING), ' convênio(s) vinculados a ', 
        CAST(QTD_EMENDAS_VINCULADAS AS STRING), ' emenda(s) parlamentar(es). O valor total conveniado foi de R$ ', 
        FORMAT("%'.2f", VL_TOTAL_CONVENIADO), ', com ticket médio de R$ ', 
        FORMAT("%'.2f", TKM_VALOR_POR_CONVENIO), ' por instrumento.'
    ) AS DS_RESUMO_SEMANTICO
FROM `project-f2711ebc-82b0-49cb-b84.3_gold.tbl_painel_convenios`;
