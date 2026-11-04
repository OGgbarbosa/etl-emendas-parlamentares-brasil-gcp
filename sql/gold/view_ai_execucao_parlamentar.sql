CREATE OR REPLACE VIEW `project-f2711ebc-82b0-49cb-b84.3_gold.view_ai_execucao_parlamentar` (
    DT_ANO OPTIONS(description="Ano de referência do orçamento da emenda parlamentar (exercício fiscal). Tipo: INT64."),
    CD_AUTOR OPTIONS(description="Código numérico único de identificação do autor/parlamentar na CGU/SIAFI. Sentinela: -1 indica ausência de código na fonte (ex.: RP9 Relator, Comissão RP8 ou dados legados de 2014)."),
    DS_AUTOR OPTIONS(description="Nome completo do autor da emenda (ex.: Deputado, Senador, Bancada, Comissão ou Relator Geral)."),
    DS_TIPO_EMENDA OPTIONS(description="Modalidade orçamentária da emenda: INDIVIDUAL, BANCADA, COMISSAO ou RELATOR (RP9)."),
    SG_UF OPTIONS(description="Sigla da Unidade Federativa (UF) do autor ou estado de atuação parlamentar (ex.: SP, RJ, NACI para âmbito nacional)."),
    FL_AUTOR_IDENTIFICADO OPTIONS(description="Flag booleana indicando se o autor possui código individualizado válido (TRUE) ou se é registro genérico/não codificado como RP9/Comissão/legado (FALSE)."),
    QTD_EMENDAS OPTIONS(description="Quantidade de emendas orçamentárias distintas associadas a este autor, ano e modalidade."),
    VL_EMPENHADO OPTIONS(description="Valor total empenhado no ano pelo autor na modalidade (recurso reservado no orçamento). Unidade: Reais (BRL). Aditivo entre linhas."),
    VL_LIQUIDADO OPTIONS(description="Valor total liquidado no ano (bens entregues ou serviços comprovadamente executados). Unidade: Reais (BRL). Aditivo entre linhas."),
    VL_PAGO OPTIONS(description="Valor total efetivamente pago no exercício fiscal. Unidade: Reais (BRL). Aditivo entre linhas."),
    VL_RESTOS_SALDO_A_PAGAR OPTIONS(description="Saldo líquido a pagar de Restos a Pagar (Inscritos - Cancelados - Pagos). Unidade: Reais (BRL)."),
    VL_RESTOS_INSCRITOS OPTIONS(description="Total de Restos a Pagar inscritos em anos anteriores para este autor/modalidade. Unidade: Reais (BRL)."),
    VL_RESTOS_CANCELADOS OPTIONS(description="Total de Restos a Pagar cancelados (recursos descompromissados). Unidade: Reais (BRL)."),
    VL_RESTOS_PAGOS OPTIONS(description="Total de Restos a Pagar efetivamente quitados. Unidade: Reais (BRL)."),
    TX_EXECUCAO OPTIONS(description="Taxa de execução percentual (VL_PAGO / VL_EMPENHADO * 100). Regra para IA: NUNCA use AVG(TX_EXECUCAO) ao agrupar; recalcule com ROUND(SAFE_DIVIDE(SUM(VL_PAGO), SUM(VL_EMPENHADO)) * 100, 2)."),
    TX_LIQUIDACAO OPTIONS(description="Taxa de liquidação percentual (VL_LIQUIDADO / VL_EMPENHADO * 100). Regra para IA: NUNCA use AVG(TX_LIQUIDACAO) ao agrupar; recalcule com ROUND(SAFE_DIVIDE(SUM(VL_LIQUIDADO), SUM(VL_EMPENHADO)) * 100, 2)."),
    DH_PROCESSAMENTO OPTIONS(description="Timestamp UTC de materialização do Data Mart Gold de origem."),
    DS_RESUMO_SEMANTICO OPTIONS(description="Narrativa em linguagem natural formatada para indexação vetorial e RAG no Vertex AI. Sintetiza parlamentar, ano, modalidade, volumes e taxa de execução.")
)
OPTIONS(
    description="[Visão Semântica p/ IA] Execução orçamentária por parlamentar, ano, UF e tipo de emenda. Grão da linha: [DT_ANO, CD_AUTOR, DS_AUTOR, DS_TIPO_EMENDA, SG_UF]. Responde perguntas sobre volume empenhado/pago por deputado/senador, taxa de execução e saldo de restos a pagar.",
    labels=[("camada", "gold_semantica"), ("consumidor", "vertex_ai_gemini"), ("dominio", "execucao_parlamentar")]
)
AS
SELECT 
    DT_ANO,
    CD_AUTOR,
    DS_AUTOR,
    DS_TIPO_EMENDA,
    SG_UF,
    (CD_AUTOR != -1) AS FL_AUTOR_IDENTIFICADO,
    QTD_EMENDAS,
    VL_EMPENHADO,
    VL_LIQUIDADO,
    VL_PAGO,
    VL_RESTOS_SALDO_A_PAGAR,
    VL_RESTOS_INSCRITOS,
    VL_RESTOS_CANCELADOS,
    VL_RESTOS_PAGOS,
    TX_EXECUCAO,
    TX_LIQUIDACAO,
    DH_PROCESSAMENTO,
    CONCAT(
        'No exercício de ', CAST(DT_ANO AS STRING), ', o parlamentar/autor ', DS_AUTOR, 
        ' (UF: ', SG_UF, ', Código: ', CAST(CD_AUTOR AS STRING), ', Tipo: ', DS_TIPO_EMENDA, 
        ') destinou ', CAST(QTD_EMENDAS AS STRING), ' emenda(s), somando R$ ', 
        FORMAT("%'.2f", VL_EMPENHADO), ' empenhados, R$ ', 
        FORMAT("%'.2f", VL_LIQUIDADO), ' liquidados e R$ ', 
        FORMAT("%'.2f", VL_PAGO), ' pagos (Taxa de Execução: ', 
        IFNULL(CAST(TX_EXECUCAO AS STRING), '0.00'), '%). Saldo restante a pagar de Restos a Pagar: R$ ', 
        FORMAT("%'.2f", VL_RESTOS_SALDO_A_PAGAR), '.'
    ) AS DS_RESUMO_SEMANTICO
FROM `project-f2711ebc-82b0-49cb-b84.3_gold.tbl_execucao_parlamentar`;
