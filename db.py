"""
db.py

Real persistence layer: SQLite via SQLAlchemy. Replaces mock_data.py.

Tables: customers, orders, shipments, tickets, conversations, messages.
Run `python seed.py` once to create the DB file and seed demo data.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, ForeignKey, JSON, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///./order_support.db")

engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    orders = relationship("Order", back_populates="customer")
    tickets = relationship("Ticket", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False, index=True)
    items = Column(JSON, nullable=False)
    total = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    placed_at = Column(DateTime, default=utcnow)

    customer = relationship("Customer", back_populates="orders")
    shipment = relationship("Shipment", back_populates="order", uselist=False)
    tickets = relationship("Ticket", back_populates="order")


class Shipment(Base):
    __tablename__ = "shipments"

    order_id = Column(String, ForeignKey("orders.order_id"), primary_key=True)
    carrier = Column(String, nullable=False)
    tracking_number = Column(String, nullable=False)
    status = Column(String, nullable=False)
    eta = Column(DateTime)
    last_update = Column(DateTime)
    history = Column(JSON, default=list)

    order = relationship("Order", back_populates="shipment")


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False, index=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String, default="MEDIUM")
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=utcnow)

    customer = relationship("Customer", back_populates="tickets")
    order = relationship("Order", back_populates="tickets")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False, index=True)
    title = Column(String, default="New conversation")
    created_at = Column(DateTime, default=utcnow)

    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.id")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "human" | "ai"
    content = Column(Text, nullable=False)
    tool_trace = Column(JSON, default=list)
    created_at = Column(DateTime, default=utcnow)

    conversation = relationship("Conversation", back_populates="messages")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
