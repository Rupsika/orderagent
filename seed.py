"""
seed.py

Creates order_support.db (SQLite) and seeds it with the same demo data
that used to live in mock_data.py, plus login passwords for the two
demo customers.

Run once:
    python seed.py
Safe to re-run — it skips seeding if customers already exist.
"""

from datetime import datetime, timedelta, timezone

from db import init_db, get_session, Customer, Order, Shipment
from security import hash_password

DEMO_PASSWORD = "password123"


def seed():
    init_db()
    now = datetime.now(timezone.utc)

    with get_session() as s:
        if s.query(Customer).count() > 0:
            print("DB already seeded, skipping.")
            return

        s.add_all([
            Customer(customer_id="C1024", name="Aditi Rao", email="aditi@example.com",
                      password_hash=hash_password(DEMO_PASSWORD)),
            Customer(customer_id="C2001", name="Marcus Webb", email="marcus@example.com",
                      password_hash=hash_password(DEMO_PASSWORD)),
        ])

        s.add_all([
            Order(order_id="ORD123", customer_id="C1024",
                  items=[{"name": "Wireless Earbuds", "qty": 1, "price": 2499}],
                  total=2499, status="SHIPPED", placed_at=now - timedelta(days=4)),
            Order(order_id="ORD124", customer_id="C1024",
                  items=[{"name": "Phone Case", "qty": 2, "price": 399}],
                  total=798, status="DELIVERED", placed_at=now - timedelta(days=10)),
            Order(order_id="ORD200", customer_id="C2001",
                  items=[{"name": "Desk Lamp", "qty": 1, "price": 1899}],
                  total=1899, status="PROCESSING", placed_at=now - timedelta(hours=6)),
        ])

        s.add_all([
            Shipment(
                order_id="ORD123", carrier="BlueDart", tracking_number="BD998877",
                status="IN_TRANSIT", eta=now + timedelta(days=1), last_update=now - timedelta(hours=14),
                history=[
                    {"ts": (now - timedelta(days=3)).isoformat(), "event": "Picked up from warehouse"},
                    {"ts": (now - timedelta(days=2)).isoformat(), "event": "Arrived at regional hub"},
                    {"ts": (now - timedelta(hours=14)).isoformat(), "event": "Out for delivery attempt — failed, no one available"},
                ],
            ),
            Shipment(
                order_id="ORD124", carrier="Delhivery", tracking_number="DL445566",
                status="DELIVERED", eta=now - timedelta(days=8), last_update=now - timedelta(days=8),
                history=[
                    {"ts": (now - timedelta(days=8)).isoformat(), "event": "Delivered — signed by recipient"},
                ],
            ),
        ])

        s.commit()

    print("Seeded order_support.db with demo customers:")
    print(f"  aditi@example.com  / {DEMO_PASSWORD}  (customer C1024 — has ORD123, ORD124)")
    print(f"  marcus@example.com / {DEMO_PASSWORD}  (customer C2001 — has ORD200)")


if __name__ == "__main__":
    seed()
