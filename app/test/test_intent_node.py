import sys
import unittest
from pathlib import Path
from unittest.mock import patch

root = Path(__file__).resolve().parents[2]
src = root / "app"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from mult_agents import nodes


def _state(query: str, **extra) -> dict:
    return {
        "query": query,
        "memory_context": "",
        "messages": [],
        **extra,
    }


class IntentNodeConfidenceRoutingTest(unittest.TestCase):
    def test_user_clarification_direct_answer_skips_llm(self):
        with patch.object(nodes, "detect_intent", side_effect=AssertionError("rule detection should be skipped")), \
             patch.object(nodes, "_invoke_json_agent", side_effect=AssertionError("LLM should be skipped")):
            result = nodes.intent_node(
                _state(
                    "original question",
                    clarification_action="direct_answer",
                    original_query="original question",
                ),
                object(),
                "intent_router",
            )

        self.assertEqual("direct", result["intent"])
        self.assertEqual(1.0, result["confidence"])
        self.assertEqual("user_clarification", result["intent_source"])
        self.assertEqual("user_clarification", result["intent_matched_rule"])
        self.assertEqual([], result["messages"])

    def test_user_clarification_deep_research_skips_llm(self):
        with patch.object(nodes, "detect_intent", side_effect=AssertionError("rule detection should be skipped")), \
             patch.object(nodes, "_invoke_json_agent", side_effect=AssertionError("LLM should be skipped")):
            result = nodes.intent_node(
                _state(
                    "original question",
                    clarification_action="deep_research",
                    original_query="original question",
                ),
                object(),
                "intent_router",
            )

        self.assertEqual("multiagent", result["intent"])
        self.assertEqual(1.0, result["confidence"])
        self.assertEqual("user_clarification", result["intent_source"])
        self.assertEqual("user_clarification", result["intent_matched_rule"])
        self.assertEqual([], result["messages"])

    def test_high_confidence_rule_result_skips_llm(self):
        with patch.object(nodes, "detect_intent", return_value=("multiagent", 0.85)) as detect, \
             patch.object(nodes, "_invoke_json_agent", side_effect=AssertionError("LLM should be skipped")) as invoke:
            result = nodes.intent_node(_state("调研AI趋势"), object(), "intent_router")

        detect.assert_called_once_with("调研AI趋势")
        invoke.assert_not_called()
        self.assertEqual("multiagent", result["intent"])
        self.assertEqual(0.85, result["confidence"])
        self.assertEqual([], result["messages"])
        self.assertIn("multiagent", result["draft"])

    def test_low_confidence_rule_result_calls_llm_and_uses_llm_confidence(self):
        llm_payload = {"route": "multiagent", "reason": "llm override", "confidence": 0.77}
        with patch.object(nodes, "detect_intent", return_value=("direct", 0.45)) as detect, \
             patch.object(nodes, "_invoke_json_agent", return_value=(llm_payload, "llm-content", ["human", "ai"])) as invoke:
            result = nodes.intent_node(_state("关于AI的一些想法"), object(), "intent_router")

        detect.assert_called_once_with("关于AI的一些想法")
        invoke.assert_called_once()

        prompt = invoke.call_args.args[1]
        fallback = invoke.call_args.args[5]
        self.assertIn("规则引擎初判：direct", prompt)
        self.assertIn("规则引擎置信度：0.45", prompt)
        self.assertIn('"confidence":0.82', prompt)
        self.assertEqual({"route": "direct", "reason": "rule", "confidence": 0.45}, fallback)

        self.assertEqual("multiagent", result["intent"])
        self.assertEqual(0.77, result["confidence"])
        self.assertEqual("llm-content", result["draft"])
        self.assertEqual(["human", "ai"], result["messages"])


if __name__ == "__main__":
    unittest.main()


from mult_agents import graph
from mult_agents.graph import route_after_intent


