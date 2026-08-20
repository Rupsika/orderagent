"""
mock_data.py

Stand-in for PostgreSQL for the basic version of the agent.
Same shape as the tables described in the README (customers, orders,
shipments, tickets) but kept as in-memory dicts so the whole project
runs with zero external services.

Swap this module out for real DB queries (SQLAlchemy / asyncpg) later
without touching agent.py or tools.py — that's the point of keeping
the data-access functions at the bottom as the only public surface.
"""

from datetime import datetime, timedelta
import itertools

_now = datetime.utcnow()

CUSTOMERS = {
    "C1024": {"customer_id": "C1024", "name": "Aditi Rao", "email": "aditi@example.com"},
    "C2001": {"customer_id": "C2001", "name": "Marcus Webb", "email": "marcus@example.com"},
}

ORDERS = {
    "ORD123": {
        "order_id": "ORD123",
        "customer_id": "C1024",
        "items": [{"name": "Wireless Earbuds", "qty": 1, "price": 2499}],
        "total": 2499,
        "status": "SHIPPED",
        "placed_at": (_now - timedelta(days=4)).isoformat(),
    },
    "ORD124": {
        "order_id": "ORD124",
        "customer_id": "C1024",
        "items": [{"name": "Phone Case", "qty": 2, "price": 399}],
        "total": 798,
        "status": "DELIVERED",
        "placed_at": (_now - timedelta(days=10)).isoformat(),
    },
    "ORD200": {
        "order_id": "ORD200",
        "customer_id": "C2001",
        "items": [{"name": "Desk Lamp", "qty": 1, "price": 1899}],
        "total": 1899,
        "status": "PROCESSING",
        "placed_at": (_now - timedelta(hours=6)).isoformat(),
    },
}

SHIPMENTS = {
    "ORD123": {
        "order_id": "ORD123",
        "carrier": "BlueDart",
        "tracking_number": "BD998877",
        "status": "IN_TRANSIT",
        "eta": (_now + timedelta(days=1)).isoformat(),
        "last_update": (_now - timedelta(hours=14)).isoformat(),
        "history": [
            {"ts": (_now - timedelta(days=3)).isoformat(), "event": "Picked up from warehouse"},
            {"ts": (_now - timedelta(days=2)).isoformat(), "event": "Arrived at regional hub"},
            {"ts": (_now - timedelta(hours=14)).isoformat(), "event": "Out for delivery attempt — failed, no one available"},
        ],
    },
    "ORD124": {
        "order_id": "ORD124",
        "carrier": "Delhivery",
        "tracking_number": "DL445566",
        "status": "DELIVERED",
        "eta": (_now - timedelta(days=8)).isoformat(),
        "last_update": (_now - timedelta(days=8)).isoformat(),
        "history": [
            {"ts": (_now - timedelta(days=8)).isoformat(), "event": "Delivered — signed by recipient"},
        ],
    },
}

TICKETS = {}
_ticket_ids = itertools.count(1025)


# ---------------------------------------------------------------------
# Public data-access functions — this is the only surface tools.py
# should call. Replace bodies with real DB queries later.
# ---------------------------------------------------------------------

def get_customer(customer_id: str):
    return CUSTOMERS.get(customer_id)


def get_orders_for_customer(customer_id: str):
    return [o for o in ORDERS.values() if o["customer_id"] == customer_id]


def get_order(order_id: str):
    return ORDERS.get(order_id)


def get_tracking(order_id: str):
    return SHIPMENTS.get(order_id)


def get_tickets_for_customer(customer_id: str):
    return [t for t in TICKETS.values() if t["customer_id"] == customer_id]


def create_ticket(customer_id: str, order_id: str, subject: str, description: str, priority: str = "MEDIUM"):
    ticket_id = f"T{next(_ticket_ids)}"
    ticket = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "subject": subject,
        "description": description,
        "priority": priority,
        "status": "OPEN",
        "created_at": datetime.utcnow().isoformat(),
    }
    TICKETS[ticket_id] = ticket
    return ticket


def cancel_order(order_id: str):
    order = ORDERS.get(order_id)
    if not order:
        return None
    if order["status"] in ("SHIPPED", "DELIVERED"):
        return {"success": False, "reason": f"Order already {order['status']}, cannot cancel"}
    order["status"] = "CANCELLED"
    return {"success": True, "reason": "Order cancelled"}
