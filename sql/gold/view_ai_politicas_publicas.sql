CREATE OR REPLACE VIEW `project-f2711ebc-82b0-49cb-b84.3_gold.view_ai_politicas_publicas` (
    DT_ANO OPTIONS(description="Ano de referência do orçamento da emenda parlamentar (exercício fiscal). Tipo: INT64."),
    CD_FUNCAO OPTIONS(description="Código numérico orçamentário da Função de Governo (ex.: 10 para Saúde, 12 para Educação)."),
    DS_FUNCAO OPTIONS(description="Nome descritivo da Função orçamentária / área temática de política pública (ex.: Saúde, Educação, Segurança Pública)."),
    CD_SUBFUNCAO OPTIONS(description="Código numérico orçamentário da Subfunção de Governo (especificação da política pública)."),
    DS_SUBFUNCAO OPTIONS(description="Nome descritivo da Subfunção de Governo (ex.: Atenção Básica, Ensino Superior)."),
    DS_TIPO_EMENDA OPTIONS(description="Modalidade da emenda parlamentar: INDIVIDUAL, BANCADA, COMISSAO ou RELATOR (RP9)."),
    DS_TENDENCIA_YOY OPTIONS(description="Classificação analítica da tendência de crescimento anual no valor pago: CRESCIMENTO (> +5%), RETRACAO (< -5%), ESTAVEL (entre -5% e +5%) ou SEM_BASE_COMPARACAO_ANTERIOR."),
    QTD_EMENDAS OPTIONS(description="Quantidade de emendas orçamentárias únicas destinadas a esta área temática no ano."),
    VL_EMPENHADO OPTIONS(description="Valor total empenhado na área temática e modalidade no exercício fiscal. Unidade: Reais (BRL). Aditivo entre linhas."),
    VL_LIQUIDADO OPTIONS(description="Valor total liquidado na área temática e modalidade. Unidade: Reais (BRL). Aditivo entre linhas."),
    VL_PAGO OPTIONS(description="Valor total efetivamente pago na área temática e modalidade. Unidade: Reais (BRL). Aditivo entre linhas."),
    TX_EXECUCAO OPTIONS(description="Taxa de execução percentual (VL_PAGO / VL_EMPENHADO * 100). Regra para IA: NUNCA use AVG(TX_EXECUCAO) ao agrupar; recalcule com ROUND(SAFE_DIVIDE(SUM(VL_PAGO), SUM(VL_EMPENHADO)) * 100, 2)."),
    TX_LIQUIDACAO OPTIONS(description="Taxa de liquidação percentual (VL_LIQUIDADO / VL_EMPENHADO * 100). Regra para IA: NUNCA use AVG(TX_LIQUIDACAO) ao agrupar; recalcule com ROUND(SAFE_DIVIDE(SUM(VL_LIQUIDADO), SUM(VL_EMPENHADO)) * 100, 2)."),
    PC_REPRESENTATIVIDADE_EMPENHO OPTIONS(description="Percentual de representatividade do empenho desta função no orçamento total de emendas daquele ano. Regra para IA: Não aditivo entre filtros parciais."),
    PC_REPRESENTATIVIDADE_PAGO OPTIONS(description="Percentual de representatividade do pagamento desta função no total pago de emendas daquele ano. Regra para IA: Não aditivo entre filtros parciais."),
    VL_PAGO_ANO_ANTERIOR OPTIONS(description="Valor total pago no ano imediatamente anterior (ano - 1) para a mesma função, subfunção e modalidade. Unidade: Reais (BRL)."),
    TX_CRESCIMENTO_YOY_PAGO OPTIONS(description="Taxa percentual de crescimento anual do valor pago comparado ao ano anterior (Year-over-Year)."),
    DH_PROCESSAMENTO OPTIONS(description="Timestamp UTC de materialização do Data Mart Gold de origem."),
    DS_RESUMO_SEMANTICO OPTIONS(description="Narrativa em linguagem natural formatada para indexação vetorial e RAG no Vertex AI. Sintetiza a destinação setorial, representatividade e evolução temporal.")
)
OPTIONS(
    description="[Visão Semântica p/ IA] Investimentos de emendas parlamentares alocados por políticas públicas, funções e subfunções setoriais de governo. Grão da linha: [DT_ANO, CD_FUNCAO, DS_FUNCAO, CD_SUBFUNCAO, DS_SUBFUNCAO, DS_TIPO_EMENDA]. Responde perguntas sobre áreas que mais receberam recursos (Saúde, Educação, etc.), share orçamentário e tendências de crescimento YoY.",
    labels=[("camada", "gold_semantica"), ("consumidor", "vertex_ai_gemini"), ("dominio", "politicas_publicas")]
)
AS
SELECT 
    DT_ANO,
    CD_FUNCAO,
    DS_FUNCAO,
    CD_SUBFUNCAO,
    DS_SUBFUNCAO,
    DS_TIPO_EMENDA,
    CASE 
        WHEN TX_CRESCIMENTO_YOY_PAGO IS NULL THEN 'SEM_BASE_COMPARACAO_ANTERIOR'
        WHEN TX_CRESCIMENTO_YOY_PAGO > 5.0 THEN 'CRESCIMENTO'
        WHEN TX_CRESCIMENTO_YOY_PAGO < -5.0 THEN 'RETRACAO'
        ELSE 'ESTAVEL'
    END AS DS_TENDENCIA_YOY,
    QTD_EMENDAS,
    VL_EMPENHADO,
    VL_LIQUIDADO,
    VL_PAGO,
    TX_EXECUCAO,
    TX_LIQUIDACAO,
    PC_REPRESENTATIVIDADE_EMPENHO,
    PC_REPRESENTATIVIDADE_PAGO,
    VL_PAGO_ANO_ANTERIOR,
    TX_CRESCIMENTO_YOY_PAGO,
    DH_PROCESSAMENTO,
    CONCAT(
        'Em ', CAST(DT_ANO AS STRING), ', a política pública na Função ', DS_FUNCAO, 
        ' (Subfunção: ', DS_SUBFUNCAO, ', Tipo: ', DS_TIPO_EMENDA, 
        ') recebeu ', CAST(QTD_EMENDAS AS STRING), ' emenda(s), somando R$ ', 
        FORMAT("%'.2f", VL_EMPENHADO), ' empenhados e R$ ', 
        FORMAT("%'.2f", VL_PAGO), ' pagos (Taxa de Execução: ', 
        IFNULL(CAST(TX_EXECUCAO AS STRING), '0.00'), '%). A área representou ', 
        IFNULL(CAST(PC_REPRESENTATIVIDADE_PAGO AS STRING), '0.00'), 
        '% de todo o valor pago em emendas no ano, com tendência anual de ',
        CASE 
            WHEN TX_CRESCIMENTO_YOY_PAGO IS NULL THEN 'Sem base de comparação anterior'
            WHEN TX_CRESCIMENTO_YOY_PAGO > 5.0 THEN CONCAT('Crescimento (+', CAST(TX_CRESCIMENTO_YOY_PAGO AS STRING), '%)')
            WHEN TX_CRESCIMENTO_YOY_PAGO < -5.0 THEN CONCAT('Retração (', CAST(TX_CRESCIMENTO_YOY_PAGO AS STRING), '%)')
            ELSE CONCAT('Estabilidade (', CAST(TX_CRESCIMENTO_YOY_PAGO AS STRING), '%)')
        END, '.'
    ) AS DS_RESUMO_SEMANTICO
FROM `project-f2711ebc-82b0-49cb-b84.3_gold.tbl_politicas_publicas`;
