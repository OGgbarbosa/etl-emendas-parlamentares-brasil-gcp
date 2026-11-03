CREATE OR REPLACE TABLE `project-f2711ebc-82b0-49cb-b84.3_gold.tbl_ranking_favorecidos`
CLUSTER BY DT_ANO, SG_UF_FAVORECIDO, DS_TIPO_FAVORECIDO, CD_FAVORECIDO
AS

-- 1. Agregação no grão anual por favorecido
WITH agregacao_favorecido_ano AS (
    SELECT 
        EXTRACT(YEAR FROM data_referencia) AS DT_ANO,
        COALESCE(NULLIF(TRIM(codigo_do_favorecido), ''), 'NÃO INFORMADO') AS CD_FAVORECIDO,
        COALESCE(NULLIF(TRIM(favorecido), ''), 'NÃO INFORMADO') AS DS_FAVORECIDO,
        COALESCE(NULLIF(TRIM(tipo_favorecido), ''), 'OUTROS') AS DS_TIPO_FAVORECIDO,
        COALESCE(NULLIF(TRIM(natureza_juridica), ''), 'NÃO INFORMADA') AS DS_NATUREZA_JURIDICA,
        COALESCE(NULLIF(TRIM(uf_favorecido), ''), 'SEM INFORMAÇÃO') AS SG_UF_FAVORECIDO,

        -- Valores no ano
        ROUND(SUM(valor_recebido), 2) AS VL_RECEBIDO_ANO,

        -- Relacionamento com parlamentares
        COUNT(DISTINCT codigo_do_autor_da_emenda) AS QTD_PARLAMENTARES_DISTINTOS_ANO,
        COUNT(DISTINCT codigo_da_emenda) AS QTD_EMENDAS_DISTINTAS_ANO,

        -- Recorrência e transações
        COUNT(DISTINCT data_referencia) AS QTD_MESES_COM_REPASSE,
        COUNT(*) AS QTD_TRANSFERENCIAS_RECEBIDAS,

        -- Datas no ano
        MIN(data_referencia) AS DT_PRIMEIRO_RECEBIMENTO_ANO,
        MAX(data_referencia) AS DT_ULTIMO_RECEBIMENTO_ANO

    FROM `project-f2711ebc-82b0-49cb-b84.2_silver.fato_favorecidos`
    GROUP BY 1, 2, 3, 4, 5, 6
)

-- 2. Métricas acumuladas históricas e janelas de contexto
SELECT 
    DT_ANO,
    CD_FAVORECIDO,
    DS_FAVORECIDO,
    DS_TIPO_FAVORECIDO,
    DS_NATUREZA_JURIDICA,
    SG_UF_FAVORECIDO,

    -- Métricas Financeiras Anuais e Acumuladas
    VL_RECEBIDO_ANO,
    ROUND(SUM(VL_RECEBIDO_ANO) OVER (
        PARTITION BY CD_FAVORECIDO 
        ORDER BY DT_ANO 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS VL_RECEBIDO_ACUMULADO_ATE_ANO,
    ROUND(SUM(VL_RECEBIDO_ANO) OVER (
        PARTITION BY CD_FAVORECIDO
    ), 2) AS VL_RECEBIDO_TOTAL_HISTORICO,

    -- Indicadores de Relacionamento
    QTD_PARLAMENTARES_DISTINTOS_ANO,
    QTD_EMENDAS_DISTINTAS_ANO,
    ROUND(SAFE_DIVIDE(VL_RECEBIDO_ANO, QTD_PARLAMENTARES_DISTINTOS_ANO), 2) AS TKM_RECEBIDO_POR_PARLAMENTAR,

    -- Recorrência de Repasses
    QTD_MESES_COM_REPASSE,
    QTD_TRANSFERENCIAS_RECEBIDAS,

    -- Marcos Temporais (Anual e Histórico Geral)
    DT_PRIMEIRO_RECEBIMENTO_ANO,
    DT_ULTIMO_RECEBIMENTO_ANO,
    MIN(DT_PRIMEIRO_RECEBIMENTO_ANO) OVER (PARTITION BY CD_FAVORECIDO) AS DT_PRIMEIRO_RECEBIMENTO_HISTORICO,
    MAX(DT_ULTIMO_RECEBIMENTO_ANO) OVER (PARTITION BY CD_FAVORECIDO) AS DT_ULTIMO_RECEBIMENTO_HISTORICO,

    -- Metadados de carga
    CURRENT_TIMESTAMP() AS DH_PROCESSAMENTO

FROM agregacao_favorecido_ano;
