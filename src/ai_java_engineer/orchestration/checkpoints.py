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

    def list_all_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Lists latest state for recent executions."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT c.execution_id, c.node_name, c.status, c.created_at, c.state_json
                FROM checkpoints c
                INNER JOIN (
                    SELECT execution_id, MAX(checkpoint_id) as max_id
                    FROM checkpoints
                    GROUP BY execution_id
                ) m ON c.execution_id = m.execution_id AND c.checkpoint_id = m.max_id
                ORDER BY c.checkpoint_id DESC
                LIMIT ?
                """,
                (limit,),
            )
            runs = []
            for row in cur.fetchall():
                exec_id, node_name, status, created_at, state_json = row
                title = ""
                iteration = 0
                changed_files = []
                try:
                    data = json.loads(state_json)
                    req = data.get("requirement", {})
                    title = req.get("title", "") if isinstance(req, dict) else ""
                    iteration = data.get("iteration", 0)
                    changed_files = data.get("changed_files", [])
                except Exception:
                    pass
                runs.append({
                    "execution_id": exec_id,
                    "node_name": node_name,
                    "status": status,
                    "created_at": created_at,
                    "title": title or exec_id,
                    "iteration": iteration,
                    "changed_files_count": len(changed_files),
                })
            return runs
        finally:
            conn.close()

    def get_checkpoints_timeline(self, execution_id: str) -> list[dict[str, Any]]:
        """Returns ordered timeline of execution nodes."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT checkpoint_id, node_name, status, created_at
                FROM checkpoints
                WHERE execution_id = ?
                ORDER BY checkpoint_id ASC
                """,
                (execution_id,),
            )
            return [
                {
                    "checkpoint_id": r[0],
                    "node_name": r[1],
                    "status": r[2],
                    "created_at": r[3],
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

