CREATE OR REPLACE TABLE `project-f2711ebc-82b0-49cb-b84.3_gold.tbl_politicas_publicas`
CLUSTER BY DT_ANO, DS_FUNCAO, DS_TIPO_EMENDA
AS

-- 1. Agregação no grão setorial [Ano, Função, Subfunção, Tipo de Emenda]
WITH agregacao_setorial AS (
    SELECT 
        ano_emenda AS DT_ANO,
        COALESCE(codigo_funcao, -1) AS CD_FUNCAO,
        COALESCE(NULLIF(TRIM(nome_funcao), ''), 'NÃO INFORMADO') AS DS_FUNCAO,
        COALESCE(codigo_subfuncao, -1) AS CD_SUBFUNCAO,
        COALESCE(NULLIF(TRIM(nome_subfuncao), ''), 'NÃO INFORMADO') AS DS_SUBFUNCAO,
        tipo_emenda AS DS_TIPO_EMENDA,

        -- Quantitativo de emendas únicas no portfólio setorial
        COUNT(DISTINCT codigo_da_emenda) AS QTD_EMENDAS,

        -- Volumes Orçamentários Principais
        ROUND(SUM(valor_empenhado), 2) AS VL_EMPENHADO,
        ROUND(SUM(valor_liquidado), 2) AS VL_LIQUIDADO,
        ROUND(SUM(valor_pago), 2) AS VL_PAGO

    FROM `project-f2711ebc-82b0-49cb-b84.2_silver.fato_emendas`
    GROUP BY 1, 2, 3, 4, 5, 6
),

-- 2. Cálculo dos totais anuais para representatividade e métricas de janela temporal (YoY)
metricas_temporais AS (
    SELECT 
        *,
        -- Totais anuais globais para cálculo de share financeiro
        SUM(VL_EMPENHADO) OVER (PARTITION BY DT_ANO) AS VL_TOTAL_EMPENHADO_ANO,
        SUM(VL_PAGO) OVER (PARTITION BY DT_ANO) AS VL_TOTAL_PAGO_ANO,

        -- Dados do ano imediatamente anterior para a mesma política e tipo de emenda
        LAG(DT_ANO) OVER (
            PARTITION BY CD_FUNCAO, CD_SUBFUNCAO, DS_TIPO_EMENDA 
            ORDER BY DT_ANO
        ) AS DT_ANO_ANTERIOR,
        LAG(VL_PAGO) OVER (
            PARTITION BY CD_FUNCAO, CD_SUBFUNCAO, DS_TIPO_EMENDA 
            ORDER BY DT_ANO
        ) AS VL_PAGO_ANO_ANTERIOR

    FROM agregacao_setorial
)

-- 3. Consolidação Final dos Indicadores Analíticos
SELECT 
    DT_ANO,
    CD_FUNCAO,
    DS_FUNCAO,
    CD_SUBFUNCAO,
    DS_SUBFUNCAO,
    DS_TIPO_EMENDA,
    QTD_EMENDAS,

    -- Valores Orçamentários
    VL_EMPENHADO,
    VL_LIQUIDADO,
    VL_PAGO,

    -- Indicadores de Eficiência no Ciclo da Despesa (%)
    ROUND(SAFE_DIVIDE(VL_PAGO, VL_EMPENHADO) * 100, 2) AS TX_EXECUCAO,
    ROUND(SAFE_DIVIDE(VL_LIQUIDADO, VL_EMPENHADO) * 100, 2) AS TX_LIQUIDACAO,

    -- Representatividade Setorial no Orçamento Total de Emendas do Ano (%)
    ROUND(SAFE_DIVIDE(VL_EMPENHADO * 100.0, VL_TOTAL_EMPENHADO_ANO), 2) AS PC_REPRESENTATIVIDADE_EMPENHO,
    ROUND(SAFE_DIVIDE(VL_PAGO * 100.0, VL_TOTAL_PAGO_ANO), 2) AS PC_REPRESENTATIVIDADE_PAGO,

    -- Evolução Anual dos Investimentos Setoriais (YoY)
    VL_PAGO_ANO_ANTERIOR,
    CASE 
        WHEN DT_ANO_ANTERIOR = DT_ANO - 1 THEN 
            ROUND(SAFE_DIVIDE((VL_PAGO - VL_PAGO_ANO_ANTERIOR) * 100.0, VL_PAGO_ANO_ANTERIOR), 2)
        ELSE NULL 
    END AS TX_CRESCIMENTO_YOY_PAGO,

    -- Metadados de auditoria e carga
    CURRENT_TIMESTAMP() AS DH_PROCESSAMENTO

FROM metricas_temporais;