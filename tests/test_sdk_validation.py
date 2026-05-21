import unittest
import pytest
from src.sdk.decorators import on_event, task, agent
from src.orchestrator.engine import OrchestrationEngine

class TestSDKValidation(unittest.TestCase):
    def test_on_event_rejects_blank(self):
        with self.assertRaisesRegex(ValueError, "event_type cannot be empty or blank"):
            on_event("")
        with self.assertRaisesRegex(ValueError, "event_type cannot be empty or blank"):
            on_event("   ")

    def test_task_rejects_blank_name(self):
        with self.assertRaisesRegex(ValueError, "task name cannot be empty or blank"):
            task(name="")
        with self.assertRaisesRegex(ValueError, "task name cannot be empty or blank"):
            task(name="  ")

    def test_agent_rejects_blank_name(self):
        with self.assertRaisesRegex(ValueError, "agent name cannot be empty or blank"):
            agent(name="")
        with self.assertRaisesRegex(ValueError, "agent name cannot be empty or blank"):
            agent(name="   ")

    def test_register_hook_rejects_blank_event(self):
        engine = OrchestrationEngine()
        with self.assertRaisesRegex(ValueError, "hook event name cannot be empty or blank"):
            engine.register_hook("", lambda: None)
        with self.assertRaisesRegex(ValueError, "hook event name cannot be empty or blank"):
            engine.register_hook("  ", lambda: None)

if __name__ == "__main__":
    unittest.main()
