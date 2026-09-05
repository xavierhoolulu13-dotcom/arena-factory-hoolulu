from factory.escalation import classify_event, should_ping


def test_routine_work_does_not_ping():
    d = classify_event("post_published", "Published instagram for starter")
    assert d.ping is False
    assert d.level in {"low", "medium"}
    assert should_ping(d.level) is False


def test_medium_follow_up_is_silent():
    d = classify_event("follow_up", "Nudge Wahiawa Auto Repair")
    assert d.level == "medium"
    assert d.ping is False


def test_payment_verify_is_high_ping():
    d = classify_event("payment_needs_human_verify", "Cash App $297 pending")
    assert d.level == "high"
    assert d.ping is True
    assert should_ping("high") is True


def test_refund_language_pings():
    d = classify_event("inbound_reply", "This is a scam I want a refund now")
    assert d.ping is True
    assert d.level == "high"
    assert d.trigger == "refund_request"


def test_lawyer_is_critical():
    d = classify_event("inbound_reply", "My attorney will file a lawsuit Monday")
    assert d.level == "critical"
    assert d.ping is True


def test_agents_cannot_self_promote_a_ping():
    d = classify_event("happy_path", "all good", default_level="critical")
    assert d.ping is False
    assert d.level == "medium"
