import pytest
import time
import os
import asyncio
from src.orchestrator.scheduler import TaskScheduler


class TestQueueVisibility:
    def setup_method(self):
        self.state_file = "/tmp/queue_visibility.json"
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.scheduler = TaskScheduler(visibility_timeout=0.1)  # Short timeout for testing

    def teardown_method(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

    @pytest.mark.asyncio
    async def test_visibility_expiry_and_persistence(self):
        task = {"name": "long-running-job"}
        task_id = self.scheduler.enqueue(task)
        
        # Dequeue the task
        dequeued_task = await self.scheduler.dequeue()
        assert dequeued_task["id"] == task_id
        
        # Check persistence
        assert os.path.exists(self.state_file)
        
        # Wait for visibility to expire
        await asyncio.sleep(0.15)
        
        # Next dequeue should trigger re-enqueueing of the expired task
        re_dequeued_task = await self.scheduler.dequeue()
        assert re_dequeued_task is not None
        assert re_dequeued_task["id"] == task_id
        assert re_dequeued_task["retries"] == 0  # Re-enqueue doesn't count as retry

    @pytest.mark.asyncio
    async def test_visibility_extension(self):
        task = {"name": "extending-job"}
        task_id = self.scheduler.enqueue(task)
        
        await self.scheduler.dequeue()
        
        # Extend visibility
        self.scheduler.extend_task_visibility(task_id, 0.5)
        
        # Wait past original timeout
        await asyncio.sleep(0.15)
        
        # Should NOT be re-enqueued yet
        result = await self.scheduler.dequeue()
        assert result is None
        
        # Wait past extended timeout
        await asyncio.sleep(0.4)
        result = await self.scheduler.dequeue()
        assert result is not None
        assert result["id"] == task_id

    @pytest.mark.asyncio
    async def test_completion_removes_visibility(self):
        task = {"name": "completing-job"}
        task_id = self.scheduler.enqueue(task)
        
        await self.scheduler.dequeue()
        self.scheduler.complete(task_id)
        
        # Wait for expiry
        await asyncio.sleep(0.15)
        
        # Should NOT be re-enqueued because it was completed
        result = await self.scheduler.dequeue()
        assert result is None

    @pytest.mark.asyncio
    async def test_visibility_extension_idempotency(self):
        task = {"name": "idempotent-job"}
        task_id = self.scheduler.enqueue(task)
        await self.scheduler.dequeue()
        
        # First extension
        self.scheduler.extend_task_visibility(task_id, 0.5, extension_id="ext_1")
        assert self.scheduler.visibility_manager._state[task_id]["extended_count"] == 1
        
        # Second extension with SAME ID
        self.scheduler.extend_task_visibility(task_id, 0.5, extension_id="ext_1")
        # Count should still be 1
        assert self.scheduler.visibility_manager._state[task_id]["extended_count"] == 1
