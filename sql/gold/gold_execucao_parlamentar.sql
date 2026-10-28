CREATE OR REPLACE TABLE 
`project-f2711ebc-82b0-49cb-b84.3_gold.tbl_execucao_parlamentar`

CLUSTER BY DT_ANO, CD_AUTOR, SG_UF, DS_TIPO_EMENDA

AS

SELECT 
ano_emenda as DT_ANO
,codigo_autor as CD_AUTOR
,nome_autor as DS_AUTOR
,tipo_emenda as DS_TIPO_EMENDA
,uf as SG_UF

-- Quantitativo de emendas únicas
,COUNT(DISTINCT codigo_da_emenda) as QTD_EMENDAS

-- Execução Orçamentária Principal
,ROUND(SUM(valor_empenhado),2) as VL_EMPENHADO 
,ROUND(SUM(valor_liquidado),2) as VL_LIQUIDADO
,ROUND(SUM(valor_pago),2) as VL_PAGO

-- Saldo pendente que ainda resta a pagar: Inscrito - Cancelado - Pago
,ROUND(SUM(
    COALESCE(valor_restos_a_pagar_inscritos, 0)
    - COALESCE(valor_restos_a_pagar_cancelados, 0)
    - COALESCE(valor_restos_a_pagar_pagos, 0)
),2) AS VL_RESTOS_SALDO_A_PAGAR

-- Restos a Pagar (Auditoria Contábil Precisa)
,ROUND(SUM(valor_restos_a_pagar_inscritos),2) as VL_RESTOS_INSCRITOS
,ROUND(SUM(valor_restos_a_pagar_cancelados),2) as VL_RESTOS_CANCELADOS
,ROUND(SUM(valor_restos_a_pagar_pagos),2) as VL_RESTOS_PAGOS

-- Indicadores de Eficiência (%)
,ROUND(SAFE_DIVIDE(SUM(valor_pago),SUM(valor_empenhado)) * 100,2) AS TX_EXECUCAO
,ROUND(SAFE_DIVIDE(SUM(valor_liquidado), SUM(valor_empenhado)) * 100,2) as TX_LIQUIDACAO

-- Metadados de carga
,CURRENT_TIMESTAMP() AS DH_PROCESSAMENTO

FROM `project-f2711ebc-82b0-49cb-b84.2_silver.fato_emendas` 

GROUP BY 1,2,3,4,5