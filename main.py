"""
main.py

FastAPI backend: real auth (JWT + hashed passwords), SQLite-backed
customer/order/ticket data, and persisted multi-turn conversations
around the LangGraph agent.

Run:
    python seed.py            # once, to create + seed order_support.db
    uvicorn main:app --reload

Then:
    curl -X POST http://localhost:8000/auth/login \\
      -H "Content-Type: application/json" \\
      -d '{"email": "aditi@example.com", "password": "password123"}'

    curl -X POST http://localhost:8000/chat \\
      -H "Content-Type: application/json" \\
      -H "Authorization: Bearer <token>" \\
      -d '{"message": "Where is my order ORD123?"}'
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

import crud
from agent import run_agent
from security import create_access_token, decode_access_token

app = FastAPI(title="Order & Delivery Support Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()


def get_current_customer_id(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    customer_id = decode_access_token(creds.credentials)
    if not customer_id or not crud.get_customer(customer_id):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return customer_id


# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_id: str
    name: str


@app.post("/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    if crud.get_customer_by_email(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    customer_id = crud.next_customer_id()
    customer = crud.create_customer(customer_id, req.name, req.email, req.password)
    token = create_access_token(customer_id)
    return TokenResponse(access_token=token, customer_id=customer["customer_id"], name=customer["name"])


@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    customer = crud.authenticate(req.email, req.password)
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(customer["customer_id"])
    return TokenResponse(access_token=token, customer_id=customer["customer_id"], name=customer["name"])


@app.get("/me")
def me(customer_id: str = Depends(get_current_customer_id)):
    return crud.get_customer(customer_id)


# ---------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------

@app.get("/conversations")
def list_conversations(customer_id: str = Depends(get_current_customer_id)):
    return crud.list_conversations(customer_id)


@app.post("/conversations")
def new_conversation(customer_id: str = Depends(get_current_customer_id)):
    conv_id = crud.create_conversation(customer_id)
    return {"id": conv_id}


@app.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: int, customer_id: str = Depends(get_current_customer_id)):
    if not crud.get_conversation(conversation_id, customer_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return crud.get_messages(conversation_id)


# ---------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    response: str
    tool_trace: list[str]
    conversation_id: int


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, customer_id: str = Depends(get_current_customer_id)):
    if req.conversation_id is not None:
        if not crud.get_conversation(req.conversation_id, customer_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = req.conversation_id
    else:
        conversation_id = crud.create_conversation(customer_id)

    history = crud.get_messages(conversation_id)
    result = run_agent(customer_id, req.message, history=history)

    crud.add_message(conversation_id, "human", req.message)
    crud.add_message(conversation_id, "ai", result["response"], tool_trace=result["tool_trace"])

    return ChatResponse(response=result["response"], tool_trace=result["tool_trace"], conversation_id=conversation_id)


@app.get("/health")
def health():
    return {"status": "ok"}
