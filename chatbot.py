import os
import re
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from langchain_community.utilities import SQLDatabase
from sqlalchemy import text

load_dotenv()

# 1. Base de Dados
db_uri = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@localhost:5432/{os.getenv('DB_NAME')}"
)
db = SQLDatabase.from_uri(db_uri)

# 2. Cliente HF — provider="auto" escolhe o melhor provider disponível
#    (Cerebras, SambaNova, Together AI, etc.) com free tier
client = InferenceClient(
    provider="auto",
    api_key=os.getenv("HUGGINGFACE_API_TOKEN"),
)
MODEL = "meta-llama/Llama-3.1-8B-Instruct" 

# 3. Carregar schema do ficheiro externo
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")
with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
    SCHEMA = f.read()

def gerar_sql(pergunta: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a PostgreSQL expert. Given a question and a database schema, "
                    "output ONLY a valid SQL query inside a ```sql block. No explanations.\n\n"
                    "Important rules:\n"
                    "- For text fields (names, descriptions, emails), ALWAYS use ILIKE '%value%' instead of =\n"
                    "- Never use exact match (=) for text searches\n\n"
                    f"Schema:\n{SCHEMA}"
                ),
            },
            {
                "role": "user",
                "content": f"Question: {pergunta}\n\nSQL query:"
            }
        ],
        max_tokens=256,
        temperature=0.05,
    )
    return response.choices[0].message.content

def extrair_sql(texto: str):
    match = re.search(r"```sql\s*(.*?)```", texto, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"(SELECT|WITH)\s.+?;", texto, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return None

def executar_query(sql: str):
    engine = db._engine
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        colunas = list(result.keys())
        linhas = result.fetchall()
    return colunas, linhas

def formatar_tabela(colunas, linhas) -> str:
    if not linhas:
        return "(sem resultados)"
    col_widths = [
        max(len(str(c)), max((len(str(r[i])) for r in linhas), default=0))
        for i, c in enumerate(colunas)
    ]
    def row_str(row):
        return " | ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(row))
    sep = "-+-".join("-" * w for w in col_widths)
    return f"{row_str(colunas)}\n{sep}\n" + "\n".join(row_str(r) for r in linhas)

def perguntar(pergunta: str) -> dict:
    try:
        raw = gerar_sql(pergunta)
        sql = extrair_sql(raw)

        if not sql:
            return {"sql": None, "colunas": [], "linhas": [], "resposta": raw, "erro": None}

        colunas, linhas = executar_query(sql)
        tabela_txt = "\n".join([" | ".join(str(v) for v in row) for row in linhas]) or "(sem resultados)"

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer in European Portuguese, concisely."},
                {"role": "user", "content": f"Pergunta: {pergunta}\nResultado:\n{tabela_txt}\n\nResponde em Português."}
            ],
            max_tokens=256,
            temperature=0.3,
        )
        resposta = resp.choices[0].message.content
        return {"sql": sql, "colunas": colunas, "linhas": linhas, "resposta": resposta, "erro": None}

    except Exception as e:
        return {"sql": None, "colunas": [], "linhas": [], "resposta": "", "erro": str(e)}


if __name__ == "__main__":
    print(f"--- Chatbot SQL · {MODEL} ---")
    print("(escreve 'sair' para terminar)\n")
    while True:
        try:
            pergunta = input("O que queres saber? ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not pergunta or pergunta.lower() == "sair":
            break
        resultado = perguntar(pergunta)
        if resultado["erro"]:
            print(f"\n❌ Erro: {resultado['erro']}\n")
        else:
            if resultado["sql"]:
                print(f"\n🔍 SQL:\n{resultado['sql']}\n")
            print(f"💬 {resultado['resposta']}\n")