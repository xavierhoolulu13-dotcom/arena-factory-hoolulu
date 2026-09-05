from pathlib import Path

from factory.agents import Cass, Echo, Kai, Pono, Watch, seed_if_empty
from factory.brain import FactoryBrain
from factory.catalog import OFFERS, recommend_sku
from factory.db import Store


def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "factory.db")


def test_seed_and_social_and_sales(tmp_path: Path):
    s = store(tmp_path)
    seed_if_empty(s)
    assert s.count("leads") >= 6
    assert s.count("posts") >= 8
    assert s.count("payments") >= 1
    pings = s.list("escalations", "ping=1 AND status='open'")
    assert pings, "zero-trust payment must ping Xavier"
    assert all(e["level"] in {"high", "critical"} for e in pings)


def test_recommend_offers():
    assert recommend_sku("need a chatbot after hours") == "souper-bot"
    assert recommend_sku("booking funnel ads") == "pro"
    assert recommend_sku("full operating system") == "kkos"
    assert recommend_sku("just a free site") == "free-site"


def test_kai_generates_every_platform(tmp_path: Path):
    kai = Kai()
    post = kai.generate("tiktok", "starter")
    assert "Starter Pack" in post["caption"] or "297" in post["caption"]
    assert post["hook"]
    queued = kai.queue(store(tmp_path), "instagram", "kkos")
    assert queued["status"] == "queued"
    assert queued["sku"] == "kkos"


def test_cass_pitches_and_never_completes_payment(tmp_path: Path):
    s = store(tmp_path)
    lead = Echo().ingest(
        s,
        name="Keoni",
        business="Island Plumbing Co",
        island="Oahu",
        channel="instagram",
        message="Need a website this week, ready to pay",
    )
    assert lead["score"] == "hot"
    cass = Cass()
    cass.pitch(s, lead)
    pay = cass.open_payment(s, {**lead, "sku": lead["sku"]})
    assert pay["status"] == "pending"
    assert pay["amount"] == OFFERS[lead["sku"]].price
    blocked = Pono().attempt(s, pay["id"])
    assert blocked["status"] == "blocked"


def test_only_operator_verify_starts_delivery(tmp_path: Path):
    brain = FactoryBrain(store(tmp_path))
    pending = brain.store.list("payments", "status='pending'", limit=1)[0]
    result = brain.verify_payment(pending["id"], operator="Xavier Hoolulu")
    assert result["payment"]["status"] == "complete"
    assert result["payment"]["verified_by"] == "Xavier Hoolulu"
    assert result["delivery"]["status"] in {"running", "done"}


def test_tick_runs_full_pipeline_silently(tmp_path: Path):
    brain = FactoryBrain(store(tmp_path))
    before = {e["id"] for e in brain.open_pings()}
    out = brain.tick()
    assert out["ping_policy"] == "HIGH_AND_CRITICAL_ONLY"
    assert "actions" in out
    # New pings can appear for pending payments, but never for routine posts.
    events = brain.store.list("events", "kind='post_queued' OR kind='pitch_sent' OR kind='lead_scored'")
    assert events
    assert all(e["ping"] == 0 for e in events)
    for ping in brain.open_pings():
        assert ping["id"] in before or ping["trigger"] in {
            "payment_needs_human_verify",
            "refund_request",
            "legal_threat",
            "hostile_customer",
            "attorney_letter",
            "active_chargeback",
            "safety_threat",
            "fraud_suspected",
            "delivery_blocked",
            "chargeback_language",
        }


def test_hostile_reply_pings_and_yes_closes(tmp_path: Path):
    s = store(tmp_path)
    lead = Echo().ingest(
        s,
        name="Pua",
        business="Big Island Pest",
        island="Big Island",
        channel="whatsapp",
        message="Interested in SEO, how much?",
    )
    cass = Cass()
    yes = cass.handle_reply(s, lead["id"], "yes let's go send payment")
    assert yes["handled"] == "closing"
    refund = cass.handle_reply(s, lead["id"], "actually this is a scam I want a refund")
    assert refund["handled"] == "escalated"
    Watch().tick(s)
    pings = s.list("escalations", "ping=1")
    assert any(p["trigger"] == "refund_request" for p in pings)
