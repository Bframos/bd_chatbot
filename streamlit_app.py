import streamlit as st
from chatbot import perguntar, MODEL
import pandas as pd

# ── Configuração da página ──
st.set_page_config(
    page_title="EcommerceDB Chatbot",
    page_icon="🗄️",
    layout="wide",
)

# ── Estilo ──
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

    st.markdown("**Esquema**")
    with st.expander("categories"):
        st.code("id, name, description")
    with st.expander("products"):
        st.code("id, name, price, stock_quantity\ncategory_id, created_at")
    with st.expander("customers"):
        st.code("id, first_name, last_name\nemail, phone, address")
    with st.expander("transactions"):
        st.code("id, customer_id, product_id\nquantity, total_amount, transaction_date")

    st.divider()
    st.markdown("**Sugestões**")
    sugestoes = [
        "Quais os produtos com menos de 20 unidades em stock?",
        "Qual o cliente que mais gastou no total?",
        "Quantas vendas foram feitas por categoria?",
        "Lista os 3 produtos mais vendidos.",
    ]
    for s in sugestoes:
        if st.button(s, use_container_width=True):
            st.session_state["sugestao"] = s

    st.divider()
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    show_sql = st.toggle("Mostrar SQL gerado", value=True)

# ── Histórico de mensagens ──
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Título ──
st.title("Assistente de Base de Dados")
st.caption("Faz perguntas em Português sobre a tua base de dados de ecommerce.")

# ── Renderizar histórico ──
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            if show_sql and msg.get("sql"):
                with st.expander("🔍 Query SQL"):
                    st.markdown(f'<div class="sql-block">{msg["sql"]}</div>', unsafe_allow_html=True)
            if msg.get("dataframe") is not None:
                st.dataframe(msg["dataframe"], use_container_width=True)
            st.markdown(msg["content"])
        else:
            st.markdown(msg["content"])

# ── Input ──
if "sugestao" in st.session_state:
    pergunta = st.session_state.pop("sugestao")
else:
    pergunta = st.chat_input("Ex: Qual o produto mais caro?")

if pergunta:
    st.session_state.messages.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("A pensar..."):
            resultado = perguntar(pergunta)

        if resultado["erro"]:
            st.error(f"❌ {resultado['erro']}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": resultado["erro"],
                "sql": None,
                "dataframe": None,
            })
        else:
            if show_sql and resultado["sql"]:
                with st.expander("🔍 Query SQL"):
                    st.markdown(f'<div class="sql-block">{resultado["sql"]}</div>', unsafe_allow_html=True)

            df = None
            if resultado["colunas"] and resultado["linhas"]:
                df = pd.DataFrame(resultado["linhas"], columns=resultado["colunas"])
                st.dataframe(df, use_container_width=True)

            st.markdown(resultado["resposta"])

            st.session_state.messages.append({
                "role": "assistant",
                "content": resultado["resposta"],
                "sql": resultado["sql"],
                "dataframe": df,
            })