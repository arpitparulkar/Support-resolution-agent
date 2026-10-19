from __future__ import annotations

from datetime import datetime, timezone

from backend.app.core.security import hash_password
from backend.app.db.database import SessionLocal, init_db
from backend.app.db.models import Order, Ticket, User


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        if not db.query(User).filter_by(email="admin@example.com").first():
            admin = User(
                email="admin@example.com",
                full_name="Admin User",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)
            db.flush()
        if not db.query(User).filter_by(email="customer@example.com").first():
            customer = User(
                email="customer@example.com",
                full_name="Priya Carter",
                password_hash=hash_password("password123"),
                role="customer",
            )
            db.add(customer)
            db.flush()

        sample_orders = [
            {
                "order_id": "ORD123",
                "customer_name": "Rahul",
                "product": "Headphones",
                "status": "Shipped",
                "order_date": "2026-10-12",
                "expected_delivery": "2026-10-20",
                "delivered_date": None,
                "amount": 89.99,
                "refund_status": "Not requested",
            },
            {
                "order_id": "ORD124",
                "customer_name": "Priya",
                "product": "Keyboard",
                "status": "Delivered",
                "order_date": "2026-10-01",
                "expected_delivery": "2026-10-10",
                "delivered_date": "2026-10-11",
                "amount": 129.99,
                "refund_status": "Not requested",
            },
            {
                "order_id": "ORD125",
                "customer_name": "Aisha",
                "product": "Wireless Mouse",
                "status": "Delivered",
                "order_date": "2026-09-20",
                "expected_delivery": "2026-09-25",
                "delivered_date": "2026-09-24",
                "amount": 34.5,
                "refund_status": "Refunded",
            },
            {
                "order_id": "ORD126",
                "customer_name": "Dev",
                "product": "USB-C Hub",
                "status": "Cancelled",
                "order_date": "2026-10-08",
                "expected_delivery": "2026-10-15",
                "delivered_date": None,
                "amount": 49.0,
                "refund_status": "Not requested",
            },
            {
                "order_id": "ORD127",
                "customer_name": "Elena",
                "product": "Wi-Fi Router",
                "status": "Shipped",
                "order_date": "2026-10-01",
                "expected_delivery": "2026-10-12",
                "delivered_date": None,
                "amount": 79.0,
                "refund_status": "Not requested",
            },
            {
                "order_id": "ORD128",
                "customer_name": "Omar",
                "product": "Office Chair",
                "status": "Delivered",
                "order_date": "2026-08-25",
                "expected_delivery": "2026-09-01",
                "delivered_date": "2026-09-02",
                "amount": 219.0,
                "refund_status": "Not requested",
            },
            {
                "order_id": "ORD129",
                "customer_name": "Maya",
                "product": "Laptop Stand",
                "status": "Processing",
                "order_date": "2026-10-15",
                "expected_delivery": "2026-10-22",
                "delivered_date": None,
                "amount": 42.0,
                "refund_status": "Not requested",
            },
        ]
        for item in sample_orders:
            if not db.query(Order).filter_by(order_id=item["order_id"]).first():
                db.add(Order(**item))

        if not db.query(Ticket).first():
            db.add(
                Ticket(
                    ticket_id="TKT101",
                    issue="Duplicate payment reported by customer",
                    priority="high",
                    status="open",
                    order_id="ORD124",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Database seeded.")
