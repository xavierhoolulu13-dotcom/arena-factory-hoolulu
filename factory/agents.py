"""Factory agents. They run the pipeline. Only Watch may ping Xavier."""

from __future__ import annotations

import itertools
import random
from datetime import datetime, timedelta, timezone

from factory.catalog import (
    HASHTAGS,
    OFFERS,
    PAYMENT_INSTRUCTIONS,
    PLATFORMS,
    recommend_sku,
    upsell_sku,
)
from factory.db import Store, new_id, utcnow
from factory.escalation import classify_event

ISLANDS = ("Oahu", "Maui", "Big Island", "Kauai", "Molokai")


# ---------------------------------------------------------------------------
# Kai — Social Media Promoter
# ---------------------------------------------------------------------------

_HOOKS = {
    "instagram": [
        "Your cousin already Googled a plumber today.",
        "If your shop is not on the phone, you are losing jobs to a Facebook page from 2014.",
        "Honolulu does not wait. Neither should your website.",
    ],
    "tiktok": [
        "POV: you still tell customers to DM for a quote.",
        "Stop posting sunsets. Start booking jobs.",
        "3 seconds. That's how long a tourist has to tap Call.",
    ],
    "facebook": [
        "Local shops: your next job is searching right now.",
        "We build sites for Hawaii trades. You keep the tools, we keep the leads.",
        "A dead website is a closed sign that never comes off.",
    ],
    "x": [
        "808 shops leaking jobs every day they stay invisible.",
        "Free site this week. Prove the work. Then we talk.",
        "Agents run the pipeline. You only get pinged when it is on fire.",
    ],
    "linkedin": [
        "Most local service businesses in Hawaii still have no booking path.",
        "We install a full sales pipeline — attract, close, deliver — then stay quiet.",
        "XKSH808: digital services for Hawaii operators who are done waiting on agencies.",
    ],
    "whatsapp": [
        "Brah you need a site that actually rings the phone.",
        "We can have you live this week. Free site, no fluff.",
        "Booked two jobs off a page we shipped Tuesday. You next?",
    ],
    "google_business": [
        "People searching 'near me' cannot find you.",
        "We clean up Google, stand up the site, turn on call tracking.",
        "Rank local. Answer fast. That's the whole game.",
    ],
}

_BODIES = {
    "free-site": "Free Website — live this week. Click-to-call, hours, map. We prove it, you keep us.",
    "souper-bot": "Souper Agent Bot $197 — answers at 2am, books the job, texts you the lead.",
    "starter": "Starter Pack $297 — site + local SEO so Oahu customers find you before the other guy.",
    "pro": "Pro Build $497 — funnel, booking, follow-up. The shop runs while you are on a job.",
    "kkos": "KK OS Setup $997 — full business OS. Leads, sales, delivery, money. We install. You operate.",
}


