import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_DB_PATH = Path.home() / ".jarvis" / "memory.db"


class MemoryDB:
    def __init__(self, path: Path = _DB_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_text TEXT NOT NULL,
                assistant_text TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def save_turn(self, session_id: str, user_text: str, assistant_text: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._conn.execute(
            "INSERT INTO turns (session_id, timestamp, user_text, assistant_text) VALUES (?, ?, ?, ?)",
            (session_id, ts, user_text, assistant_text),
        )
        self._conn.commit()

    def list_sessions(self) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT session_id, MIN(timestamp), MAX(timestamp), COUNT(*), "
            "  (SELECT user_text FROM turns t2 WHERE t2.session_id = t.session_id ORDER BY id LIMIT 1) "
            "FROM turns t GROUP BY session_id ORDER BY MAX(timestamp) DESC"
        ).fetchall()
        return [
            {
                "session_id": r[0],
                "started": r[1],
                "last": r[2],
                "turns": r[3],
                "first_message": r[4],
            }
            for r in rows
        ]

    def get_session_turns(self, session_id: str) -> List[Tuple[str, str, str]]:
        rows = self._conn.execute(
            "SELECT timestamp, user_text, assistant_text FROM turns "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        return rows

    def get_recent(self, session_id: str, n: int = 20) -> List[Tuple[str, str, str]]:
        rows = self._conn.execute(
            "SELECT timestamp, user_text, assistant_text FROM turns "
            "WHERE session_id != ? ORDER BY id DESC LIMIT ?",
            (session_id, n),
        ).fetchall()
        return list(reversed(rows))

    def search(self, query: str, n: int = 5) -> List[Tuple[str, str, str]]:
        like = f"%{query}%"
        rows = self._conn.execute(
            "SELECT timestamp, user_text, assistant_text FROM turns "
            "WHERE user_text LIKE ? OR assistant_text LIKE ? ORDER BY id DESC LIMIT ?",
            (like, like, n),
        ).fetchall()
        return list(reversed(rows))


_db: Optional[MemoryDB] = None


def init_memory() -> MemoryDB:
    global _db
    _db = MemoryDB()
    return _db


def get_memory() -> Optional[MemoryDB]:
    return _db


def format_memory_context(turns: List[Tuple[str, str, str]]) -> str:
    if not turns:
        return ""
    lines = "\n".join(f"[{ts}] User: {u} | Jarvis: {a}" for ts, u, a in turns)
    return f"\n\nPast conversations:\n{lines}"
