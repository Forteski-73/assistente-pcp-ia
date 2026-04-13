import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Novos caminhos de importação corrigidos
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# -------------------------
# CONFIG BANCO
# -------------------------

user = os.getenv("DB_USER")
password = quote_plus(os.getenv("DB_PASSWORD"))
host = os.getenv("DB_HOST")
database = os.getenv("DB_NAME")

# Certifique-se de que as variáveis de ambiente acima estão no seu arquivo .env
db = SQLDatabase.from_uri(
    f"mysql+pymysql://{user}:{password}@{host}/{database}",
    engine_args={
        "pool_pre_ping": True,
        "pool_recycle": 3600
    }
)

# -------------------------
# MODELO IA
# -------------------------

# Dica: Verifique se gpt-4.1 é o nome exato liberado na sua API. 
# Caso dê erro de 'model_not_found', altere para "gpt-4o".
llm = ChatOpenAI(
    #model="gpt-4.1-mini",#
    model="gpt-4o",
    temperature=0
)

# -------------------------
# PROMPT GERADOR DE SQL
# -------------------------

sql_prompt = PromptTemplate.from_template("""
Você é um especialista em SQL que retorna APENAS código.
Não escreva explicações. Não escreva "Aqui está a query".
Não use blocos de Markdown como ```sql.
Retorne apenas o comando SELECT puro para MariaDB.

REGRAS CRÍTICAS:
1. Use APENAS os nomes de colunas que aparecem explicitamente no schema abaixo.
2. Se não encontrar uma coluna de "data" ou "data_cadastro", verifique se existem colunas como 'update', 'timestamp' ou 'id' (para ordenar pelos últimos IDs).
3. Não invente colunas como 'created_at'.
4. Retorne apenas o código SQL puro.

Schema do banco:
{schema}

Pergunta:
{question}

SQL:
""")

# -------------------------
# PROMPT DE RESPOSTA
# -------------------------

answer_prompt = PromptTemplate.from_template("""
Você é um assistente de planejamento de produção. 
Com base na pergunta do usuário e no resultado da consulta SQL do nosso banco de dados, 
explique o que os dados significam de forma clara e profissional.

Regras:
1. Seja extremamente conciso.
2. Se o resultado for um número, responda apenas o número ou uma frase curta.
3. Não faça introduções como "Com base nos dados..." ou "O resultado da consulta é...".
4. Vá direto ao ponto.

Pergunta do usuário:
{question}

Resultado da consulta SQL:
{result}

Explique o resultado em português:
""")

# -------------------------
# LOOP CHAT
# -------------------------

print("--- Assistente de PCP Inteligente Iniciado ---")
print("Digite 'S' para encerrar.")

while True:
    pergunta = input("\nFale com a IA: ")

    if pergunta.lower() == "s":
        break

    try:
        # 1. Obter informações das tabelas (Schema)
        schema = db.get_table_info()

        # 2. Gerar a Query SQL
        # Adicionamos o StrOutputParser para garantir que o resultado seja uma string limpa
        sql_chain = sql_prompt | llm | StrOutputParser()
        
        sql_bruto = sql_chain.invoke({
            "question": pergunta,
            "schema": schema
        })

        # Limpeza simples caso a IA coloque blocos de código markdown
        sql_limpo = sql_bruto.replace("```sql", "").replace("```", "").strip()
        print("\n")
        #print("\n[DEBUG] SQL gerado:")
        #print(sql_limpo)

        # 3. Executar no Banco de Dados
        result = db.run(sql_limpo)

        # 4. Gerar a resposta final para o humano
        answer_chain = answer_prompt | llm | StrOutputParser()
        
        resposta = answer_chain.invoke({
            "question": pergunta,
            "result": result
        })

        print("\n******************************************************* R E S P O S T A:\n")
        print(resposta)

    except Exception as e:
        print(f"\nErro ao processar a solicitação: {e}")