class Kai:
    name = "kai"
    role = "Social Media Promoter"

    def generate(self, platform: str, sku: str) -> dict:
        if platform not in PLATFORMS:
            raise ValueError(f"unknown platform {platform}")
        if sku not in OFFERS:
            raise ValueError(f"unknown sku {sku}")
        offer = OFFERS[sku]
        hook = random.choice(_HOOKS[platform])
        caption = (
            f"{hook}\n\n{_BODIES[sku]}\n\n"
            f"{offer.pitch}\n\n{HASHTAGS}"
        )
        cta = {
            "free-site": "Reply SITE and we stand it up this week.",
            "souper-bot": "Reply BOT — $197, live on your page.",
            "starter": "Reply STARTER — $297 web + SEO.",
            "pro": "Reply PRO — $497 full funnel + booking.",
            "kkos": "Reply OS — $997 we install the whole machine.",
        }[sku]
        return {
            "platform": platform,
            "sku": sku,
            "hook": hook,
            "caption": caption,
            "cta": cta,
        }

    def queue(self, store: Store, platform: str, sku: str) -> dict:
        content = self.generate(platform, sku)
        when = datetime.now(timezone.utc) + timedelta(hours=random.randint(1, 36))
        row = {
            "id": new_id("post_"),
            **content,
            "status": "queued",
            "scheduled_for": when.replace(microsecond=0).isoformat(),
            "created_at": utcnow(),
        }
        store.insert("posts", row)
        store.log_event(self.name, "post_queued", f"{platform} · {OFFERS[sku].name}", payload=content)
        return row

    def tick(self, store: Store) -> list[dict]:
        """Keep a healthy calendar. Never pings Xavier."""
        actions = []
        queued = store.count("posts", "status IN ('queued','scheduled')")
        if queued < 8:
            platform = random.choice(PLATFORMS)
            sku = random.choice(list(OFFERS))
            post = self.queue(store, platform, sku)
            actions.append({"agent": self.name, "action": "queued_post", "id": post["id"]})
        due = store.list("posts", "status='queued'", order="scheduled_for ASC", limit=2)
        now = utcnow()
        for post in due:
            if post["scheduled_for"] and post["scheduled_for"] <= now:
                store.update("posts", post["id"], {"status": "published"})
                store.log_event(
                    self.name,
                    "post_published",
                    f"Published {post['platform']} for {post['sku']}",
                )
                actions.append({"agent": self.name, "action": "published", "id": post["id"]})
        return actions


# ---------------------------------------------------------------------------
# Echo — Lead Engine
# ---------------------------------------------------------------------------

HOT_WORDS = ("asap", "ready to pay", "need now", "this week", "budget", "how much", "book it")
WARM_WORDS = ("interested", "quote", "looking for", "can you", "website", "seo", "chatbot")


def score_inbound(text: str) -> tuple[str, int]:
    t = (text or "").lower()
    urgency = 2
    if any(w in t for w in HOT_WORDS):
        urgency = 5 if "asap" in t or "need now" in t else 4
        return "hot", urgency
    if any(w in t for w in WARM_WORDS):
        return "warm", 3
    return "cold", 1


class Echo:
    name = "echo"
    role = "Lead Engine"

    def ingest(self, store: Store, *, name: str, business: str, island: str, channel: str, message: str) -> dict:
        score, urgency = score_inbound(message)
        sku = recommend_sku(message)
        now = utcnow()
        lead = {
            "id": new_id("lead_"),
            "name": name,
            "business": business,
            "island": island,
            "channel": channel,
            "need": message[:280],
            "score": score,
            "urgency": urgency,
            "status": "scored",
            "stage": "qualify",
            "sku": sku,
            "last_inbound": message,
            "created_at": now,
            "updated_at": now,
        }
        store.insert("leads", lead)
        store.insert(
            "messages",
            {
                "id": new_id("msg_"),
                "lead_id": lead["id"],
                "role": "lead",
                "body": message,
                "created_at": now,
            },
        )
        store.log_event(
            self.name,
            "lead_scored",
            f"{business} → {score.upper()} · {OFFERS[sku].name}",
            payload={"lead_id": lead["id"], "score": score},
        )
        return lead

    def tick(self, store: Store) -> list[dict]:
        # New inbound already sits in 'new'; score anything leftover.
        actions = []
        for lead in store.list("leads", "status='new'", limit=20):
            score, urgency = score_inbound(lead.get("last_inbound") or lead.get("need", ""))
            sku = lead.get("sku") or recommend_sku(lead.get("need", ""))
            store.update(
                "leads",
                lead["id"],
                {"status": "scored", "stage": "qualify", "score": score, "urgency": urgency, "sku": sku},
            )
            actions.append({"agent": self.name, "action": "scored", "id": lead["id"]})
        return actions


# ---------------------------------------------------------------------------
# Cass — Sales Closer
# ---------------------------------------------------------------------------

