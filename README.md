# Order & Delivery Support Agent 

A working slice of the full system in your spec: a real **LangGraph
ReAct agent** over **LangChain** tools, backed by **Gemini 2.5 Flash**.
No Postgres, no AfterShip, no Next.js frontend yet — data is an
in-memory mock store so you can run and test the agent loop itself
today.

## What's actually real here
- Real `langgraph.StateGraph` with an agent node + tool node + a
  conditional edge that loops until the model stops calling tools.
- Real LangChain `@tool`-decorated functions, bound to Gemini via
  `bind_tools`.
- Real security pattern: tools are built per-request closed over the
  authenticated `customer_id`, so the model can never fetch another
  customer's order/ticket data even if it tries.
- A FastAPI `/chat` endpoint and a CLI `demo.py` to exercise it.

## What's mocked (intentionally, for this stage)
- `mock_data.py` stands in for PostgreSQL — same shape as the tables
  in your spec (customers, orders, shipments, tickets), just in-memory.
- No AfterShip integration — tracking data is hardcoded sample events.
- No auth/RBAC layer — `customer_id` is passed directly in the request.
- No RAG / policy retrieval, no ticket escalation UI, no dashboards.

## Setup
```bash
cd order_support_agent
python -m venv venv && source venv/bin/activate   # or your preferred env tool
pip install -r requirements.txt
cp .env.example .env
# put your Gemini API key in .env
```

## Run the CLI demo (fastest way to see it work)
```bash
python demo.py
```
This runs three sample customer messages through the agent and prints
which tools it chose to call and its final answer for each — this is
the "tool trace" your README's UI wants to surface (e.g. "✓ Order
retrieved, ✓ Tracking checked").

## Run the API
```bash
uvicorn main:app --reload
```
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "C1024", "message": "Where is my order ORD123?"}'
```

Try customer `C1024` (has a delayed shipment on `ORD123`, a delivered
order `ORD124`) and `C2001` (has a `PROCESSING` order `ORD200` that can
still be cancelled).

## File map
```
mock_data.py   # in-memory "database" — swap for real Postgres later
tools.py       # LangChain tools, scoped to one customer_id
agent.py       # the LangGraph ReAct graph + run_agent() entrypoint
main.py        # FastAPI /chat endpoint
demo.py        # CLI runner, no server needed
```

## Next steps (matches your spec's build order)
1. Swap `mock_data.py` for real Postgres (SQLAlchemy) — nothing in
   `tools.py` or `agent.py` needs to change if you keep the same
   function signatures.
2. Add real shipment tracking via AfterShip in `get_tracking_status`.
3. Add short-term memory by persisting `history` per conversation
   (e.g. Redis or a `conversations` table) and passing it into
   `run_agent(..., history=...)`.
4. Add auth so `customer_id` comes from a verified session, not the
   request body.
5. Add ticket escalation rules and human-approval gating on
   `request_cancellation` before it's a real state change.
