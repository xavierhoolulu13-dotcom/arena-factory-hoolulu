from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from factory.agents import AGENTS, Cass, Echo, Kai
from factory.brain import FactoryBrain
from factory.catalog import OFFERS, PLATFORMS
from factory.config import STATIC_DIR

brain = FactoryBrain()
app = FastAPI(title="Arena Factory Hoolulu", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class LeadIn(BaseModel):
    name: str
    business: str
    island: str = "Oahu"
    channel: str = "instagram"
    message: str


class ReplyIn(BaseModel):
    message: str


class PostIn(BaseModel):
    platform: str
    sku: str


class AutopilotIn(BaseModel):
    on: bool


class VerifyIn(BaseModel):
    operator: str = Field(default="Xavier Hoolulu")


@app.get("/")
def index():
    page = STATIC_DIR / "index.html"
    if not page.exists():
        raise HTTPException(500, "frontend missing")
    return FileResponse(page)


@app.get("/api/health")
def health():
    return {"ok": True, "factory": "arena-factory-hoolulu", "ping_policy": "HIGH_AND_CRITICAL_ONLY"}


@app.get("/api/state")
def state():
    return brain.snapshot()


@app.post("/api/tick")
def tick():
    return brain.tick()


@app.post("/api/autopilot")
def autopilot(body: AutopilotIn):
    brain.set_autopilot(body.on)
    return {"autopilot": body.on}


@app.post("/api/leads")
def create_lead(body: LeadIn):
    lead = Echo().ingest(
        brain.store,
        name=body.name,
        business=body.business,
        island=body.island,
        channel=body.channel,
        message=body.message,
    )
    AGENTS["watch"].raise_event(
        brain.store,
        kind="inbound_reply",
        title=f"Inbound · {body.business}",
        detail=body.message,
        lead_id=lead["id"],
        text=body.message,
    )
    return lead


@app.post("/api/leads/{lead_id}/reply")
def reply(lead_id: str, body: ReplyIn):
    try:
        result = Cass().handle_reply(brain.store, lead_id, body.message)
    except KeyError:
        raise HTTPException(404, "lead not found") from None
    AGENTS["watch"].raise_event(
        brain.store,
        kind="inbound_reply",
        title=f"Reply · {lead_id}",
        detail=body.message,
        lead_id=lead_id,
        text=body.message,
    )
    return result


@app.post("/api/social/generate")
def generate_post(body: PostIn):
    if body.platform not in PLATFORMS:
        raise HTTPException(400, f"platform must be one of {PLATFORMS}")
    if body.sku not in OFFERS:
        raise HTTPException(400, f"sku must be one of {tuple(OFFERS)}")
    return Kai().queue(brain.store, body.platform, body.sku)


@app.post("/api/social/{post_id}/publish")
def publish_post(post_id: str):
    post = brain.store.get("posts", post_id)
    if not post:
        raise HTTPException(404, "post not found")
    brain.store.update("posts", post_id, {"status": "published"})
    return brain.store.get("posts", post_id)


@app.post("/api/escalations/{esc_id}/ack")
def ack(esc_id: str):
    try:
        return brain.ack_escalation(esc_id)
    except KeyError:
        raise HTTPException(404, "escalation not found") from None


@app.post("/api/payments/{payment_id}/verify")
def verify(payment_id: str, body: VerifyIn | None = None):
    operator = body.operator if body else "Xavier Hoolulu"
    try:
        return brain.verify_payment(payment_id, operator=operator)
    except KeyError:
        raise HTTPException(404, "payment not found") from None


@app.get("/api/contract")
def contract():
    return brain.snapshot()["contract"]


def create_app() -> FastAPI:
    return app
