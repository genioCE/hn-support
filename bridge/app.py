from base64 import b64encode
import os, httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()
ZAMMAD = os.getenv("ZAMMAD_BASE_URL", "http://zammad:8080").rstrip("/")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN")
OP = os.getenv("OPENPROJECT_BASE_URL", "http://openproject:8080").rstrip("/")
OP_KEY = os.getenv("OPENPROJECT_API_KEY")
LLM = os.getenv("LLM_BASE_URL", "http://llm:8000/v1").rstrip("/")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ticket.create")
async def ticket_create(payload: dict):
    """payload: {title, body, customer_email, group}"""
    if not ZAMMAD_TOKEN:
        raise HTTPException(500, "ZAMMAD_TOKEN not set")
    data = {
        "title": payload.get("title", "New ticket"),
        "group": payload.get("group", "Users"),
        "customer": payload.get("customer_email"),
        "article": {
            "subject": payload.get("title", "New ticket"),
            "body": payload.get("body", ""),
            "type": "email",
            "internal": False,
            "sender": "Customer"
        }
    }
    headers = {
        "Authorization": f"Token token={ZAMMAD_TOKEN}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as cx:
        r = await cx.post(f"{ZAMMAD}/api/v1/tickets", headers=headers, json=data, timeout=30)
    if r.status_code >= 300:
        raise HTTPException(r.status_code, r.text)
    return r.json()

@app.post("/issue.create")
async def issue_create(payload: dict):
    """payload: {project_id:int, subject:str, description:str, type_id:int}"""
    if not OP_KEY:
        raise HTTPException(500, "OPENPROJECT_API_KEY not set")
    basic = b64encode(f"apikey:{OP_KEY}".encode()).decode()
    headers = {"Authorization": f"Basic {basic}", "Content-Type": "application/json"}
    proj = payload.get("project_id")
    type_id = payload.get("type_id", 1)
    data = {
        "subject": payload.get("subject", "New issue"),
        "description": {"raw": payload.get("description", "")},
        "_links": {
            "project": {"href": f"/api/v3/projects/{proj}"},
            "type": {"href": f"/api/v3/types/{type_id}"}
        }
    }
    async with httpx.AsyncClient() as cx:
        r = await cx.post(f"{OP}/api/v3/work_packages", headers=headers, json=data, timeout=30)
    if r.status_code >= 300:
        raise HTTPException(r.status_code, r.text)
    return r.json()

@app.post("/chat")
async def chat(messages: dict):
    """Pass-through to local vLLM OpenAI-compatible /chat/completions."""
    async with httpx.AsyncClient() as cx:
        r = await cx.post(f"{LLM}/chat/completions", json=messages, timeout=120)
    if r.status_code >= 300:
        raise HTTPException(r.status_code, r.text)
    return r.json()
