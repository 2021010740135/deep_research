import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src = root / "app"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from backend.service.workflow_service import WorkflowService


class FakeConfig:
    user_id = "user01"
    thread_id = "thread01"
    tenant_id = "tenant01"
    max_iterations = 2
    enable_memory = False
    memory_top_k = 6

    def with_overrides(self, **kwargs):
        clone = FakeConfig()
        for key, value in kwargs.items():
            if value is not None:
                setattr(clone, key, value)
        return clone


class FakeApp:
    def __init__(self, results):
        self.results = list(results)
        self.states = []

    def invoke(self, state, config):
        self.states.append(state)
        return self.results.pop(0)


class WorkflowClarificationTest(unittest.TestCase):
    def _service(self, app):
        service = WorkflowService("unused-config.json")
        service._initialized = True
        service._base_config = FakeConfig()
        service._memory_manager = None
        service._app = app
        return service

    def test_clarification_state_blocks_free_text_until_button_action(self):
        app = FakeApp([
            {
                "intent": "clarify",
                "final": "choose",
                "clarify_options": [{"id": "direct_answer"}, {"id": "deep_research"}],
                "pending_clarification": {"original_query": "帮我做AI产品分析"},
            },
            {
                "intent": "direct",
                "final": "direct answer",
            },
        ])
        service = self._service(app)

        first_final, first_route = service._run_sync(
            query="帮我做AI产品分析",
            user_id="user01",
            thread_id="thread01",
            tenant_id="tenant01",
            max_iterations=None,
            enable_memory=False,
            clarification_action=None,
            original_query=None,
        )

        self.assertEqual("choose", first_final)
        self.assertEqual("clarify", first_route)
        self.assertIn(("tenant01", "user01", "thread01"), service._pending_clarifications)

        with self.assertRaises(ValueError):
            service._run_sync(
                query="你自己决定",
                user_id="user01",
                thread_id="thread01",
                tenant_id="tenant01",
                max_iterations=None,
                enable_memory=False,
                clarification_action=None,
                original_query=None,
            )

        second_final, second_route = service._run_sync(
            query="ignored button label",
            user_id="user01",
            thread_id="thread01",
            tenant_id="tenant01",
            max_iterations=None,
            enable_memory=False,
            clarification_action="direct_answer",
            original_query=None,
        )

        self.assertEqual("direct answer", second_final)
        self.assertEqual("direct", second_route)
        self.assertEqual("帮我做AI产品分析", app.states[-1]["query"])
        self.assertEqual("direct_answer", app.states[-1]["clarification_action"])
        self.assertNotIn(("tenant01", "user01", "thread01"), service._pending_clarifications)


if __name__ == "__main__":
    unittest.main()