class Cass:
    name = "cass"
    role = "Sales Closer"

    def pitch(self, store: Store, lead: dict) -> dict:
        sku = lead.get("sku") or recommend_sku(lead.get("need", ""))
        offer = OFFERS[sku]
        nxt = upsell_sku(sku)
        upsell = f" After that, most shops step up to {OFFERS[nxt].name} (${OFFERS[nxt].price})." if nxt else ""
        body = (
            f"Aloha {lead['name'].split()[0]}, it's Cass with XKSH808.\n\n"
            f"For {lead['business']} on {lead['island']}, the right move is {offer.name} "
            f"(${offer.price}). {offer.pitch}\n\n"
            f"{PAYMENT_INSTRUCTIONS}{upsell}"
        )
        store.insert(
            "messages",
            {
                "id": new_id("msg_"),
                "lead_id": lead["id"],
                "role": "cass",
                "body": body,
                "created_at": utcnow(),
            },
        )
        store.update("leads", lead["id"], {"status": "pitched", "stage": "pitch", "sku": sku})
        store.log_event(self.name, "pitch_sent", f"Pitched {offer.name} to {lead['business']}")
        return {"lead_id": lead["id"], "sku": sku, "body": body}

    def open_payment(self, store: Store, lead: dict) -> dict:
        sku = lead["sku"] or "starter"
        offer = OFFERS[sku]
        now = utcnow()
        payment = {
            "id": new_id("pay_"),
            "lead_id": lead["id"],
            "sku": sku,
            "amount": offer.price,
            "status": "pending",
            "verified_by": None,
            "created_at": now,
            "updated_at": now,
        }
        store.insert("payments", payment)
        store.update("leads", lead["id"], {"status": "closing", "stage": "close"})
        store.log_event(self.name, "payment_pending", f"{lead['business']} · ${offer.price} pending")
        return payment

    def handle_reply(self, store: Store, lead_id: str, message: str) -> dict:
        lead = store.get("leads", lead_id)
        if not lead:
            raise KeyError(lead_id)
        store.insert(
            "messages",
            {
                "id": new_id("msg_"),
                "lead_id": lead_id,
                "role": "lead",
                "body": message,
                "created_at": utcnow(),
            },
        )
        decision = classify_event("inbound_reply", message)
        store.update("leads", lead_id, {"last_inbound": message})

        if decision.ping:
            return {"handled": "escalated", "decision": decision.as_dict(), "lead": lead}

        t = message.lower()
        if any(w in t for w in ("yes", "let's go", "lets go", "book it", "send payment", "i'll take", "ill take", "ready")):
            payment = self.open_payment(store, lead)
            ack = (
                f"Locked in {OFFERS[lead['sku']].name} at ${OFFERS[lead['sku']].price}. "
                f"{PAYMENT_INSTRUCTIONS}"
            )
            store.insert(
                "messages",
                {
                    "id": new_id("msg_"),
                    "lead_id": lead_id,
                    "role": "cass",
                    "body": ack,
                    "created_at": utcnow(),
                },
            )
            return {"handled": "closing", "payment": payment, "decision": decision.as_dict()}

        if any(w in t for w in ("too much", "expensive", "cheaper", "free")):
            store.update("leads", lead_id, {"sku": "free-site", "stage": "pitch"})
            return {**self.pitch(store, {**lead, "sku": "free-site"}), "handled": "downsell"}

        pitched = self.pitch(store, lead)
        return {**pitched, "handled": "replied", "decision": decision.as_dict()}

    def tick(self, store: Store) -> list[dict]:
        actions = []
        for lead in store.list("leads", "status='scored' AND score IN ('hot','warm')", limit=8):
            self.pitch(store, lead)
            actions.append({"agent": self.name, "action": "pitched", "id": lead["id"]})
        return actions


# ---------------------------------------------------------------------------
# Pono — Delivery (zero-trust)
# ---------------------------------------------------------------------------

