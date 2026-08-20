"""
crud.py

DB-backed data-access functions, same shape/names as the old
mock_data.py so tools.py and agent.py barely had to change. Every
function opens its own short-lived session — fine for SQLite + this
request volume.
"""

import itertools
from datetime import datetime, timezone

from db import get_session, Customer, Order, Shipment, Ticket, Conversation, Message
from security import hash_password, verify_password

_ticket_ids = itertools.count(1025)


def _order_to_dict(o: Order):
    return {
        "order_id": o.order_id,
        "customer_id": o.customer_id,
        "items": o.items,
        "total": o.total,
        "status": o.status,
        "placed_at": o.placed_at.isoformat() if o.placed_at else None,
    }


def _shipment_to_dict(s: Shipment):
    return {
        "order_id": s.order_id,
        "carrier": s.carrier,
        "tracking_number": s.tracking_number,
        "status": s.status,
        "eta": s.eta.isoformat() if s.eta else None,
        "last_update": s.last_update.isoformat() if s.last_update else None,
        "history": s.history,
    }


def _ticket_to_dict(t: Ticket):
    return {
        "ticket_id": t.ticket_id,
        "customer_id": t.customer_id,
        "order_id": t.order_id,
        "subject": t.subject,
        "description": t.description,
        "priority": t.priority,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


# ---------------------------------------------------------------------
# Customers / auth
# ---------------------------------------------------------------------

def get_customer(customer_id: str):
    with get_session() as s:
        c = s.get(Customer, customer_id)
        if not c:
            return None
        return {"customer_id": c.customer_id, "name": c.name, "email": c.email}


def get_customer_by_email(email: str):
    with get_session() as s:
        return s.query(Customer).filter(Customer.email == email).first()


def create_customer(customer_id: str, name: str, email: str, password: str):
    with get_session() as s:
        c = Customer(customer_id=customer_id, name=name, email=email, password_hash=hash_password(password))
        s.add(c)
        s.commit()
        return {"customer_id": c.customer_id, "name": c.name, "email": c.email}


def authenticate(email: str, password: str):
    with get_session() as s:
        c = s.query(Customer).filter(Customer.email == email).first()
        if not c or not verify_password(password, c.password_hash):
            return None
        return {"customer_id": c.customer_id, "name": c.name, "email": c.email}


def next_customer_id():
    with get_session() as s:
        count = s.query(Customer).count()
        return f"C{2100 + count}"


# ---------------------------------------------------------------------
# Orders / shipments / tickets
# ---------------------------------------------------------------------

def get_orders_for_customer(customer_id: str):
    with get_session() as s:
        rows = s.query(Order).filter(Order.customer_id == customer_id).all()
        return [_order_to_dict(o) for o in rows]


def get_order(order_id: str):
    with get_session() as s:
        o = s.get(Order, order_id)
        return _order_to_dict(o) if o else None


def get_tracking(order_id: str):
    with get_session() as s:
        sh = s.get(Shipment, order_id)
        return _shipment_to_dict(sh) if sh else None


def get_tickets_for_customer(customer_id: str):
    with get_session() as s:
        rows = s.query(Ticket).filter(Ticket.customer_id == customer_id).all()
        return [_ticket_to_dict(t) for t in rows]


def create_ticket(customer_id: str, order_id: str, subject: str, description: str, priority: str = "MEDIUM"):
    with get_session() as s:
        ticket_id = f"T{next(_ticket_ids)}"
        t = Ticket(
            ticket_id=ticket_id,
            customer_id=customer_id,
            order_id=order_id,
            subject=subject,
            description=description,
            priority=priority,
            status="OPEN",
        )
        s.add(t)
        s.commit()
        return _ticket_to_dict(t)


def cancel_order(order_id: str):
    with get_session() as s:
        o = s.get(Order, order_id)
        if not o:
            return None
        if o.status in ("SHIPPED", "DELIVERED"):
            return {"success": False, "reason": f"Order already {o.status}, cannot cancel"}
        o.status = "CANCELLED"
        s.commit()
        return {"success": True, "reason": "Order cancelled"}


# ---------------------------------------------------------------------
# Conversations / messages (persisted multi-turn memory)
# ---------------------------------------------------------------------

def create_conversation(customer_id: str, title: str = "New conversation"):
    with get_session() as s:
        conv = Conversation(customer_id=customer_id, title=title)
        s.add(conv)
        s.commit()
        return conv.id


def list_conversations(customer_id: str):
    with get_session() as s:
        rows = (
            s.query(Conversation)
            .filter(Conversation.customer_id == customer_id)
            .order_by(Conversation.created_at.desc())
            .all()
        )
        return [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in rows]


def get_conversation(conversation_id: int, customer_id: str):
    with get_session() as s:
        conv = s.get(Conversation, conversation_id)
        if not conv or conv.customer_id != customer_id:
            return None
        return {"id": conv.id, "title": conv.title}


def get_messages(conversation_id: int):
    with get_session() as s:
        rows = s.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.id).all()
        return [
            {"role": m.role, "content": m.content, "tool_trace": m.tool_trace or []}
            for m in rows
        ]


def add_message(conversation_id: int, role: str, content: str, tool_trace: list | None = None):
    with get_session() as s:
        m = Message(conversation_id=conversation_id, role=role, content=content, tool_trace=tool_trace or [])
        s.add(m)
        # First human message becomes the conversation title.
        conv = s.get(Conversation, conversation_id)
        if conv and conv.title == "New conversation" and role == "human":
            conv.title = content[:60]
        s.commit()
