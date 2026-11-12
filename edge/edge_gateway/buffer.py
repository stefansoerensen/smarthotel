"""A SQLite queue of readings that survives restarts and outages."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Stored:
    """A buffered reading with its queue id."""

    id: int
    device_code: str
    value: float
    measured_at: str


class Buffer:
    """Readings waiting for the cloud, oldest first, plus the last known configuration."""

    def __init__(self, path: str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "device_code TEXT NOT NULL, value REAL NOT NULL, measured_at TEXT NOT NULL)"
        )
        self.db.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
        self.db.commit()

    def add(self, readings: list[tuple[str, float, str]]) -> None:
        """Queue readings as (device_code, value, measured_at ISO)."""
        self.db.executemany(
            "INSERT INTO readings (device_code, value, measured_at) VALUES (?, ?, ?)", readings
        )
        self.db.commit()

    def peek(self, limit: int = 500) -> list[Stored]:
        """The oldest ``limit`` readings."""
        rows = self.db.execute(
            "SELECT id, device_code, value, measured_at FROM readings ORDER BY id LIMIT ?", (limit,)
        ).fetchall()
        return [Stored(*row) for row in rows]

    def remove(self, ids: list[int]) -> None:
        """Drop delivered readings."""
        self.db.executemany("DELETE FROM readings WHERE id = ?", [(i,) for i in ids])
        self.db.commit()

    def count(self) -> int:
        """How many readings are waiting."""
        return int(self.db.execute("SELECT count(*) FROM readings").fetchone()[0])

    def save_config(self, hello: dict) -> None:
        """Keep the last hello answer, so a restart works without the cloud."""
        self.db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('hello', ?)", (json.dumps(hello),)
        )
        self.db.commit()

    def load_config(self) -> dict | None:
        """The last hello answer, if any."""
        row = self.db.execute("SELECT value FROM config WHERE key = 'hello'").fetchone()
        return json.loads(row[0]) if row else None
