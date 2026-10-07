"""Hub-local SQLite: executed command ids (replay guard), offline outbox, state cache."""

import json
import sqlite3
import threading
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from gateway.timeutil import iso, utcnow

SCHEMA = """
CREATE TABLE IF NOT EXISTS executed_commands (
    command_id TEXT PRIMARY KEY,
    received_at TEXT NOT NULL,
    outcome TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS device_state (
    device_key TEXT NOT NULL,
    capability TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value TEXT,
    source TEXT NOT NULL,
    ts TEXT NOT NULL,
    PRIMARY KEY (device_key, capability, attribute)
);
CREATE TABLE IF NOT EXISTS kv (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS availability (
    device_key TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    ts TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # ---- replay guard -------------------------------------------------------------
    def claim_command(self, command_id: str) -> bool:
        """Record command_id BEFORE execution. False if it was seen already (replay)."""
        with self._lock:
            try:
                self.db.execute(
                    "INSERT INTO executed_commands (command_id, received_at, outcome) "
                    "VALUES (?, ?, 'pending')", (command_id, iso(utcnow())))
                return True
            except sqlite3.IntegrityError:
                return False

    def set_outcome(self, command_id: str, outcome: str) -> None:
        with self._lock:
            self.db.execute("UPDATE executed_commands SET outcome=? WHERE command_id=?",
                            (outcome, command_id))

    def purge_executed(self, older_than_days: int) -> None:
        # Only safe because expired commands are refused anyway (expires_at check).
        cutoff = iso(utcnow() - timedelta(days=older_than_days))
        with self._lock:
            self.db.execute("DELETE FROM executed_commands WHERE received_at < ?", (cutoff,))

    # ---- outbox -----------------------------------------------------------------
    def enqueue(self, kind: str, payload: dict) -> None:
        with self._lock:
            self.db.execute("INSERT INTO outbox (kind, payload, created_at) VALUES (?, ?, ?)",
                            (kind, json.dumps(payload), iso(utcnow())))

    def peek(self, kind: str, limit: int = 100) -> List[Tuple[int, dict]]:
        with self._lock:
            rows = self.db.execute(
                "SELECT id, payload FROM outbox WHERE kind=? ORDER BY id LIMIT ?",
                (kind, limit)).fetchall()
        return [(r[0], json.loads(r[1])) for r in rows]

    def ack_outbox(self, ids: List[int]) -> None:
        if not ids:
            return
        with self._lock:
            self.db.execute(f"DELETE FROM outbox WHERE id IN ({','.join('?' * len(ids))})", ids)

    def outbox_size(self) -> int:
        with self._lock:
            return self.db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]

    # ---- state cache ------------------------------------------------------------------
    def put_state(self, key: str, capability: str, attribute: str, value, source: str,
                  ts: str) -> None:
        with self._lock:
            self.db.execute(
                "INSERT INTO device_state VALUES (?,?,?,?,?,?) ON CONFLICT"
                "(device_key, capability, attribute) DO UPDATE SET value=excluded.value,"
                " source=excluded.source, ts=excluded.ts",
                (key, capability, attribute, json.dumps(value), source, ts))

    def get_state(self, key: str, capability: str, attribute: str) -> Optional[dict]:
        with self._lock:
            row = self.db.execute(
                "SELECT value, source, ts FROM device_state WHERE device_key=? AND "
                "capability=? AND attribute=?", (key, capability, attribute)).fetchone()
        if row is None:
            return None
        return {"value": json.loads(row[0]), "source": row[1], "ts": row[2]}

    def all_states(self) -> Dict[str, Dict[str, Dict[str, dict]]]:
        out: Dict[str, Dict[str, Dict[str, dict]]] = {}
        with self._lock:
            rows = self.db.execute("SELECT * FROM device_state").fetchall()
        for key, cap, attr, value, source, ts in rows:
            out.setdefault(key, {}).setdefault(cap, {})[attr] = {
                "value": json.loads(value), "source": source, "ts": ts}
        return out

    def set_availability(self, key: str, status: str) -> None:
        with self._lock:
            self.db.execute(
                "INSERT INTO availability VALUES (?,?,?) ON CONFLICT(device_key) DO UPDATE SET "
                "status=excluded.status, ts=excluded.ts", (key, status, iso(utcnow())))

    def availability(self) -> Dict[str, str]:
        with self._lock:
            return dict(self.db.execute("SELECT device_key, status FROM availability").fetchall())

    # ---- key/value (last known hub config, for offline start) ---------------------
    def put_kv(self, k: str, v) -> None:
        with self._lock:
            self.db.execute("INSERT INTO kv VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                            (k, json.dumps(v)))

    def get_kv(self, k: str):
        with self._lock:
            row = self.db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return json.loads(row[0]) if row else None