class RouteAfterIntentDynamicThresholdTest(unittest.TestCase):
    def test_routes_trusted_rule_multiagent_to_plan(self):
        result = route_after_intent({
            "intent": "multiagent",
            "confidence": 0.70,
            "intent_source": "rule",
            "intent_matched_rule": "strong_multiagent_keyword",
            "intent_reason": "matched strong keyword",
        })

        self.assertEqual("plan", result)

    def test_routes_low_confidence_llm_multiagent_to_clarify(self):
        result = route_after_intent({
            "intent": "multiagent",
            "confidence": 0.84,
            "intent_source": "llm",
            "intent_matched_rule": "medium_multiagent_keyword",
            "intent_reason": "weak multiagent signal",
        })

        self.assertEqual("clarify", result)

    def test_routes_llm_medium_keyword_multiagent_to_clarify_even_when_confident(self):
        result = route_after_intent({
            "intent": "multiagent",
            "confidence": 0.95,
            "intent_source": "llm",
            "intent_matched_rule": "medium_multiagent_keyword",
            "intent_reason": "llm thinks analysis is needed",
        })

        self.assertEqual("clarify", result)

    def test_routes_threshold_passing_llm_multiagent_to_plan(self):
        result = route_after_intent({
            "intent": "multiagent",
            "confidence": 0.85,
            "intent_source": "llm",
            "intent_matched_rule": "",
            "intent_reason": "research needed",
        })

        self.assertEqual("plan", result)

    def test_routes_trusted_direct_rule_to_direct_answer(self):
        result = route_after_intent({
            "intent": "direct",
            "confidence": 0.70,
            "intent_source": "rule",
            "intent_matched_rule": "simple_math",
            "intent_reason": "simple arithmetic query",
        })

        self.assertEqual("direct_answer", result)

    def test_routes_unknown_intent_to_direct_answer(self):
        result = route_after_intent({
            "intent": "unknown",
            "confidence": 0.99,
            "intent_source": "llm",
            "intent_reason": "invalid output",
        })

        self.assertEqual("direct_answer", result)


class ClarifyNodeTest(unittest.TestCase):
    def test_clarify_node_asks_user_to_choose_depth_for_low_confidence_expensive_task(self):
        result = nodes.clarify_node({
            "query": "关于AI的一些想法",
            "confidence": 0.77,
            "intent_reason": "weak multiagent signal",
            "intent_source": "llm",
            "intent_matched_rule": "medium_multiagent_keyword",
        })

        self.assertEqual("clarify", result["intent"])
        self.assertEqual("clarification_required", result["phase"])
        self.assertIn("关于AI的一些想法", result["final"])
        self.assertEqual(
            ["direct_answer", "deep_research"],
            [item["id"] for item in result["clarify_options"]],
        )
        self.assertEqual(
            "关于AI的一些想法",
            result["pending_clarification"]["original_query"],
        )
        self.assertEqual(0.77, result["pending_clarification"]["confidence"])
        self.assertEqual("llm", result["pending_clarification"]["source"])
        self.assertEqual(
            "medium_multiagent_keyword",
            result["pending_clarification"]["matched_rule"],
        )
        self.assertEqual(result["final"], result["draft"])
        self.assertEqual([], result["messages"])


class GraphClarifyBranchTest(unittest.TestCase):
    def test_build_app_registers_clarify_node_and_branch(self):
        workflow = RecordingWorkflow()
        agents = FakeAgents()

        with patch.object(graph, "StateGraph", return_value=workflow):
            result = graph.build_app(agents, checkpointer=None)

        self.assertEqual("compiled", result)
        self.assertIn("clarify", workflow.nodes)
        self.assertIn(("clarify", graph.END), workflow.edges)
        intent_edges = [
            item for item in workflow.conditional_edges
            if item[0] == "intent"
        ]
        self.assertEqual(1, len(intent_edges))
        self.assertEqual("clarify", intent_edges[0][2]["clarify"])


class RecordingWorkflow:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.conditional_edges = []

    def add_node(self, name, node):
        self.nodes[name] = node

    def add_edge(self, start, end):
        self.edges.append((start, end))

    def add_conditional_edges(self, start, route_func, mapping):
        self.conditional_edges.append((start, route_func, mapping))

    def compile(self, checkpointer=None):
        self.checkpointer = checkpointer
        return "compiled"


class FakeAgents:
    intent_router = object()
    direct_responder = object()
    planner = object()
    scout_web = object()
    scout_local = object()
    evidence_judge = object()
    analyst = object()
    writer = object()
