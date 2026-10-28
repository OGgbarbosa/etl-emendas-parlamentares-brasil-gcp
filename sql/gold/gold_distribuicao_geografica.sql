CREATE OR REPLACE TABLE `project-f2711ebc-82b0-49cb-b84.3_gold.tbl_distribuicao_geografica`
CLUSTER BY DT_ANO, SG_REGIAO, SG_UF, CD_MUNICIPIO_IBGE
AS

-- 1. Totalizar os convênios por código de emenda (grão 1:1 por emenda para prevenir fan-out)
WITH convenios_por_emenda AS (
    SELECT 
        codigo_da_emenda,
        COUNT(DISTINCT numero_convenio) AS qtd_convenios,
        SUM(valor_convenio) AS total_valor_convenio
    FROM `project-f2711ebc-82b0-49cb-b84.2_silver.fato_convenios`
    GROUP BY codigo_da_emenda
),

-- 2. Consolidar as dotações de emendas por emenda e território
emendas_territorio AS (
    SELECT 
        ano_emenda AS DT_ANO,
        regiao AS SG_REGIAO,
        uf AS SG_UF,
        municipio AS DS_MUNICIPIO,
        codigo_municipio_ibge AS CD_MUNICIPIO_IBGE,
        codigo_da_emenda,
        SUM(valor_empenhado) AS vl_empenhado,
        SUM(valor_liquidado) AS vl_liquidado,
        SUM(valor_pago) AS vl_pago
    FROM `project-f2711ebc-82b0-49cb-b84.2_silver.fato_emendas`
    GROUP BY 1, 2, 3, 4, 5, 6
),

-- 3. Cruzar emendas com o resumo de convênios sem risco de explosão cartesiana
emendas_com_convenios AS (
    SELECT 
        e.DT_ANO,
        e.SG_REGIAO,
        e.SG_UF,
        e.DS_MUNICIPIO,
        e.CD_MUNICIPIO_IBGE,
        e.codigo_da_emenda,
        e.vl_empenhado,
        e.vl_liquidado,
        e.vl_pago,
        COALESCE(c.qtd_convenios, 0) AS qtd_convenios,
        COALESCE(c.total_valor_convenio, 0.0) AS vl_convenio
    FROM emendas_territorio e
    LEFT JOIN convenios_por_emenda c ON e.codigo_da_emenda = c.codigo_da_emenda
)

-- 4. Agrupamento final no grão geográfico [Ano, Região, UF, Município, Âmbito]
SELECT 
    DT_ANO,
    SG_REGIAO,
    SG_UF,
    DS_MUNICIPIO,
    CD_MUNICIPIO_IBGE,

    -- Classificação da esfera governamental / destinação
    CASE 
        WHEN CD_MUNICIPIO_IBGE > 0 THEN 'MUNICIPAL'
        WHEN UPPER(DS_MUNICIPIO) = 'ESTADUAL' OR (CD_MUNICIPIO_IBGE < 0 AND SG_UF != 'NACI') THEN 'ESTADUAL'
        ELSE 'NACIONAL_REGIONAL'
    END AS DS_AMBITO_GEOGRAFICO,

    -- Quantitativos
    COUNT(DISTINCT codigo_da_emenda) AS QTD_EMENDAS,
    SUM(qtd_convenios) AS QTD_CONVENIOS,

    -- Valores Orçamentários Consolidados (Zero Duplicação)
    ROUND(SUM(vl_empenhado), 2) AS VL_EMPENHADO,
    ROUND(SUM(vl_liquidado), 2) AS VL_LIQUIDADO,
    ROUND(SUM(vl_pago), 2) AS VL_PAGO,
    ROUND(SUM(vl_convenio), 2) AS VL_CONVENIO,

    -- Indicadores Analíticos
    ROUND(SAFE_DIVIDE(SUM(vl_pago), COUNT(DISTINCT codigo_da_emenda)), 2) AS TKM_PAGO_POR_EMENDA,
    ROUND(SAFE_DIVIDE(SUM(vl_pago), SUM(vl_empenhado)) * 100, 2) AS TX_EXECUCAO,

    -- Metadados de auditoria e carga
    CURRENT_TIMESTAMP() AS DH_PROCESSAMENTO

FROM emendas_com_convenios
GROUP BY 1, 2, 3, 4, 5, 6;
