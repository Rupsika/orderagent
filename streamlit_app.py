"""
streamlit_app.py

Chat UI for the Order & Delivery Support Agent, talking to the real
FastAPI backend (auth, SQLite persistence, LangGraph agent) over HTTP.

Run (with the API already running on :8000):
    streamlit run streamlit_app.py
"""

import requests
import streamlit as st

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Order Support Agent", page_icon="📦", layout="centered")


def api_post(path, json=None, auth=True):
    headers = {"Authorization": f"Bearer {st.session_state.token}"} if auth else {}
    r = requests.post(f"{API_URL}{path}", json=json, headers=headers)
    return r


def api_get(path):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    r = requests.get(f"{API_URL}{path}", headers=headers)
    return r


# ---------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------

if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.customer_name = None
    st.session_state.conversation_id = None
    st.session_state.messages = []  # [{"role": "human"/"ai", "content": str, "tool_trace": [...]}]


# ---------------------------------------------------------------------
# Auth screen
# ---------------------------------------------------------------------

def auth_screen():
    st.title("📦 Order & Delivery Support")
    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", value="aditi@example.com")
            password = st.text_input("Password", type="password", value="password123")
            submitted = st.form_submit_button("Log in")
        if submitted:
            r = api_post("/auth/login", {"email": email, "password": password}, auth=False)
            if r.status_code == 200:
                data = r.json()
                st.session_state.token = data["access_token"]
                st.session_state.customer_name = data["name"]
                st.rerun()
            else:
                st.error(r.json().get("detail", "Login failed"))
        st.caption("Demo accounts: aditi@example.com / marcus@example.com, password: password123")

    with tab_register:
        with st.form("register_form"):
            name = st.text_input("Name")
            email_r = st.text_input("Email", key="reg_email")
            password_r = st.text_input("Password (min 6 chars)", type="password", key="reg_password")
            submitted_r = st.form_submit_button("Create account")
        if submitted_r:
            r = api_post("/auth/register", {"name": name, "email": email_r, "password": password_r}, auth=False)
            if r.status_code == 200:
                data = r.json()
                st.session_state.token = data["access_token"]
                st.session_state.customer_name = data["name"]
                st.rerun()
            else:
                st.error(r.json().get("detail", "Registration failed"))


# ---------------------------------------------------------------------
# Chat screen
# ---------------------------------------------------------------------

def load_conversation(conv_id):
    r = api_get(f"/conversations/{conv_id}/messages")
    if r.status_code == 200:
        st.session_state.conversation_id = conv_id
        st.session_state.messages = r.json()


def chat_screen():
    with st.sidebar:
        st.markdown(f"**Logged in as** {st.session_state.customer_name}")
        if st.button("Log out"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.divider()
        if st.button("➕ New conversation"):
            r = api_post("/conversations", {})
            if r.status_code == 200:
                st.session_state.conversation_id = r.json()["id"]
                st.session_state.messages = []
                st.rerun()

        st.markdown("**Conversations**")
        convs = api_get("/conversations").json()
        for c in convs:
            label = c["title"] or f"Conversation {c['id']}"
            if st.button(label, key=f"conv_{c['id']}", use_container_width=True):
                load_conversation(c["id"])
                st.rerun()

    st.title("📦 Order & Delivery Support")

    for m in st.session_state.messages:
        with st.chat_message("user" if m["role"] == "human" else "assistant"):
            st.write(m["content"])
            if m.get("tool_trace"):
                st.caption("🔧 " + ", ".join(m["tool_trace"]))

    prompt = st.chat_input("Ask about an order, tracking, refund, or raise an issue...")
    if prompt:
        st.session_state.messages.append({"role": "human", "content": prompt, "tool_trace": []})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                r = api_post("/chat", {
                    "message": prompt,
                    "conversation_id": st.session_state.conversation_id,
                })
            if r.status_code == 200:
                data = r.json()
                st.session_state.conversation_id = data["conversation_id"]
                st.write(data["response"])
                if data["tool_trace"]:
                    st.caption("🔧 " + ", ".join(data["tool_trace"]))
                st.session_state.messages.append({
                    "role": "ai", "content": data["response"], "tool_trace": data["tool_trace"]
                })
            else:
                st.error(r.json().get("detail", "Something went wrong"))


# ---------------------------------------------------------------------

if not st.session_state.token:
    auth_screen()
else:
    chat_screen()
