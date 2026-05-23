"""Queue Visibility Manager — Persists and manages task visibility timeouts."""

import json
import os
import time
from typing import Dict, List, Optional


class VisibilityManager:
    def __init__(self, state_path: str = "/tmp/queue_visibility.json"):
        self.state_path = state_path
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r") as f:
                    self._state = json.load(f)
            except Exception:
                self._state = {}
        else:
            self._state = {}

    def _save_state(self):
        with open(self.state_path, "w") as f:
            json.dump(self._state, f)

    def set_visibility(self, task_id: str, timeout: float, queue: str):
        """Mark a task as invisible until timeout expires."""
        self._state[task_id] = {
            "expires_at": time.time() + timeout,
            "queue": queue,
            "extended_count": 0
        }
        self._save_state()

    def extend_visibility(self, task_id: str, extension: float):
        """Extend the visibility timeout for a long-running task."""
        if task_id in self._state:
            self._state[task_id]["expires_at"] = time.time() + extension
            self._state[task_id]["extended_count"] += 1
            self._save_state()
            return True
        return False

    def remove_visibility(self, task_id: str):
        """Remove visibility tracking (on completion or explicit failure)."""
        if task_id in self._state:
            del self._state[task_id]
            self._save_state()
            return True
        return False

    def get_expired_tasks(self) -> List[Dict]:
        """Get tasks whose visibility timeout has expired."""
        now = time.time()
        expired = []
        for tid, info in list(self._state.items()):
            if now >= info["expires_at"]:
                expired.append({"id": tid, "queue": info["queue"]})
        return expired
