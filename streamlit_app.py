import pandas as pd
import streamlit as st

from chatbot import MODEL, ask

# ── Page configuration ──
st.set_page_config(
    page_title="EcommerceDB Chatbot",
    page_icon="🗄️",
    layout="wide",
)

# ── Styles ──
st.markdown("""
<style>
    .stChatMessage { border-radius: 12px; }
    .sql-block {
        background: #1e1e2e;
        color: #a6e3a1;
        padding: 12px 16px;
        border-radius: 8px;
        font-family: monospace;
        font-size: 13px;
        margin: 8px 0;
    }
    .model-badge {
        background: #1e1e2e;
        color: #89b4fa;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.title("🗄️ EcommerceDB")
    st.markdown(f'<span class="model-badge">🤖 {MODEL.split("/")[-1]}</span>', unsafe_allow_html=True)
    st.divider()

    st.markdown("**Schema**")
    with st.expander("categories"):
        st.code("id, name, description")
    with st.expander("products"):
        st.code("id, name, price, stock_quantity\ncategory_id, created_at")
    with st.expander("customers"):
        st.code("id, first_name, last_name\nemail, phone, address")
    with st.expander("transactions"):
        st.code("id, customer_id, product_id\nquantity, total_amount, transaction_date")

    st.divider()
    st.markdown("**Suggestions**")
    suggestions = [
        "Which products have less than 20 units in stock?",
        "Which customer spent the most in total?",
        "How many sales were made per category?",
        "List the 3 best-selling products.",
    ]
    for s in suggestions:
        if st.button(s, width='stretch'):
            st.session_state["suggestion"] = s

    st.divider()
    if st.button("🗑️ Clear conversation", width='stretch'):
        st.session_state.messages = []
        st.rerun()

    show_sql = st.toggle("Show generated SQL", value=True)

# ── Message history ──
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Title ──
st.title("Database Assistant")
st.caption("Ask questions about your ecommerce database in plain English.")

# ── Render history ──
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            if show_sql and msg.get("sql"):
                with st.expander("🔍 SQL Query"):
                    st.markdown(f'<div class="sql-block">{msg["sql"]}</div>', unsafe_allow_html=True)
            if msg.get("dataframe") is not None:
                st.dataframe(msg["dataframe"], width='stretch')
            st.markdown(msg["content"])
        else:
            st.markdown(msg["content"])

# ── Input ──
if "suggestion" in st.session_state:
    question = st.session_state.pop("suggestion")
else:
    question = st.chat_input("e.g. What is the most expensive product?")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = ask(question, history=st.session_state.messages)


        if result["error"]:
            st.error(f"❌ {result['error']}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["error"],
                "sql": None,
                "dataframe": None,
            })
        else:
            if show_sql and result["sql"]:
                with st.expander("🔍 SQL Query"):
                    st.markdown(f'<div class="sql-block">{result["sql"]}</div>', unsafe_allow_html=True)

            df = None
            if result["columns"] and result["rows"]:
                df = pd.DataFrame(result["rows"], columns=result["columns"])
                st.dataframe(df, width='stretch')

            st.markdown(result["answer"])

            assistant_content = result["answer"]
            if result["sql"]:
                assistant_content = f"SQL used: {result['sql']}\n\nAnswer: {result['answer']}"
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_content,
                "sql": result["sql"],
                "dataframe": df,
            })