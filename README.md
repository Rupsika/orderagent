# Order & Delivery Support Agent

A customer-support agent for orders and deliveries, built as a **LangGraph
ReAct agent** over **LangChain** tools and backed by **Gemini 2.5 Flash**.
It ships with a FastAPI backend (JWT auth, SQLite persistence, saved
multi-turn conversations) and a Streamlit chat UI.

## Features
- **LangGraph agent**: a `StateGraph` with an agent node, a tool node, and a
  conditional edge that loops until the model stops calling tools.
- **LangChain tools** (`@tool`) bound to Gemini via `bind_tools`: look up
  orders, check tracking, list and create support tickets, check refund
  eligibility, and request cancellation.
- **Authentication**: customers register or log in with email and password.
  Passwords are hashed with PBKDF2-HMAC-SHA256 (600,000 iterations, per
  OWASP guidance), and sessions use JWT bearer tokens.
- **Per-customer data scoping**: tools are built per request around the
  `customer_id` from the verified JWT, never from the request body, so the
  model can't read another customer's orders or tickets.
- **Persistence**: SQLite via SQLAlchemy stores customers, orders,
  shipments, tickets, conversations, and messages. Chat history is passed
  back to the agent so each conversation keeps its context.
- **Tool trace**: each response lists the tools the agent called
  (for example "✓ Order retrieved, ✓ Tracking checked").

## Setup
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then set GOOGLE_API_KEY and JWT_SECRET
python seed.py                  # creates order_support.db with demo data
```

The SQLite file is created locally and is **not** committed (`*.db` is
listed in `.gitignore`).

Demo accounts created by `seed.py` (password `password123`):

| Email                | Customer | Orders                                              |
|----------------------|----------|-----------------------------------------------------|
| `aditi@example.com`  | C1024    | `ORD123` (delayed shipment), `ORD124` (delivered)   |
| `marcus@example.com` | C2001    | `ORD200` (processing, can still be cancelled)       |

## Run the API
```bash
uvicorn main:app --reload
```

```bash
# log in to get a token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "aditi@example.com", "password": "password123"}'

# chat with the agent
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "Where is my order ORD123?"}'
```

Endpoints:

| Method | Path                                   | Purpose                                |
|--------|----------------------------------------|----------------------------------------|
| POST   | `/auth/register`, `/auth/login`        | Create an account or log in; returns a JWT |
| GET    | `/me`                                  | Current customer                       |
| GET/POST | `/conversations`                     | List conversations or start a new one  |
| GET    | `/conversations/{id}/messages`         | Message history                        |
| POST   | `/chat`                                | Send a message (optional `conversation_id`) |
| GET    | `/health`                              | Health check                           |

## Run the Streamlit UI
With the API running on port 8000:
```bash
streamlit run streamlit_app.py
```

## Run the CLI demo (no server)
```bash
python demo.py
```
This sends three sample messages through the agent and prints which tools
it called and its final answer.

## File map
```
agent.py          # LangGraph ReAct graph + run_agent() entrypoint
tools.py          # LangChain tools, scoped to one authenticated customer_id
crud.py           # data-access functions over the database
db.py             # SQLAlchemy models + SQLite engine
security.py       # password hashing + JWT helpers
seed.py           # creates and seeds the local SQLite database
main.py           # FastAPI app (auth, conversations, /chat)
streamlit_app.py  # chat UI that talks to the API
demo.py           # CLI runner, no server needed
mock_data.py      # original in-memory data store (legacy, no longer used)
```

## Next steps
1. Add real shipment tracking (for example AfterShip) in the tracking tool.
2. Move from SQLite to PostgreSQL for production (set `DATABASE_URL`).
3. Add RAG over return/refund policy documents.
4. Add ticket escalation rules and human approval before
   `request_cancellation` changes an order.
5. Consider Argon2id for password hashing.
