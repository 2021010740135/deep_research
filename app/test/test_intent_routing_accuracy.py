import re
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

root = Path(__file__).resolve().parents[2]
src = root / "app"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from mult_agents.graph import route_after_intent
from mult_agents import nodes
from mult_agents.nodes import detect_intent


@dataclass(frozen=True)
class RoutingCase:
    query: str
    expected_action: str
    group: str


TOPICS = [
    "AI产品",
    "大模型",
    "智能体框架",
    "RAG系统",
    "代码助手",
    "向量数据库",
    "自动驾驶",
    "机器人",
    "医疗AI",
    "金融科技",
]

SECONDARY_TOPICS = [
    "LangGraph",
    "LlamaIndex",
    "AutoGen",
    "CrewAI",
    "Dify",
    "OpenAI API",
    "Milvus",
    "Qdrant",
    "Python",
    "Java",
]


def _legacy_detect_intent(query: str) -> str:
    normalized_query = query.strip()
    force_multiagent_keywords = [
        "调查",
        "调研",
        "来源",
        "证据",
        "检索统计",
        "来源清单",
        "重大新闻",
        "热门项目",
        "趋势",
        "新闻",
        "最新",
        "盘点",
    ]
    if re.search(r"20\d{2}年", normalized_query) and any(
        word in normalized_query for word in ["趋势", "新闻", "调研", "调查", "盘点"]
    ):
        return "multiagent"
    if any(word in query for word in force_multiagent_keywords):
        return "multiagent"
    keywords = [
        "调研",
        "研究",
        "调查",
        "盘点",
        "热门",
        "趋势",
        "榜单",
        "分析",
        "方案",
        "架构",
        "设计",
        "对比",
        "报告",
        "代码",
        "实现",
        "落地",
        "检索",
        "知识库",
        "证据",
        "来源",
        "溯源",
        "资料",
        "手册",
        "验证",
        "数据",
        "模型",
    ]
    return "multiagent" if any(word in query for word in keywords) else "direct"


def _legacy_route_action(query: str) -> str:
    return "direct_answer" if _legacy_detect_intent(query) == "direct" else "plan"


def _new_rule_route_action(query: str) -> str:
    decision = detect_intent(query)
    return route_after_intent(
        {
            "intent": decision.route,
            "confidence": decision.confidence,
            "intent_source": decision.source,
            "intent_reason": decision.reason,
            "intent_matched_rule": decision.matched_rule,
        }
    )


def _build_cases() -> list[RoutingCase]:
    cases: list[RoutingCase] = []
    seen: set[str] = set()

    def add(query: str, expected_action: str, group: str) -> None:
        if query not in seen:
            seen.add(query)
            cases.append(RoutingCase(query, expected_action, group))

    direct_queries = [
        "你好",
        "在吗",
        "早上好",
        "晚上好",
        "嗨",
        "hello",
        "hi",
        "你是谁",
        "你能做什么",
        "介绍你自己",
        "你的名字是什么",
        "今天星期几",
        "现在几点",
        "天气怎么样",
        "讲个笑话",
        "谢谢你",
        "你叫什么",
        "帮我看看这句话",
        "这个问题怎么理解",
        "关于AI的一些想法",
    ]
    for query in direct_queries:
        add(query, "direct_answer", "direct_basic")

    for left in range(1, 16):
        add(f"{left}+{left}等于几", "direct_answer", "direct_math")
        add(f"{left}加{left + 1}是多少", "direct_answer", "direct_math")
        add(f"{left + 10}减{left}是多少", "direct_answer", "direct_math")

    for phrase in ["说个笑话", "讲个笑话", "来个笑话", "笑话"]:
        for suffix in ["", "给我听", "吧"]:
            add(f"{phrase}{suffix}", "direct_answer", "direct_chat")

    force_keywords = [
        "调查",
        "调研",
        "来源",
        "证据",
        "检索统计",
        "来源清单",
        "重大新闻",
        "热门项目",
        "趋势",
        "新闻",
        "最新",
        "盘点",
    ]
    for keyword in force_keywords:
        for topic in TOPICS:
            add(f"帮我{keyword}{topic}", "plan", "trusted_multiagent_keyword")

    years = ["2024年", "2025年", "2026年", "2027年"]
    trend_words = ["趋势", "新闻", "调研", "调查", "盘点"]
    for year in years:
        for topic in TOPICS:
            for word in trend_words:
                add(f"{year}{topic}{word}", "plan", "trusted_year_trend")

    medium_keywords = [
        "研究",
        "分析",
        "方案",
        "架构",
        "设计",
        "对比",
        "比较",
        "报告",
        "总结",
        "代码",
        "实现",
        "落地",
        "检索",
        "知识库",
        "溯源",
        "资料",
        "手册",
        "验证",
        "数据",
        "模型",
        "哪个更好",
        "vs",
    ]
    for keyword in medium_keywords:
        for index, topic in enumerate(TOPICS):
            other = SECONDARY_TOPICS[index % len(SECONDARY_TOPICS)]
            if keyword in {"对比", "比较", "哪个更好", "vs"}:
                add(f"{topic}和{other}{keyword}", "clarify", "low_confidence_high_cost")
            else:
                add(f"帮我做{topic}{keyword}", "clarify", "low_confidence_high_cost")

    return cases


class IntentRoutingAccuracyComparisonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _build_cases()

    def test_dataset_has_hundreds_of_labeled_cases(self):
        self.assertGreaterEqual(len(self.cases), 300)

    def test_new_rule_router_matches_labeled_expected_actions(self):
        failures = []
        for case in self.cases:
            actual = _new_rule_route_action(case.query)
            if actual != case.expected_action:
                failures.append(
                    f"{case.group}: {case.query!r} expected={case.expected_action} actual={actual}"
                )

        self.assertFalse(failures, "\n".join(failures[:30]))

    def test_new_router_preserves_legacy_behavior_for_confident_direct_and_plan_cases(self):
        failures = []
        for case in self.cases:
            if case.expected_action == "clarify":
                continue
            legacy_action = _legacy_route_action(case.query)
            new_action = _new_rule_route_action(case.query)
            if legacy_action != case.expected_action or new_action != case.expected_action:
                failures.append(
                    f"{case.group}: {case.query!r} expected={case.expected_action} "
                    f"legacy={legacy_action} new={new_action}"
                )

        self.assertFalse(failures, "\n".join(failures[:30]))

    def test_new_router_converts_low_confidence_high_cost_legacy_routes_to_clarify(self):
        clarify_cases = [case for case in self.cases if case.expected_action == "clarify"]
        changed_to_clarify = [
            case for case in clarify_cases
            if _legacy_route_action(case.query) != "clarify" and _new_rule_route_action(case.query) == "clarify"
        ]

        self.assertGreaterEqual(len(clarify_cases), 150)
        self.assertEqual(len(clarify_cases), len(changed_to_clarify))

    def test_concrete_ambiguous_high_cost_examples_avoid_legacy_plan_misfire(self):
        examples = [
            "帮我做AI产品分析",
            "给我一个RAG系统方案",
            "Python和Java哪个更好",
            "帮我写一个智能体框架实现思路",
            "这个模型怎么用，给点资料",
            "帮我总结一下LangGraph",
            "帮我看看向量数据库架构",
            "AutoGen vs CrewAI",
            "帮我做医疗AI数据验证",
            "给我一个代码助手落地方案",
            "这个报错的原因分析一下",
            "帮我整理大模型手册",
        ]
        failures = []
        legacy_plan_to_clarify = 0
        legacy_direct_to_clarify = 0
        for query in examples:
            legacy_action = _legacy_route_action(query)
            new_action = _new_rule_route_action(query)
            if legacy_action == "plan" and new_action == "clarify":
                legacy_plan_to_clarify += 1
            elif legacy_action == "direct_answer" and new_action == "clarify":
                legacy_direct_to_clarify += 1
            else:
                failures.append(
                    f"{query!r} legacy={legacy_action} new={new_action}"
                )

        self.assertFalse(failures, "\n".join(failures))
        self.assertGreaterEqual(legacy_plan_to_clarify, 1)
        self.assertGreaterEqual(legacy_direct_to_clarify, 1)

    def test_clarify_node_does_not_call_llm(self):
        with patch.object(nodes, "_invoke_json_agent", side_effect=AssertionError("clarify should not call LLM")):
            result = nodes.clarify_node(
                {
                    "query": "帮我做AI产品分析",
                    "confidence": 0.70,
                    "intent_reason": "matched medium multiagent keyword: 分析",
                }
            )

        self.assertEqual("clarify", result["intent"])
        self.assertEqual([], result["messages"])


if __name__ == "__main__":
    unittest.main()
