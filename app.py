import streamlit as st
import json

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
AGENT_FQN = "WELLNESS_AI.DEMO_SEMANTIC.AAYU_PUBLIC_AGENT"

SUBJECTS = {
    "wellness": [
        {"id": 9001, "label": "Active Athlete",        "icon": "🏃", "days": "90 days"},
        {"id": 9002, "label": "Stressed Professional",  "icon": "💼", "days": "60 days"},
        {"id": 9003, "label": "Garmin Runner",           "icon": "⌚", "days": "45 days"},
        {"id": 9004, "label": "Poor Sleeper",            "icon": "😴", "days": "30 days"},
        {"id": 9005, "label": "Balanced Baseline",       "icon": "⚖️", "days": "60 days"},
        {"id": 9011, "label": "Sparse Wellness",         "icon": "📉", "days": "5 days"},
    ],
    "metabolic": [
        {"id": 9006, "label": "Well-Controlled T2DM",   "icon": "✅", "days": "3 visits"},
        {"id": 9007, "label": "Worsening T1DM",          "icon": "📈", "days": "4 visits"},
        {"id": 9008, "label": "New Diagnosis",            "icon": "🆕", "days": "2 visits"},
        {"id": 9009, "label": "Stable Elderly",           "icon": "🧓", "days": "3 visits"},
        {"id": 9010, "label": "Metabolic Syndrome",       "icon": "⚠️", "days": "3 visits"},
        {"id": 9012, "label": "Sparse Metabolic",         "icon": "📉", "days": "1 visit"},
    ],
}

WELLNESS_QUESTIONS = [
    "How is sleep for person {id}?",
    "How is recovery for person {id}?",
    "What is the activity level for person {id}?",
    "Is person {id} sleeping less than usual?",
    "Show all domain details for person {id}",
    "What has changed recently for person {id}?",
    "Has sleep been getting worse for person {id}?",
    "Does recovery look normal for person {id}?",
    "Has person {id} been less active than normal?",
    "What is the latest health snapshot for person {id}?",
    "How is circadian rhythm for person {id}?",
    "What is the data quality for person {id}?",
    "Is person {id} well-rested?",
    "Show the sleep trend for person {id} over the last 7 days",
    "Compare sleep and recovery for person {id}",
]

METABOLIC_QUESTIONS = [
    "What is the latest metabolic profile for person {id}?",
    "Show the metabolic trajectory for person {id}",
    "Is person {id} getting better or worse?",
    "What is the HbA1c for person {id}?",
    "What is the BMI for person {id}?",
    "How is kidney function for person {id}?",
    "What diabetes type does person {id} have?",
    "Is the metabolic risk score reliable for person {id}?",
    "Show all visits for person {id}",
    "What is the risk trend for person {id}?",
    "Is person {id} improving?",
    "Does person {id} have complete lab data?",
]

GENERAL_QUESTIONS = [
    "How many subjects have critical sleep debt?",
    "Which patients are getting worse?",
    "Compare T1DM vs T2DM patients",
    "What is the distribution of metabolic risk scores?",
    "How many subjects have good data quality?",
]


# ──────────────────────────────────────────────
# SNOWFLAKE CONNECTION + AGENT CALL
# ──────────────────────────────────────────────
def get_connection():
    """Get or create a Snowflake connection."""
    if "sf_conn" in st.session_state and st.session_state.sf_conn:
        try:
            st.session_state.sf_conn.cursor().execute("SELECT 1")
            return st.session_state.sf_conn
        except Exception:
            st.session_state.sf_conn = None

    import snowflake.connector
    conn_params = {
        "account": st.secrets["snowflake"]["account"],
        "user": st.secrets["snowflake"]["user"],
        "warehouse": st.secrets["snowflake"]["warehouse"],
        "database": "WELLNESS_AI",
        "schema": "DEMO_SEMANTIC",
        "role": st.secrets["snowflake"].get("role", "ACCOUNTADMIN"),
    }

    if "private_key_path" in st.secrets["snowflake"]:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        with open(st.secrets["snowflake"]["private_key_path"], "rb") as f:
            p_key = serialization.load_pem_private_key(
                f.read(),
                password=(
                    st.secrets["snowflake"]["private_key_passphrase"].encode()
                    if st.secrets["snowflake"].get("private_key_passphrase")
                    else None
                ),
                backend=default_backend(),
            )
        conn_params["private_key"] = p_key
    else:
        conn_params["password"] = st.secrets["snowflake"]["password"]

    conn = snowflake.connector.connect(**conn_params)
    st.session_state.sf_conn = conn
    return conn


def call_agent(question: str) -> str:
    """Call the agent via SNOWFLAKE.CORTEX.DATA_AGENT_RUN with proper JSON request body."""
    try:
        conn = get_connection()

        # Build the JSON request body per the DATA_AGENT_RUN spec:
        # https://docs.snowflake.com/en/sql-reference/functions/data_agent_run-snowflake-cortex
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question}
                    ]
                }
            ],
            "stream": False,
        }
        request_json = json.dumps(request_body)

        sql = f"""
        SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
            '{AGENT_FQN}',
            $${request_json}$$
        ) AS response
        """
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()
        cur.close()

        if row and row[0]:
            result = json.loads(row[0]) if isinstance(row[0], str) else row[0]

            if isinstance(result, dict):
                # Response format: {"role": "assistant", "content": [...], ...}
                content = result.get("content", [])
                if isinstance(content, list):
                    texts = [
                        c.get("text", "")
                        for c in content
                        if c.get("type") == "text" and c.get("text")
                    ]
                    if texts:
                        return "\n\n".join(texts)

                # Fallback: threaded response with messages array
                messages = result.get("messages", [])
                for msg in reversed(messages):
                    if msg.get("role") == "assistant":
                        msg_content = msg.get("content", "")
                        if isinstance(msg_content, list):
                            texts = [c.get("text", "") for c in msg_content if c.get("type") == "text"]
                            return "\n\n".join(texts) if texts else str(msg_content)
                        return str(msg_content)

                # Last fallback: dump raw JSON
                if "text" in result:
                    return result["text"]
                return f"```json\n{json.dumps(result, indent=2)}\n```"
            return str(result)
        return "No response from agent."
    except Exception as e:
        return f"Error: {e}"


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def get_subject_cohort(person_id: int) -> str:
    for s in SUBJECTS["wellness"]:
        if s["id"] == person_id:
            return "wellness"
    for s in SUBJECTS["metabolic"]:
        if s["id"] == person_id:
            return "metabolic"
    return "unknown"


