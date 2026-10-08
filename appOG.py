import streamlit as st
import duckdb
import pandas as pd
import json
import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load local environment variables from .env
load_dotenv()

st.set_page_config(
    page_title="Customer Support AI Assistant", 
    layout="wide", 
    page_icon="🎫"
)

# 1. Database Connection & Dataset State Initialization
if "conn" not in st.session_state:
    st.session_state.conn = duckdb.connect(database=':memory:')
    st.session_state.conn.execute("CREATE TABLE default_tickets AS SELECT * FROM read_json_auto('tickets.json')")
    st.session_state.available_tables = ["default_tickets"]

conn = st.session_state.conn

# 2. Permanent Dark Mode Styling
st.markdown("""
    <style>
        /* Main App Canvas Background */
        [data-testid="stAppViewContainer"] {
            background-color: #0b0f17 !important;
        }
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #111827 !important;
            border-right: 1px solid #1f2937 !important;
        }
        /* Dark Mode Chat Cards */
        div[data-testid="stChatMessage"] {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            border-radius: 12px !important;
            padding: 1rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Configuration
st.sidebar.title("⚙️ Settings")

dev_mode = st.sidebar.toggle("🛠️ Developer Mode", value=False)

st.sidebar.divider()

# Resolve API Key from .env or UI fallback
env_api_key = os.getenv("GROQ_API_KEY", "")
if env_api_key:
    st.sidebar.success("🔒 API Key loaded from `.env`")
    api_key = env_api_key
else:
    api_key = st.sidebar.text_input("Groq API Key (gsk_...)", type="password")

selected_model = "openai/gpt-oss-120b"

if api_key:
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        res = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=5)
        if res.status_code == 200:
            models_data = res.json().get("data", [])
            # Filter out terms-gated or audio/speech models
            model_ids = [
                m["id"] for m in models_data 
                if not any(blocked in m["id"].lower() for blocked in ["whisper", "guard", "canopylabs", "orpheus", "playai"])
            ]
            if model_ids:
                default_idx = 0
                for idx, m_id in enumerate(model_ids):
                    if "120b" in m_id.lower() or "gpt-oss" in m_id.lower():
                        default_idx = idx
                        break
                selected_model = st.sidebar.selectbox("Select Groq Model", options=model_ids, index=default_idx)
            else:
                st.sidebar.error("No text generation models available for this key.")
        else:
            st.sidebar.error("Invalid API Key.")
    except Exception as e:
        st.sidebar.error(f"Failed to fetch models: {e}")

st.sidebar.divider()
st.sidebar.subheader("🎯 Active Query Target")
query_scope = st.sidebar.radio(
    "Select Scope for Queries:",
    options=["Combined View (All Datasets)"] + st.session_state.available_tables,
    index=0
)

# Helper function to update active table target in DuckDB
def prepare_active_table():
    if query_scope == "Combined View (All Datasets)":
        union_queries = [f"SELECT *, '{tbl}' as dataset_source FROM {tbl}" for tbl in st.session_state.available_tables]
        combined_sql = " UNION ALL ".join(union_queries)
        conn.execute(f"CREATE OR REPLACE VIEW active_tickets AS {combined_sql}")
    else:
        conn.execute(f"CREATE OR REPLACE VIEW active_tickets AS SELECT *, '{query_scope}' as dataset_source FROM {query_scope}")

prepare_active_table()

# 4. Main Interface Layout Tabs
tab_chat, tab_data = st.tabs(["💬 Chat Analytics", "📊 Data View"])

# ==========================================
# TAB 1: Chat Analytics UI
# ==========================================
with tab_chat:
    st.title("🎫 Customer Support AI Assistant")
    st.caption(f"Ask natural language questions to analyze your tickets. Currently querying: **{query_scope}**")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I can analyze your support tickets, identify top product issues, or track refunds. What would you like to know today?"
            }
        ]

    # Render previous conversation history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if dev_mode and "sql" in msg:
                st.code(msg["sql"], language="sql")
            if "df" in msg:
                st.dataframe(msg["df"], width="stretch")


# ==========================================
# TAB 2: Data View & Dataset Ingestion
# ==========================================
with tab_data:
    st.header("📊 Dataset Management & Ingestion")
    
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("📤 Upload New Dataset")
        uploaded_file = st.file_uploader("Upload JSON File", type=["json"], key="new_dataset_uploader")
        dataset_name = st.text_input("New Table Name", placeholder="e.g., q2_tickets").strip().replace(" ", "_")
        
        if st.button("Create Dataset Table"):
            if uploaded_file and dataset_name:
                try:
                    data = json.load(uploaded_file)
                    df_upload = pd.DataFrame(data)
                    conn.register("temp_upload", df_upload)
                    conn.execute(f"CREATE TABLE {dataset_name} AS SELECT * FROM temp_upload")
                    
                    if dataset_name not in st.session_state.available_tables:
                        st.session_state.available_tables.append(dataset_name)
                    
                    st.success(f"Successfully created dataset `{dataset_name}`!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Error loading JSON: {err}")
            else:
                st.warning("Please provide both a JSON file and a unique table name.")

    with col2:
        st.subheader("➕ Append Data to Dataset")
        target_table = st.selectbox("Select Target Dataset Table", options=st.session_state.available_tables)
        append_file = st.file_uploader("Upload JSON to Append", type=["json"], key="append_dataset_uploader")
        
        if st.button("Append Records"):
            if append_file and target_table:
                try:
                    append_data = json.load(append_file)
                    df_append = pd.DataFrame(append_data)
                    conn.register("temp_append", df_append)
                    conn.execute(f"INSERT INTO {target_table} SELECT * FROM temp_append")
                    st.success(f"Successfully appended records to `{target_table}`!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Append failed: {err}")

    st.divider()
    st.subheader("🔍 Dataset Viewer")
    view_target = st.selectbox("Inspect dataset:", options=["Combined View (All Datasets)"] + st.session_state.available_tables)
    
    if view_target == "Combined View (All Datasets)":
        preview_df = conn.execute("SELECT * FROM active_tickets").df()
    else:
        preview_df = conn.execute(f"SELECT * FROM {view_target}").df()
        
    st.dataframe(preview_df, width="stretch")


# ==========================================
# ROOT-LEVEL CHAT INPUT (Anchored to Bottom)
# ==========================================
if prompt := st.chat_input("e.g., Which product has the most refund requests?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    if not api_key or not selected_model:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "⚠️ Missing API key or model selection. Please configure in the sidebar."
        })
    else:
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        
        system_prompt = """
        You are an expert SQL data analyst assistant specializing in DuckDB SQL.
        Convert the user's question into a DuckDB SQL query against the table view named 'active_tickets'.

        Available columns:
        - ticket_id (text)
        - customer_name (text)
        - order_id (text)
        - product_name (text)
        - fault_category (text)
        - priority (text)
        - refund_requested (boolean)
        - refund_type (text)
        - description (text)
        - dataset_source (text)

        CRITICAL SQL GENERATION RULES:
        1. ALWAYS use case-insensitive fuzzy matching (`ILIKE '%term%'`) or REGEX (`regexp_matches(column, 'pattern', 'i')`) for names, descriptions, products, or text fields unless an exact ID match is requested.
        2. Do NOT use `SELECT EXISTS(...)` or `COUNT(*)` when asking if a record exists. Select the actual matching rows.
        3. Return ONLY the raw valid DuckDB SQL query string. Do NOT include markdown code blocks, explanation, or extra prose.
        """

        try:
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            sql_query = response.choices[0].message.content.strip().replace("```sql", "").replace("```", "").strip()
            result_df = conn.execute(sql_query).df()
            summary_text = f"Here are the query results from `{query_scope}`:"

            st.session_state.messages.append({
                "role": "assistant",
                "content": summary_text,
                "sql": sql_query,
                "df": result_df
            })
        except Exception as e:
            error_msg = f"Sorry, I encountered an issue running that query: `{e}`"
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.rerun()