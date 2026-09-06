"""Escalation gate — agents work silently. Xavier is pinged on HIGH / CRITICAL only."""

from __future__ import annotations

import re
from dataclasses import dataclass

from factory.config import CRITICAL_TRIGGERS, HIGH_TRIGGERS, PING_LEVELS, SILENT_LEVELS

LEVELS = ("low", "medium", "high", "critical")

# Language that must surface to the operator.
_CRITICAL_PATTERNS = (
    (re.compile(r"\b(attorney|lawyer|lawsuit|sue you|small claims)\b", re.I), "attorney_letter"),
    (re.compile(r"\b(chargeback|dispute with (my )?bank|file a dispute)\b", re.I), "active_chargeback"),
    (re.compile(r"\b(kill|hurt you|come after you|bomb)\b", re.I), "safety_threat"),
)
_HIGH_PATTERNS = (
    (re.compile(r"\b(refund|money back|scam|fraud|stole|ripoff|rip-off)\b", re.I), "refund_request"),
    (re.compile(r"\b(bbb|report you|attorney general|consumer protection)\b", re.I), "legal_threat"),
    (re.compile(r"\b(incompetent|worst|hate you|useless|never again)\b", re.I), "hostile_customer"),
)


@dataclass(frozen=True)
class EscalationDecision:
    level: str
    trigger: str
    ping: bool
    reason: str

    def as_dict(self) -> dict:
        return {
            "level": self.level,
            "trigger": self.trigger,
            "ping": self.ping,
            "reason": self.reason,
        }


def should_ping(level: str) -> bool:
    return level in PING_LEVELS


def classify_event(kind: str, text: str = "", *, default_level: str = "low") -> EscalationDecision:
    """Map an agent event to a level. Only high/critical set ping=True."""
    blob = f"{kind} {text}".strip()

    for pattern, trigger in _CRITICAL_PATTERNS:
        if pattern.search(blob):
            return _decide("critical", trigger, f"Critical language matched ({trigger}).")

    if kind in CRITICAL_TRIGGERS:
        return _decide("critical", kind, "Event type is locked as critical in the frozen contract.")

    for pattern, trigger in _HIGH_PATTERNS:
        if pattern.search(blob):
            return _decide("high", trigger, f"High-risk language matched ({trigger}).")

    if kind in HIGH_TRIGGERS:
        return _decide("high", kind, "Event type requires operator (frozen contract).")

    if kind in {"follow_up", "trial_expiring", "lead_stalled", "post_failed"}:
        return _decide("medium", kind, "Agents handle this. Dashboard only.")

    level = default_level if default_level in LEVELS else "low"
    if level in PING_LEVELS:
        # Agents are not allowed to self-promote a ping without a contract trigger.
        level = "medium"
    return _decide(level, kind or "routine", "Routine factory work. Operator is not pinged.")


def _decide(level: str, trigger: str, reason: str) -> EscalationDecision:
    if level in PING_LEVELS:
        ping = True
    elif level in SILENT_LEVELS:
        ping = False
    else:
        ping = False
        level = "low"
    return EscalationDecision(level=level, trigger=trigger, ping=ping, reason=reason)
