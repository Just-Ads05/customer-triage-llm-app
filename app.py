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

# 1. Database Connection & Schema Initialization
if "conn" not in st.session_state:
    st.session_state.conn = duckdb.connect(database=':memory:')
    st.session_state.conn.execute("""
        CREATE TABLE default_tickets AS 
        SELECT 
            ticket_id, customer_name, order_id, product_name, 
            fault_category, priority, refund_requested, refund_type, 
            description, CAST(created_at AS TIMESTAMP) as created_at 
        FROM read_json_auto('tickets.json')
    """)
    st.session_state.available_tables = ["default_tickets"]

conn = st.session_state.conn

# 2. Permanent Dark Mode, Sticky Header Tabs, & Floating Controls Styling
st.markdown("""
    <style>
        /* Base Dark Backgrounds */
        [data-testid="stAppViewContainer"] { background-color: #0b0f17 !important; }
        section[data-testid="stSidebar"] { background-color: #111827 !important; border-right: 1px solid #1f2937 !important; }
        div[data-testid="stChatMessage"] { background-color: #1f2937 !important; border: 1px solid #374151 !important; border-radius: 12px !important; padding: 1rem !important; }

        /* 1. STICKY TABS HEADER */
        div[data-baseweb="tab-list"] {
            position: sticky !important;
            top: 0px !important;
            background-color: #0b0f17 !important;
            z-index: 9999 !important;
            padding-top: 12px !important;
            padding-bottom: 12px !important;
            border-bottom: 1px solid #1f2937 !important;
        }

        /* 2. MODE SELECTOR (Gemini-Style Horizontal Pills) */
        div[data-testid="stRadio"] > div {
            display: flex !important;
            flex-direction: row !important;
            gap: 8px !important;
            padding-bottom: 6px !important;
        }
        div[data-testid="stRadio"] label {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            border-radius: 20px !important;
            padding: 4px 14px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stRadio"] label:hover {
            border-color: #6366f1 !important;
            color: #ffffff !important;
        }

        /* 3. SCROLL TO BOTTOM FLOATING ARROW */
        .scroll-bottom-btn {
            position: fixed;
            bottom: 90px;
            right: 25px;
            width: 42px;
            height: 42px;
            background-color: #1f2937;
            color: #ffffff;
            border: 1px solid #374151;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            transition: all 0.2s ease;
            text-decoration: none !important;
            font-size: 18px;
            font-weight: bold;
        }
        .scroll-bottom-btn:hover {
            background-color: #374151;
            transform: scale(1.1);
            color: #6366f1;
        }

        /* 4. RIGHT-SIDE QUERY DOT INDEX */
        .nav-dot-container {
            position: fixed;
            right: 18px;
            top: 50%;
            transform: translateY(-50%);
            display: flex;
            flex-direction: column;
            gap: 14px;
            z-index: 9999;
        }
        .dot-wrapper {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: flex-end;
        }
        .nav-dot {
            width: 10px;
            height: 10px;
            background-color: #4b5563;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s ease;
            display: block;
        }
        .dot-wrapper:hover .nav-dot {
            background-color: #6366f1;
            transform: scale(1.4);
            box-shadow: 0 0 8px #6366f1;
        }
        .dot-tooltip {
            visibility: hidden;
            opacity: 0;
            position: absolute;
            right: 24px;
            background-color: #1f2937;
            color: #f3f4f6;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            white-space: nowrap;
            max-width: 260px;
            overflow: hidden;
            text-overflow: ellipsis;
            border: 1px solid #374151;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            transition: opacity 0.2s ease, visibility 0.2s ease;
            pointer-events: none;
        }
        .dot-wrapper:hover .dot-tooltip {
            visibility: visible;
            opacity: 1;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Setup
st.sidebar.title("⚙️ Settings")
dev_mode = st.sidebar.toggle("🛠️ Developer Mode", value=False)
st.sidebar.divider()

env_api_key = os.getenv("GROQ_API_KEY", "")
api_key = env_api_key if env_api_key else st.sidebar.text_input("Groq API Key (gsk_...)", type="password")

selected_model = "openai/gpt-oss-120b"
if api_key:
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        res = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=5)
        if res.status_code == 200:
            models_data = res.json().get("data", [])
            model_ids = [m["id"] for m in models_data if not any(b in m["id"].lower() for b in ["whisper", "guard", "canopylabs", "orpheus", "playai"])]
            if model_ids:
                default_idx = next((i for i, m in enumerate(model_ids) if "120b" in m.lower() or "gpt-oss" in m.lower()), 0)
                selected_model = st.sidebar.selectbox("Select Groq Model", options=model_ids, index=default_idx)
    except Exception as e:
        st.sidebar.error(f"Failed to load models: {e}")

st.sidebar.divider()
st.sidebar.subheader("🎯 Active Query Target")
query_scope = st.sidebar.radio("Select Scope for Queries:", options=["Combined View (All Datasets)"] + st.session_state.available_tables, index=0)

def prepare_active_table():
    if query_scope == "Combined View (All Datasets)":
        union_queries = [f"SELECT *, '{tbl}' as dataset_source FROM {tbl}" for tbl in st.session_state.available_tables]
        conn.execute(f"CREATE OR REPLACE VIEW active_tickets AS {' UNION ALL '.join(union_queries)}")
    else:
        conn.execute(f"CREATE OR REPLACE VIEW active_tickets AS SELECT *, '{query_scope}' as dataset_source FROM {query_scope}")

prepare_active_table()

# 4. Main Navigation Tabs (Sticky Header)
tab_chat, tab_data = st.tabs(["💬 Chat Analytics", "📊 Data View & Management"])

# ==========================================
# TAB 1: Chat Analytics Engine
# ==========================================
with tab_chat:
    st.title("🎫 Customer Support AI Assistant")
    st.caption(f"Ask natural language questions to analyze your tickets. Target view: **{query_scope}**")

    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hello! I can perform analytics, summarize customer issues, or track refund metrics. What would you like to investigate?"
        }]

    # Render message history and assign scroll anchors
    user_query_count = 0
    user_prompts = []

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"<div id='query-{user_query_count}' style='scroll-margin-top: 80px;'></div>", unsafe_allow_html=True)
            user_prompts.append(msg["content"])
            user_query_count += 1
            
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if dev_mode and "sql" in msg:
                st.code(msg["sql"], language="sql")
            if "df" in msg and msg["df"] is not None and not msg["df"].empty:
                st.dataframe(msg["df"], width="stretch")

    # Mode Selector directly above chat_input
    selected_mode = st.radio(
        "Response Mode",
        options=["⚡ Normal", "🧠 Verbose"],
        index=1,
        horizontal=True,
        label_visibility="collapsed",
        key="response_mode"
    )
    verbose_mode = (selected_mode == "🧠 Verbose")

    # Floating Dot Navigation & Scroll-to-Bottom Arrow UI
    if user_prompts:
        dots_html = ""
        for idx, prompt_text in enumerate(user_prompts):
            clean_text = prompt_text.replace('"', '&quot;').replace("'", "&#39;")
            short_text = clean_text[:32] + ("..." if len(clean_text) > 32 else "")
            dots_html += f'''
            <div class="dot-wrapper">
                <span class="dot-tooltip">Query {idx + 1}: {short_text}</span>
                <a href="#query-{idx}" class="nav-dot"></a>
            </div>
            '''
        
        st.markdown(f'''
            <div class="nav-dot-container">
                {dots_html}
            </div>
            <a href="#latest-anchor" class="scroll-bottom-btn" title="Go to Latest Query" onclick="window.scrollTo({{top: document.body.scrollHeight, behavior: 'smooth'}});">
                ↓
            </a>
            <div id="latest-anchor"></div>
        ''', unsafe_allow_html=True)


# ==========================================
# TAB 2: Data Ingestion & Dataset Viewer
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
                    if "created_at" in df_upload.columns:
                        df_upload["created_at"] = pd.to_datetime(df_upload["created_at"])
                    
                    conn.register("temp_upload", df_upload)
                    conn.execute(f"CREATE TABLE {dataset_name} AS SELECT * FROM temp_upload")
                    
                    if dataset_name not in st.session_state.available_tables:
                        st.session_state.available_tables.append(dataset_name)
                    
                    st.success(f"Successfully created table `{dataset_name}`!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Error loading JSON: {err}")
            else:
                st.warning("Please provide both a JSON file and a unique table name.")

    with col2:
        st.subheader("➕ Append Data to Existing Dataset")
        target_table = st.selectbox("Select Target Dataset Table", options=st.session_state.available_tables)
        append_file = st.file_uploader("Upload JSON to Append", type=["json"], key="append_dataset_uploader")
        
        if st.button("Append Records"):
            if append_file and target_table:
                try:
                    append_data = json.load(append_file)
                    df_append = pd.DataFrame(append_data)
                    if "created_at" in df_append.columns:
                        df_append["created_at"] = pd.to_datetime(df_append["created_at"])
                        
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
# CHAT INPUT ENGINE
# ==========================================
if prompt := st.chat_input("e.g., Summarize top complaints logged in the last 30 days"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with tab_chat:
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.chat_message("assistant"):
            if not api_key or not selected_model:
                st.error("⚠️ Missing API Key or Model selection in sidebar.")
                st.session_state.messages.append({"role": "assistant", "content": "⚠️ Missing API Key or Model."})
            else:
                spinner_label = "💭 Thinking, generating SQL, & analyzing database..." if verbose_mode else "⚡ Executing fast SQL query..."
                with st.spinner(spinner_label):
                    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
                    
                    system_sql_prompt = """
                    You are an expert SQL analyst generating DuckDB SQL queries against the table view 'active_tickets'.

                    Available Columns:
                    - ticket_id (text)
                    - customer_name (text)
                    - order_id (text)
                    - product_name (text)
                    - fault_category (text)
                    - priority (text)
                    - refund_requested (boolean)
                    - refund_type (text)
                    - description (text)
                    - created_at (TIMESTAMP, e.g., '2026-09-15 14:22:00')
                    - dataset_source (text)

                    STRICT SQL RULES:
                    1. SYNONYMS/KEYWORDS: When searching concepts in text fields (description, product_name), combine multiple potential terms using OR and ILIKE. Example: `(description ILIKE '%flicker%' OR description ILIKE '%line%' OR description ILIKE '%screen%')`.
                    2. TEMPORAL QUERIES: Use DuckDB timestamp functions. Examples: `created_at >= CURRENT_DATE - INTERVAL '30 days'` or `DATE_TRUNC('month', created_at)`.
                    3. AGGREGATION: For percentages, use calculations like `ROUND(COUNT(CASE WHEN refund_requested THEN 1 END) * 100.0 / COUNT(*), 2)`.
                    4. OUTPUT FORMAT: Return ONLY the raw SQL query string without markdown code blocks or commentary.
                    """

                    messages = [
                        {"role": "system", "content": system_sql_prompt},
                        {"role": "user", "content": prompt}
                    ]

                    sql_query = ""
                    result_df = None
                    max_retries = 3
                    attempt = 0
                    error_logs = []

                    while attempt < max_retries:
                        attempt += 1
                        try:
                            response = client.chat.completions.create(
                                model=selected_model,
                                messages=messages,
                                temperature=0
                            )
                            sql_query = response.choices[0].message.content.strip().replace("```sql", "").replace("```", "").strip()
                            result_df = conn.execute(sql_query).df()
                            break
                        except Exception as e:
                            err_msg = str(e)
                            error_logs.append(f"Attempt {attempt}: {err_msg}")
                            messages.append({"role": "assistant", "content": sql_query})
                            messages.append({
                                "role": "user", 
                                "content": f"The query failed with error: {err_msg}. Please fix the DuckDB SQL and re-output the corrected query ONLY."
                            })

                    if result_df is not None:
                        if verbose_mode:
                            if result_df.empty:
                                synthesis_text = "No matching records were found in the database for your query."
                            else:
                                sample_data = result_df.head(15).to_dict(orient="records")
                                synthesis_prompt = f"""
                                The user asked: "{prompt}"
                                The DuckDB query returned {len(result_df)} records. Sample records:
                                {json.dumps(sample_data, default=str)}

                                Provide a clear, direct natural language answer summarizing the key findings, metrics, or main takeaways requested by the user.
                                Keep it concise (2-4 bullet points or short sentences). Do not mention SQL unless asked.
                                """
                                
                                synth_response = client.chat.completions.create(
                                    model=selected_model,
                                    messages=[{"role": "user", "content": synthesis_prompt}],
                                    temperature=0.3
                                )
                                synthesis_text = synth_response.choices[0].message.content.strip()
                        else:
                            synthesis_text = f"📊 Query executed successfully. Returned **{len(result_df)}** matching record(s)."

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": synthesis_text,
                            "sql": sql_query,
                            "df": result_df
                        })
                    else:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"⚠️ Unable to execute query after {max_retries} attempts.\nErrors: {'; '.join(error_logs)}"
                        })

    st.rerun()