def get_questions_for_subject(person_id: int) -> list:
    cohort = get_subject_cohort(person_id)
    if cohort == "wellness":
        return [q.format(id=person_id) for q in WELLNESS_QUESTIONS]
    elif cohort == "metabolic":
        return [q.format(id=person_id) for q in METABOLIC_QUESTIONS]
    return []


# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="AAYU Research Project",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    footer { visibility: hidden; }
    div[data-testid="stSidebar"] .stButton > button {
        text-align: left !important;
        font-size: 0.85rem;
        padding: 6px 10px;
        white-space: normal;
        height: auto;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────
if "selected_subject" not in st.session_state:
    st.session_state.selected_subject = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Sample Questions")

    selected = st.session_state.selected_subject
    if selected is None:
        st.info("Select a subject first to see relevant questions.")
    else:
        subj = None
        for cohort in SUBJECTS.values():
            for s in cohort:
                if s["id"] == selected:
                    subj = s
                    break

        if subj:
            cohort_name = get_subject_cohort(selected)
            color = "🟢" if cohort_name == "wellness" else "🟡"
            st.markdown(f"**{color} {subj['icon']} {subj['label']}** (ID: {selected})")
            st.caption(f"{subj['days']} of data")
            st.divider()

            questions = get_questions_for_subject(selected)
            for i, q in enumerate(questions):
                if st.button(q, key=f"sq_{i}", use_container_width=True):
                    st.session_state.pending_question = q

    st.divider()
    st.markdown("### General Questions")
    st.caption("No subject selection required.")
    for i, q in enumerate(GENERAL_QUESTIONS):
        if st.button(q, key=f"gq_{i}", use_container_width=True):
            st.session_state.pending_question = q

    # Cross-cohort test buttons
    if selected:
        st.divider()
        st.markdown("### Cross-Cohort Tests")
        st.caption("These should trigger boundary responses.")
        if get_subject_cohort(selected) == "wellness":
            test_q = f"What is the HbA1c for person {selected}?"
        else:
            test_q = f"How is sleep for person {selected}?"
        if st.button(test_q, key="cross_test", use_container_width=True):
            st.session_state.pending_question = test_q

    st.divider()
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()


# ──────────────────────────────────────────────
# MAIN — Header
# ──────────────────────────────────────────────
st.markdown("# 🧬 AAYU Research Project")
st.caption("Proactive Wellness Intelligence — Synthetic Demo Data")


# ──────────────────────────────────────────────
# MAIN — Subject Selection
# ──────────────────────────────────────────────
st.markdown("#### Select a Subject")

st.markdown("**🟢 Wellness Cohort** — Sleep, Activity, Recovery, Circadian")
w_cols = st.columns(6)
for i, subj in enumerate(SUBJECTS["wellness"]):
    with w_cols[i]:
        is_selected = st.session_state.selected_subject == subj["id"]
        btn_label = f"{subj['icon']} {subj['label']}\n{subj['id']} · {subj['days']}"
        if st.button(
            btn_label,
            key=f"w_{subj['id']}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state.selected_subject = subj["id"]
            st.rerun()

st.markdown("**🟡 Metabolic Cohort** — HbA1c, BMI, eGFR, Diabetes")
m_cols = st.columns(6)
for i, subj in enumerate(SUBJECTS["metabolic"]):
    with m_cols[i]:
        is_selected = st.session_state.selected_subject == subj["id"]
        btn_label = f"{subj['icon']} {subj['label']}\n{subj['id']} · {subj['days']}"
        if st.button(
            btn_label,
            key=f"m_{subj['id']}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state.selected_subject = subj["id"]
            st.rerun()

st.divider()


# ──────────────────────────────────────────────
# MAIN — Chat History
# ──────────────────────────────────────────────
for entry in st.session_state.chat_history:
    if entry["role"] == "user":
        with st.chat_message("user"):
            st.markdown(entry["content"])
    else:
        with st.chat_message("assistant", avatar="🧬"):
            st.markdown(entry["content"])


# ──────────────────────────────────────────────
# MAIN — Process pending question from sidebar
# ──────────────────────────────────────────────
if st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None

    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🧬"):
        with st.spinner("AAYU is thinking..."):
            response = call_agent(prompt)
        st.markdown(response)
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.rerun()


# ──────────────────────────────────────────────
# MAIN — Chat Input (bottom prompt bar)
# ──────────────────────────────────────────────
if prompt := st.chat_input("Ask AAYU about a subject's health..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🧬"):
        with st.spinner("AAYU is thinking..."):
            response = call_agent(prompt)
        st.markdown(response)
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.rerun()
