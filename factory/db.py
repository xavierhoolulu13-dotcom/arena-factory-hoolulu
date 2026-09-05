from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from factory.config import DATA_DIR, DB_PATH

_LOCK = threading.Lock()


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str = "") -> str:
    stem = uuid.uuid4().hex[:10]
    return f"{prefix}{stem}" if prefix else stem


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS factory_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    business TEXT NOT NULL,
    island TEXT NOT NULL,
    channel TEXT NOT NULL,
    need TEXT NOT NULL DEFAULT '',
    score TEXT NOT NULL DEFAULT 'cold',
    urgency INTEGER NOT NULL DEFAULT 2,
    status TEXT NOT NULL DEFAULT 'new',
    stage TEXT NOT NULL DEFAULT 'capture',
    sku TEXT,
    last_inbound TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    role TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    sku TEXT NOT NULL,
    hook TEXT NOT NULL,
    caption TEXT NOT NULL,
    cta TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    scheduled_for TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    verified_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE TABLE IF NOT EXISTS deliveries (
    id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    payment_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'blocked',
    summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    FOREIGN KEY (payment_id) REFERENCES payments(id)
);

CREATE TABLE IF NOT EXISTS escalations (
    id TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    trigger TEXT NOT NULL,
    ping INTEGER NOT NULL,
    title TEXT NOT NULL,
    detail TEXT NOT NULL,
    lead_id TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    acked_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    kind TEXT NOT NULL,
    level TEXT NOT NULL,
    ping INTEGER NOT NULL,
    summary TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    @contextmanager
    def session(self):
        with _LOCK:
            con = self._connect()
            try:
                yield con
                con.commit()
            except Exception:
                con.rollback()
                raise
            finally:
                con.close()

    def get_state(self, key: str, default: str | None = None) -> str | None:
        with self.session() as con:
            row = con.execute("SELECT value FROM factory_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_state(self, key: str, value: str) -> None:
        with self.session() as con:
            con.execute(
                "INSERT INTO factory_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def insert(self, table: str, row: dict) -> dict:
        cols = ", ".join(row.keys())
        marks = ", ".join("?" for _ in row)
        with self.session() as con:
            con.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(row.values()))
        return row

    def update(self, table: str, ident: str, fields: dict) -> None:
        fields = {**fields, "updated_at": utcnow()} if "updated_at" in _columns_for(table) else fields
        sets = ", ".join(f"{k}=?" for k in fields)
        with self.session() as con:
            con.execute(f"UPDATE {table} SET {sets} WHERE id=?", (*fields.values(), ident))

    def get(self, table: str, ident: str) -> dict | None:
        with self.session() as con:
            row = con.execute(f"SELECT * FROM {table} WHERE id=?", (ident,)).fetchone()
        return dict(row) if row else None

    def list(self, table: str, where: str = "1=1", args: tuple = (), order: str = "created_at DESC", limit: int = 200) -> list[dict]:
        with self.session() as con:
            rows = con.execute(
                f"SELECT * FROM {table} WHERE {where} ORDER BY {order} LIMIT {int(limit)}",
                args,
            ).fetchall()
        return [dict(r) for r in rows]

    def count(self, table: str, where: str = "1=1", args: tuple = ()) -> int:
        with self.session() as con:
            n = con.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {where}", args).fetchone()["n"]
        return int(n)

    def log_event(self, agent: str, kind: str, summary: str, *, level: str = "low", ping: bool = False, payload: dict | None = None) -> dict:
        row = {
            "id": new_id("ev_"),
            "agent": agent,
            "kind": kind,
            "level": level,
            "ping": int(ping),
            "summary": summary,
            "payload": json.dumps(payload or {}),
            "created_at": utcnow(),
        }
        return self.insert("events", row)


_TABLE_COLUMNS = {
    "leads": {"updated_at"},
    "payments": {"updated_at"},
    "deliveries": {"updated_at"},
}


def _columns_for(table: str) -> set[str]:
    return _TABLE_COLUMNS.get(table, set())


def reset_db(path: Path | None = None) -> None:
    target = Path(path) if path else DB_PATH
    if target.exists():
        target.unlink()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
