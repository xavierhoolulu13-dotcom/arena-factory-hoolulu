"""Factory brain — runs the full pipeline. Xavier is pinged on HIGH / CRITICAL only."""

from __future__ import annotations

from factory.agents import AGENTS, Pono, seed_if_empty
from factory.catalog import OFFERS
from factory.config import CONTRACT, PIPELINE_STAGES, PING_POLICY, VERSION
from factory.db import Store, utcnow
from factory.escalation import should_ping

STAGE_LABELS = {
    "discover": "Discover",
    "attract": "Attract",
    "capture": "Capture",
    "qualify": "Qualify",
    "pitch": "Pitch",
    "close": "Close",
    "verify": "Verify",
    "deliver": "Deliver",
    "retain": "Retain",
}


class FactoryBrain:
    def __init__(self, store: Store | None = None):
        self.store = store or Store()
        seed_if_empty(self.store)

    def tick(self) -> dict:
        """One full pipeline cycle. Social → leads → sales → delivery → retain → watch."""
        actions: list[dict] = []
        # Order is the pipeline. Watch runs last so it can see everything.
        for name in ("kai", "echo", "cass", "pono", "aloha", "watch"):
            actions.extend(AGENTS[name].tick(self.store))
        ticks = int(self.store.get_state("ticks", "0") or 0) + 1
        self.store.set_state("ticks", str(ticks))
        self.store.log_event("brain", "tick", f"Cycle {ticks} · {len(actions)} actions")
        pings = self.open_pings()
        return {
            "ticks": ticks,
            "actions": actions,
            "pings": pings,
            "ping_policy": PING_POLICY,
        }

    def open_pings(self) -> list[dict]:
        rows = self.store.list("escalations", "ping=1 AND status='open'", limit=50)
        return rows

    def snapshot(self) -> dict:
        leads = self.store.list("leads", limit=200)
        posts = self.store.list("posts", limit=80)
        payments = self.store.list("payments", limit=80)
        deliveries = self.store.list("deliveries", limit=80)
        escalations = self.store.list("escalations", limit=80)
        events = self.store.list("events", limit=80)
        messages = self.store.list("messages", limit=120)

        pipeline = []
        for stage in PIPELINE_STAGES:
            pipeline.append(
                {
                    "id": stage,
                    "label": STAGE_LABELS[stage],
                    "count": sum(1 for l in leads if l["stage"] == stage),
                    "leads": [l for l in leads if l["stage"] == stage],
                }
            )

        revenue_pending = sum(p["amount"] for p in payments if p["status"] == "pending")
        revenue_complete = sum(p["amount"] for p in payments if p["status"] == "complete")
        open_pings = [e for e in escalations if e["ping"] and e["status"] == "open"]

        return {
            "version": VERSION,
            "contract": CONTRACT,
            "operator": self.store.get_state("operator", "Xavier Hoolulu"),
            "autopilot": self.store.get_state("autopilot", "1") == "1",
            "ticks": int(self.store.get_state("ticks", "0") or 0),
            "ping_policy": PING_POLICY,
            "kpis": {
                "leads": len(leads),
                "hot": sum(1 for l in leads if l["score"] == "hot"),
                "posts_queued": sum(1 for p in posts if p["status"] in {"queued", "scheduled"}),
                "posts_published": sum(1 for p in posts if p["status"] == "published"),
                "revenue_pending": revenue_pending,
                "revenue_complete": revenue_complete,
                "open_pings": len(open_pings),
                "deliveries_running": sum(1 for d in deliveries if d["status"] == "running"),
            },
            "pipeline": pipeline,
            "leads": leads,
            "posts": posts,
            "payments": payments,
            "deliveries": deliveries,
            "escalations": escalations,
            "open_pings": open_pings,
            "events": events,
            "messages": messages,
            "offers": [
                {"sku": o.sku, "name": o.name, "price": o.price, "tier": o.tier, "pitch": o.pitch}
                for o in OFFERS.values()
            ],
            "agents": [
                {"id": k, "name": v.name, "role": v.role, "can_ping": k == "watch"}
                for k, v in AGENTS.items()
            ],
        }

    def set_autopilot(self, on: bool) -> None:
        self.store.set_state("autopilot", "1" if on else "0")

    def ack_escalation(self, ident: str) -> dict:
        row = self.store.get("escalations", ident)
        if not row:
            raise KeyError(ident)
        with self.store.session() as con:
            con.execute(
                "UPDATE escalations SET status='acked', acked_at=? WHERE id=?",
                (utcnow(), ident),
            )
        return self.store.get("escalations", ident) or row

    def verify_payment(self, payment_id: str, operator: str = "Xavier Hoolulu") -> dict:
        """Operator-only. Agents cannot mark payment complete."""
        pay = self.store.get("payments", payment_id)
        if not pay:
            raise KeyError(payment_id)
        self.store.update(
            "payments",
            payment_id,
            {"status": "complete", "verified_by": operator},
        )
        lead = self.store.get("leads", pay["lead_id"])
        if lead:
            self.store.update("leads", lead["id"], {"stage": "verify", "status": "paid"})
        with self.store.session() as con:
            con.execute(
                "UPDATE escalations SET status='acked', acked_at=? "
                "WHERE lead_id=? AND trigger='payment_needs_human_verify' AND status='open'",
                (utcnow(), pay["lead_id"]),
            )
        delivery = Pono().attempt(self.store, payment_id)
        self.store.log_event(
            "watch",
            "payment_verified",
            f"{operator} verified ${pay['amount']}",
            level="high",
            ping=False,
        )
        return {"payment": self.store.get("payments", payment_id), "delivery": delivery}


def should_notify(level: str) -> bool:
    return should_ping(level)
