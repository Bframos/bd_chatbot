# EcommerceDB Chatbot

A Text-to-SQL chatbot that answers natural language questions about an ecommerce PostgreSQL database. Built with Streamlit, Hugging Face, Redis, and sqlglot.

## Architecture

```
User
 │
 ▼
Streamlit (frontend)
 │
 ├──► Redis (cache.py)
 │     └── cache hit → return immediately
 │
 └──► chatbot.py
       ├──► Hugging Face API (Llama-3.1-8B) → generates SQL
       ├──► sql_validator.py (sqlglot) → blocks unsafe queries
       └──► PostgreSQL → executes query → returns rows
```

## Features

- **Natural language to SQL** — ask questions in plain English, get answers from the database
- **Conversation memory** — the model remembers the last 5 exchanges for contextual follow-ups
- **Redis caching** — repeated questions are answered instantly without calling the LLM
- **SQL validation** — sqlglot parses and blocks any non-SELECT statement (DROP, DELETE, UPDATE, etc.)
- **Fuzzy text search** — uses ILIKE for partial text matching on product names, emails, etc.
- **Tie handling** — uses DENSE_RANK() instead of LIMIT 1 to correctly handle tied results

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| LLM | Hugging Face Inference API (Llama-3.1-8B-Instruct) |
| Cache | Redis 7 |
| Database | PostgreSQL 16 |
| SQL validation | sqlglot |
| CI | GitHub Actions + ruff |

## Project Structure

```
bd_chatbot/
├── .github/
│   └── workflows/
│       └── ci.yml          # CI pipeline (lint)
├── chatbot.py              # Core logic: generate_sql, ask()
├── cache.py                # Redis cache layer
├── sql_validator.py        # SQL safety validation
├── streamlit_app.py        # Streamlit frontend
├── schema.sql              # Database schema (LLM context)
├── init.sql                # Database seed data
├── docker-compose.yml      # PostgreSQL + Redis + RedisInsight
├── pyproject.toml          # Ruff configuration
├── requirements.txt        # Python dependencies
└── .env.example            # Environment variables template
```

## Getting Started

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Hugging Face account + API token ([huggingface.co/settings/tokens](https://huggingface.co/settings/tokens))
  - Token must have **"Make calls to Inference Providers"** permission

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/bd_chatbot.git
cd bd_chatbot

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your HUGGINGFACE_API_TOKEN

# 5. Start the database and Redis
docker compose up -d

# 6. Run the chatbot
streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### Environment Variables

```env
DB_USER=admin
DB_PASSWORD=admin
DB_NAME=ecommerce_db
HUGGINGFACE_API_TOKEN=hf_...
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_TTL=3600        # cache TTL in seconds (default: 1 hour)
```

## Example Questions

```
Which products have less than 20 units in stock?
Which customer spent the most in total?
How many sales were made per category?
List the 3 best-selling products.
What is the most expensive product in the Electronics category?
How many transactions were made last month?
```

## Design Decisions

**Cache by question, not by SQL**
The bottleneck is the LLM call, not the database query. Caching by question avoids the LLM entirely on a cache hit. The trade-off is that semantically equivalent questions with different wording won't share a cache entry — acceptable given the latency gain.

**sqlglot over a keyword blacklist**
A blacklist (`if 'DROP' in sql`) can be bypassed with mixed casing (`DrOp`) or SQL comments (`DR--\nOP`). sqlglot parses the SQL properly and checks the statement type, making it significantly harder to bypass.

**ILIKE over exact match**
User queries like "macbook" should match "MacBook Air M2". Using `ILIKE '%value%'` for all text field filters handles partial and case-insensitive matches without requiring semantic search infrastructure.

**Conversation memory (last 10 messages)**
Passing the full conversation history would exceed the context window for long sessions and increase latency. Limiting to the last 10 messages (5 exchanges) keeps contextual follow-ups working while controlling token usage.

## Monitoring

RedisInsight is available at [http://localhost:5540](http://localhost:5540) to inspect cache keys, TTLs, and memory usage.

Connect with:
- **Host**: `redis`
- **Port**: `6379`

## CI Pipeline

On every push to `main`, GitHub Actions runs:

```
ruff check .   # linting and import ordering
```
