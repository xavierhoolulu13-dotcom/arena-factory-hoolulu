from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE_PATH = ROOT / "core" / "FROZEN_CONTRACT.json"
DATA_DIR = ROOT / ".data"
DB_PATH = DATA_DIR / "factory.db"
STATIC_DIR = ROOT / "app" / "static"

CONTRACT = json.loads(CORE_PATH.read_text(encoding="utf-8"))
VERSION = CONTRACT["version"]

OPERATOR = CONTRACT["operator"]["name"]
PING_POLICY = CONTRACT["operator"]["ping_policy"]
PING_LEVELS = frozenset(CONTRACT["escalation"]["ping"])
SILENT_LEVELS = frozenset(CONTRACT["escalation"]["silent"])

PIPELINE_STAGES = list(CONTRACT["pipeline"])

HIGH_TRIGGERS = frozenset(CONTRACT["escalation"]["high_triggers"])
CRITICAL_TRIGGERS = frozenset(CONTRACT["escalation"]["critical_triggers"])
