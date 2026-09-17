"""State checkpointing and persistence using SQLite."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_java_engineer.domain.execution import RunStatus


class CheckpointStore:
    """Stores and retrieves execution snapshots to enable pausing, human review, and resumption."""

    def __init__(self, db_path: str = "ai_java_engineer.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_checkpoints_exec_id 
                ON checkpoints(execution_id, checkpoint_id DESC)
                """
            )
            conn.commit()
        finally:
            conn.close()

    def save_checkpoint(self, execution_id: str, node_name: str, status: RunStatus, state: dict[str, Any]) -> int:
        """Serializes current state into SQLite."""
        # Convert non-serializable objects to dicts if needed
        clean_state = {}
        for k, v in state.items():
            if hasattr(v, "model_dump"):
                clean_state[k] = v.model_dump()
            else:
                clean_state[k] = v

        serialized = json.dumps(clean_state, default=str)

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO checkpoints (execution_id, node_name, status, state_json)
                VALUES (?, ?, ?, ?)
                """,
                (execution_id, node_name, status.value, serialized),
            )
            conn.commit()
            return cur.lastrowid or 0
        finally:
            conn.close()

    def load_latest_checkpoint(self, execution_id: str) -> dict[str, Any] | None:
        """Retrieves the most recent state checkpoint for a run."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT state_json FROM checkpoints
                WHERE execution_id = ?
                ORDER BY checkpoint_id DESC
                LIMIT 1
                """,
                (execution_id,),
            )
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
            return None
        finally:
            conn.close()
