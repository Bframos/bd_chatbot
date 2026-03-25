import os
import re

from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from langchain_community.utilities import SQLDatabase
from sqlalchemy import text
import sql_validator


import cache

load_dotenv()

# 1. Database configuration
db_uri = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@localhost:5432/{os.getenv('DB_NAME')}"
)
db = SQLDatabase.from_uri(db_uri)
#======================================================================================================================


# 2. HF client — provider="auto" picks the best available provider
client = InferenceClient(
    provider="auto",
    api_key=os.getenv("HUGGINGFACE_API_TOKEN"),
)
MODEL = "meta-llama/Llama-3.1-8B-Instruct"
#======================================================================================================================


# 3. Load schema from external file
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")
with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
    SCHEMA = f.read()
#======================================================================================================================


def generate_sql(question: str, history: list = []) -> str:
    # Build conversation history for the model
    # Only include user questions and assistant SQL responses
    messages = [
        {
            "role": "system",
            "content": (
                "You are a PostgreSQL expert. Given a question and a database schema, "
                "output ONLY a valid SQL query inside a ```sql block. No explanations.\n\n"
                "Important rules:\n"
                "- For text fields (names, descriptions, emails), ALWAYS use ILIKE '%value%' instead of =\n"
                "- Never use exact match (=) for text searches\n"
                "- When the user asks for 'the most/least/best/worst', never use LIMIT 1 — instead use DENSE_RANK() to handle ties correctly\n\n"
                f"Schema:\n{SCHEMA}"
            ),
        },
    ]

    # Add conversation history — last 5 exchanges max
    for msg in history[-10:]:  # 10 = 5 exchanges (user + assistant each)
        if msg["role"] in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current question
    messages.append({"role": "user", "content": f"Question: {question}\n\nSQL query:"})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=256,
        temperature=0.05,
    )
    return response.choices[0].message.content


def extract_sql(text: str):
    match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"(SELECT|WITH)\s.+?;", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return None


def execute_query(sql: str):
    engine = db._engine
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchall()
    return columns, rows


def format_table(columns, rows) -> str:
    if not rows:
        return "(no results)"
    col_widths = [
        max(len(str(c)), max((len(str(r[i])) for r in rows), default=0))
        for i, c in enumerate(columns)
    ]
    def row_str(row):
        return " | ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(row))
    sep = "-+-".join("-" * w for w in col_widths)
    return f"{row_str(columns)}\n{sep}\n" + "\n".join(row_str(r) for r in rows)


def ask(question: str, history: list = []) -> dict:
    cached = cache.get(question)
    if cached:
        cached["from_cache"] = True
        return cached

    try:
        raw = generate_sql(question, history)  # pass history here
        sql = extract_sql(raw)

        if not sql:
            return {"sql": None, "columns": [], "rows": [], "answer": raw, "error": None, "from_cache": False}

        try:
            sql_validator.validate(sql)
        except sql_validator.UnsafeSQLError as e:
            return {"sql": sql, "columns": [], "rows": [], "answer": "", "error": str(e), "from_cache": False}

        columns, rows = execute_query(sql)
        table_txt = "\n".join([" | ".join(str(v) for v in row) for row in rows]) or "(no results)"

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer in English, concisely."},
                {"role": "user", "content": f"Question: {question}\nQuery result:\n{table_txt}\n\nAnswer the question clearly and directly."}
            ],
            max_tokens=256,
            temperature=0.3,
        )
        answer = resp.choices[0].message.content
        result = {"sql": sql, "columns": columns, "rows": rows, "answer": answer, "error": None, "from_cache": False}

        cache.set(question, result)
        return result

    except Exception as e:
        return {"sql": None, "columns": [], "rows": [], "answer": "", "error": str(e), "from_cache": False}

if __name__ == "__main__":
    print(f"--- SQL Chatbot · {MODEL} ---")
    print("(type 'exit' to quit)\n")
    while True:
        try:
            question = input("What do you want to know? ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not question or question.lower() == "exit":
            break
        result = ask(question)
        if result["error"]:
            print(f"\n❌ Error: {result['error']}\n")
        else:
            if result["sql"]:
                print(f"\n🔍 SQL:\n{result['sql']}\n")
            print(f"💬 {result['answer']}\n")