class Pono:
    name = "pono"
    role = "Delivery"

    def attempt(self, store: Store, payment_id: str) -> dict:
        payment = store.get("payments", payment_id)
        if not payment:
            raise KeyError(payment_id)
        lead = store.get("leads", payment["lead_id"])
        now = utcnow()

        if payment["status"] != "complete":
            delivery = {
                "id": new_id("del_"),
                "lead_id": payment["lead_id"],
                "payment_id": payment_id,
                "sku": payment["sku"],
                "status": "blocked",
                "summary": (
                    f"Zero-trust gate blocked delivery. Payment is '{payment['status']}', "
                    "not human-verified complete."
                ),
                "created_at": now,
                "updated_at": now,
            }
            store.insert("deliveries", delivery)
            store.log_event(
                self.name,
                "delivery_blocked",
                f"Blocked {lead['business'] if lead else payment_id}",
                level="medium",
            )
            return delivery

        offer = OFFERS[payment["sku"]]
        delivery = {
            "id": new_id("del_"),
            "lead_id": payment["lead_id"],
            "payment_id": payment_id,
            "sku": payment["sku"],
            "status": "running",
            "summary": offer.deliverable,
            "created_at": now,
            "updated_at": now,
        }
        store.insert("deliveries", delivery)
        if lead:
            store.update("leads", lead["id"], {"status": "client", "stage": "deliver"})
        store.log_event(self.name, "delivery_started", f"{offer.name} for {lead['business'] if lead else '?'}")
        return delivery

    def tick(self, store: Store) -> list[dict]:
        actions = []
        for pay in store.list("payments", "status='complete'", limit=20):
            existing = store.list("deliveries", "payment_id=?", args=(pay["id"],), limit=1)
            if existing:
                if existing[0]["status"] == "running":
                    store.update("deliveries", existing[0]["id"], {"status": "done"})
                    lead = store.get("leads", pay["lead_id"])
                    if lead:
                        store.update("leads", lead["id"], {"status": "retained", "stage": "retain"})
                    actions.append({"agent": self.name, "action": "completed", "id": existing[0]["id"]})
                continue
            d = self.attempt(store, pay["id"])
            actions.append({"agent": self.name, "action": d["status"], "id": d["id"]})
        return actions


# ---------------------------------------------------------------------------
# Aloha — Retention
# ---------------------------------------------------------------------------

class Aloha:
    name = "aloha"
    role = "Retention"

    def tick(self, store: Store) -> list[dict]:
        actions = []
        for lead in store.list("leads", "status='retained'", limit=10):
            nxt = upsell_sku(lead.get("sku") or "starter")
            if not nxt:
                continue
            # Quiet upsell — never a ping.
            store.log_event(
                self.name,
                "upsell_queued",
                f"{lead['business']} → {OFFERS[nxt].name}",
            )
            actions.append({"agent": self.name, "action": "upsell", "id": lead["id"]})
        stalled = store.list("leads", "status='pitched' AND score='warm'", limit=5)
        for lead in stalled:
            store.log_event(self.name, "follow_up", f"Nudge {lead['business']}", level="medium")
            actions.append({"agent": self.name, "action": "nudge", "id": lead["id"]})
        return actions


# ---------------------------------------------------------------------------
# Watch — Monitor + the only agent allowed to ping
# ---------------------------------------------------------------------------

