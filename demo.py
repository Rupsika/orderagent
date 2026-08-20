"""
demo.py

Quick way to see the ReAct loop run without spinning up FastAPI.

Run:
    python demo.py
"""

from dotenv import load_dotenv
load_dotenv()

from agent import run_agent

QUERIES = [
    ("C1024", "Where is my order ORD123? It feels late."),
    ("C1024", "My order ORD124 arrived but the case was cracked. What can I do?"),
    ("C2001", "Can I cancel order ORD200?"),
]

if __name__ == "__main__":
    from db import init_db
    init_db()  # demo.py can run standalone even before seed.py

    for customer_id, message in QUERIES:
        print("=" * 70)
        print(f"Customer {customer_id}: {message}")
        result = run_agent(customer_id, message)
        print(f"Tools called: {result['tool_trace']}")
        print(f"Agent: {result['response']}")
        print()
