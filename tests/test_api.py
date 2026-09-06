from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["ping_policy"] == "HIGH_AND_CRITICAL_ONLY"


def test_state_and_tick_and_social():
    state = client.get("/api/state").json()
    assert state["kpis"]["leads"] >= 1
    assert {a["id"] for a in state["agents"]} >= {"kai", "cass", "watch"}
    kai = next(a for a in state["agents"] if a["id"] == "kai")
    cass = next(a for a in state["agents"] if a["id"] == "cass")
    watch = next(a for a in state["agents"] if a["id"] == "watch")
    assert kai["can_ping"] is False
    assert cass["can_ping"] is False
    assert watch["can_ping"] is True

    tick = client.post("/api/tick").json()
    assert tick["ping_policy"] == "HIGH_AND_CRITICAL_ONLY"

    post = client.post("/api/social/generate", json={"platform": "tiktok", "sku": "souper-bot"}).json()
    assert post["platform"] == "tiktok"
    assert "197" in post["caption"] or "Souper" in post["caption"]


def test_home_page():
    res = client.get("/")
    assert res.status_code == 200
    assert "Hoolulu" in res.text
