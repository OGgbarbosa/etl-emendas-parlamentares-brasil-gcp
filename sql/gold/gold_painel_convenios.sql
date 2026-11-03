CREATE OR REPLACE TABLE `project-f2711ebc-82b0-49cb-b84.3_gold.tbl_painel_convenios`
CLUSTER BY DT_ANO, SG_UF, DS_FUNCAO
AS

-- 1. Deduplicação no grão único do convênio para prevenir superestimação de valor financeiro
WITH convenios_unicos AS (
    SELECT 
        numero_convenio,
        COALESCE(EXTRACT(YEAR FROM data_publicacao_convenio), -1) AS DT_ANO,
        COALESCE(NULLIF(TRIM(localidade_classificada), ''), 'SEM INFORMAÇÃO') AS SG_UF,
        COALESCE(NULLIF(TRIM(convenente), ''), 'NÃO INFORMADO') AS DS_CONVENENTE,
        COALESCE(NULLIF(TRIM(nome_funcao), ''), 'NÃO INFORMADO') AS DS_FUNCAO,
        MAX(valor_convenio) AS valor_convenio,
        COUNT(DISTINCT codigo_da_emenda) AS qtd_emendas_no_convenio
    FROM `project-f2711ebc-82b0-49cb-b84.2_silver.fato_convenios`
    GROUP BY 1, 2, 3, 4, 5
)

-- 2. Agrupamento final no grão analítico do painel
SELECT 
    DT_ANO,
    SG_UF,
    DS_CONVENENTE,
    DS_FUNCAO,

    -- Quantitativos Consolidados
    COUNT(DISTINCT numero_convenio) AS QTD_CONVENIOS,
    SUM(qtd_emendas_no_convenio) AS QTD_EMENDAS_VINCULADAS,

    -- Valores Orçamentários Auditados (Zero Duplicação)
    ROUND(SUM(valor_convenio), 2) AS VL_TOTAL_CONVENIADO,
    ROUND(SAFE_DIVIDE(SUM(valor_convenio), COUNT(DISTINCT numero_convenio)), 2) AS TKM_VALOR_POR_CONVENIO,

    -- Metadados de carga
    CURRENT_TIMESTAMP() AS DH_PROCESSAMENTO

FROM convenios_unicos
GROUP BY 1, 2, 3, 4;

