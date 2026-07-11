import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src = root / "app"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from mult_agents.nodes import IntentDecision, detect_intent


class DetectIntentDecisionMetadataTest(unittest.TestCase):
    def test_detect_intent_can_still_unpack_route_and_confidence(self):
        route, confidence = detect_intent("调研AI趋势")

        self.assertEqual("multiagent", route)
        self.assertEqual(0.92, confidence)

    def test_detect_intent_exposes_reason_source_and_matched_rule(self):
        decision = detect_intent("你好")

        self.assertIsInstance(decision, IntentDecision)
        self.assertEqual("direct", decision.route)
        self.assertEqual(0.98, decision.confidence)
        self.assertEqual("rule", decision.source)
        self.assertEqual("greeting_exact_match", decision.matched_rule)
        self.assertEqual("exact greeting", decision.reason)

    def test_detect_intent_as_dict_contains_routing_metadata(self):
        decision = detect_intent("2026年AI趋势")

        self.assertEqual(
            {
                "route": "multiagent",
                "confidence": 0.95,
                "reason": "year plus research/trend keyword",
                "source": "rule",
                "matched_rule": "year_trend",
            },
            decision.as_dict(),
        )


if __name__ == "__main__":
    unittest.main()
