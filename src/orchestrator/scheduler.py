"""Task Scheduler — Priority-based task queuing and dispatch."""

import asyncio
import heapq
import time
import logging
from typing import Any, Dict, Optional, List
from uuid import uuid4

from .visibility import VisibilityManager

logger = logging.getLogger(__name__)


class PriorityQueue:
    def __init__(self):
        self._queue = []
        self._counter = 0

    def push(self, item: Any, priority: int = 0) -> None:
        heapq.heappush(self._queue, (-priority, self._counter, item))
        self._counter += 1

    def pop(self) -> Optional[Any]:
        if self._queue:
            return heapq.heappop(self._queue)[2]
        return None

    def peek(self) -> Optional[Any]:
        if self._queue:
            return self._queue[0][2]
        return None

    def __len__(self) -> int:
        return len(self._queue)


class TaskScheduler:
    def __init__(self, visibility_timeout: float = 30.0):
        self._queues: Dict[str, PriorityQueue] = {}
        self._scheduled: Dict[str, float] = {}
        self._in_flight: Dict[str, Dict] = {}
        self._max_retries = 3
        self.visibility_manager = VisibilityManager()
        self.visibility_timeout = visibility_timeout

    def enqueue(self, task: Dict, queue: str = "default", priority: int = 0) -> str:
        task_id = task.get("id") or str(uuid4())
        task["id"] = task_id
        task["enqueued_at"] = time.time()
        task["retries"] = task.get("retries", 0)

        if queue not in self._queues:
            self._queues[queue] = PriorityQueue()
        self._queues[queue].push(task, priority)
        return task_id

    def schedule(self, task: Dict, delay: float, queue: str = "default", priority: int = 0) -> str:
        task_id = str(uuid4())
        task["id"] = task_id
        self._scheduled[task_id] = time.time() + delay
        return task_id

    async def dequeue(self, queue: str = "default", timeout: float = 1.0) -> Optional[Dict]:
        now = time.time()
        
        # Check for expired visibility and re-enqueue
        expired_visibility = self.visibility_manager.get_expired_tasks()
        for expired in expired_visibility:
            task = self._in_flight.pop(expired["id"], None)
            if task:
                logger.info(f"Task {task['id']} visibility expired, re-enqueueing to {expired['queue']}")
                self.visibility_manager.remove_visibility(task["id"])
                self.enqueue(task, expired["queue"])

        expired_scheduled = [tid for tid, t in self._scheduled.items() if t <= now]
        for tid in expired_scheduled:
            task = self._scheduled.pop(tid)
            if task:
                self.enqueue(task, queue)

        if queue in self._queues and len(self._queues[queue]) > 0:
            task = self._queues[queue].pop()
            if task:
                self._in_flight[task["id"]] = task
                # Persist visibility extension
                self.visibility_manager.set_visibility(task["id"], self.visibility_timeout, queue)
                return task
        return None

    def extend_task_visibility(self, task_id: str, extension_seconds: float) -> bool:
        """Explicitly extend visibility for long running agents."""
        return self.visibility_manager.extend_visibility(task_id, extension_seconds)

    def complete(self, task_id: str) -> bool:
        self.visibility_manager.remove_visibility(task_id)
        return self._in_flight.pop(task_id, None) is not None

    def fail(self, task_id: str, queue: str = "default") -> bool:
        self.visibility_manager.remove_visibility(task_id)
        task = self._in_flight.pop(task_id, None)
        if task:
            task["retries"] += 1
            if task["retries"] < self._max_retries:
                self.enqueue(task, queue, priority=task.get("priority", 0))
                return True
        return False
