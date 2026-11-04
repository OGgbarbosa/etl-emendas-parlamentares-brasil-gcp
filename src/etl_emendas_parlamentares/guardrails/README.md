# 🛡️ Guardrails do Observatório de Emendas Parlamentares

Este diretório contém os componentes de governança, segurança e validação de dados para as interações de Inteligência Artificial (Vertex AI, Gemini e BigQuery RAG).

---

## 🏛️ Arquitetura de Guardrails

O sistema de guardrails atua em três camadas defensivas:

```
[ Usuário ] 
     │
     ▼
[ 1. Input Guards ] ────────► Bloqueio de Prompt Injection, SQLi e Overflow
     │
     ▼
[ 2. BigQuery & SQL Guards ] ──► Restrição a DQL (SELECT/WITH), anti-NaN e limites de custo
     │
     ▼
[ 3. Output Guards ] ───────► Anti-Hallucination, Anti-NaN, Sanitização de Credenciais
     │
     ▼
[ Interface Streamlit ]
```

---

## 📦 Módulos Disponíveis

1. **`input_guards.py`**:
   - `validar_prompt_usuario(prompt: str) -> ValidacaoEntrada`
   - Valida tamanho, tentativas de jailbreak/injeção e escopo temático orçamentário.

2. **`output_guards.py`**:
   - `validar_resposta_ia(resposta: str, contexto_tabela=None) -> ValidacaoSaida`
   - Impede que valores nulos como `nan`, `null` ou `none` cheguem ao usuário, substituindo por narrativas auditadas factíveis.
   - Detecta e mascara qualquer vazamento acidental de tokens ou credenciais.

3. **`sql_guards.py`**:
   - `validar_consulta_sql(sql: str) -> bool`
   - Assegura que apenas consultas de leitura (DQL) sejam encaminhadas ao BigQuery.

---

## 🚀 Como Utilizar

```python
from etl_emendas_parlamentares.guardrails import validar_prompt_usuario, validar_resposta_ia

# 1. Validação do Prompt de Entrada
validacao_in = validar_prompt_usuario(prompt_usuario)
if not validacao_in.valido:
    return {"texto": f"Aviso de Segurança: {validacao_in.motivo}", "tipo": "bloqueio"}

# 2. Execução da Consulta e Geração da Resposta
resposta_bruta = executar_consulta_semantica(validacao_in.prompt_higienizado)

# 3. Validação da Resposta de Saída
validacao_out = validar_resposta_ia(resposta_bruta)
texto_final = validacao_out.texto_filtrado
```
