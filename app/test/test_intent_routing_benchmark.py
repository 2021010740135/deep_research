import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src = root / "app"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from app.test.intent_routing_benchmark import evaluate_cases
from app.test.test_intent_routing_accuracy import _build_cases


class IntentRoutingBenchmarkTest(unittest.TestCase):
    def test_evaluation_metrics_show_new_router_reduces_expensive_false_plan(self):
        metrics = evaluate_cases(_build_cases())

        self.assertGreaterEqual(metrics["total_cases"], 300)
        self.assertGreater(metrics["new_accuracy"], metrics["legacy_accuracy"])
        self.assertGreater(metrics["legacy_false_plan_on_clarify"], 0)
        self.assertEqual(metrics["new_false_plan_on_clarify"], 0)
        self.assertGreater(metrics["new_clarify_guard_rate"], 0.95)
        self.assertGreater(metrics["intent_llm_calls_saved_vs_legacy"], 0)
        self.assertEqual(metrics["clarify_node_llm_calls"], 0)


if __name__ == "__main__":
    unittest.main()