class Watch:
    name = "watch"
    role = "Monitor + Escalation Gate"

    def raise_event(
        self,
        store: Store,
        *,
        kind: str,
        title: str,
        detail: str,
        lead_id: str | None = None,
        text: str = "",
    ) -> dict:
        decision = classify_event(kind, text or detail)
        esc = None
        if decision.ping:
            esc = {
                "id": new_id("esc_"),
                "level": decision.level,
                "trigger": decision.trigger,
                "ping": 1,
                "title": title,
                "detail": detail,
                "lead_id": lead_id,
                "status": "open",
                "created_at": utcnow(),
                "acked_at": None,
            }
            store.insert("escalations", esc)
        store.log_event(
            self.name,
            decision.trigger,
            title,
            level=decision.level,
            ping=decision.ping,
            payload={"lead_id": lead_id, "reason": decision.reason},
        )
        return {"decision": decision.as_dict(), "escalation": esc}

    def tick(self, store: Store) -> list[dict]:
        actions = []
        # Pending payments older than now always need Xavier — HIGH.
        for pay in store.list("payments", "status='pending'", limit=20):
            existing = store.list(
                "escalations",
                "trigger='payment_needs_human_verify' AND lead_id=? AND status='open'",
                args=(pay["lead_id"],),
                limit=1,
            )
            if existing:
                continue
            lead = store.get("leads", pay["lead_id"])
            name = lead["business"] if lead else pay["lead_id"]
            result = self.raise_event(
                store,
                kind="payment_needs_human_verify",
                title=f"Verify ${pay['amount']} from {name}",
                detail=(
                    f"Zero-trust gate: {OFFERS[pay['sku']].name} is pending. "
                    "Mark complete only after you see Cash App / PayPal / Stripe."
                ),
                lead_id=pay["lead_id"],
            )
            actions.append({"agent": self.name, "action": "ping" if result["decision"]["ping"] else "log", "id": pay["id"]})

        # Scan latest inbound for hostile / legal / refund language.
        for msg in store.list("messages", "role='lead'", limit=15):
            decision = classify_event("inbound_reply", msg["body"])
            if not decision.ping:
                continue
            existing = store.list(
                "escalations",
                "lead_id=? AND trigger=? AND status='open'",
                args=(msg["lead_id"], decision.trigger),
                limit=1,
            )
            if existing:
                continue
            lead = store.get("leads", msg["lead_id"])
            self.raise_event(
                store,
                kind=decision.trigger,
                title=f"{decision.level.upper()} · {lead['business'] if lead else msg['lead_id']}",
                detail=msg["body"],
                lead_id=msg["lead_id"],
                text=msg["body"],
            )
            actions.append({"agent": self.name, "action": "ping", "id": msg["id"]})
        return actions


AGENTS = {
    "kai": Kai(),
    "echo": Echo(),
    "cass": Cass(),
    "pono": Pono(),
    "aloha": Aloha(),
    "watch": Watch(),
}


SEED_LEADS = [
    {
        "name": "Keoni Silva",
        "business": "Island Plumbing Co",
        "island": "Oahu",
        "channel": "instagram",
        "message": "Need a website this week, ready to pay, people can't find us on Google.",
    },
    {
        "name": "Malia Kealoha",
        "business": "Kailua Cleaning Crew",
        "island": "Oahu",
        "channel": "facebook",
        "message": "Looking for a chatbot that books jobs after hours.",
    },
    {
        "name": "Tua Rangi",
        "business": "Wahiawa Auto Repair",
        "island": "Oahu",
        "channel": "whatsapp",
        "message": "Can you do SEO? Quotes keep going to the other shop.",
    },
    {
        "name": "Aunty Lani",
        "business": "North Shore Landscaping",
        "island": "Oahu",
        "channel": "tiktok",
        "message": "Just looking maybe later.",
    },
    {
        "name": "Ikaika Mendes",
        "business": "Maui Roofing Pros",
        "island": "Maui",
        "channel": "google_business",
        "message": "Need booking + funnel ASAP we are slammed and missing calls.",
    },
    {
        "name": "Pua Nakamura",
        "business": "Big Island Pest Control",
        "island": "Big Island",
        "channel": "instagram",
        "message": "Interested in a site. How much?",
    },
]


def seed_if_empty(store: Store) -> None:
    if store.count("leads") > 0:
        return
    echo, kai, cass = Echo(), Kai(), Cass()
    store.set_state("autopilot", "1")
    store.set_state("ticks", "0")
    store.set_state("operator", "Xavier Hoolulu")

    cycle = itertools.cycle(PLATFORMS)
    for sku in OFFERS:
        kai.queue(store, next(cycle), sku)
        kai.queue(store, next(cycle), sku)

    for raw in SEED_LEADS:
        echo.ingest(
            store,
            name=raw["name"],
            business=raw["business"],
            island=raw["island"],
            channel=raw["channel"],
            message=raw["message"],
        )

    # One deal already at the zero-trust gate so Xavier sees the only ping that matters.
    hot = store.list("leads", "business='Island Plumbing Co'", limit=1)[0]
    cass.pitch(store, hot)
    cass.open_payment(store, {**hot, "sku": hot["sku"] or "starter"})
    Watch().tick(store)
