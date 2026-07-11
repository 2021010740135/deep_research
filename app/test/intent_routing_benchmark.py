import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src = root / "app"
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from mult_agents.nodes import RULE_SKIP_THRESHOLD, detect_intent


def _ratio(value: int, total: int) -> float:
    if total == 0:
        return 0.0
    return value / total


def evaluate_cases(cases) -> dict:
    from app.test.test_intent_routing_accuracy import (
        _legacy_route_action,
        _new_rule_route_action,
    )

    total_cases = len(cases)
    expected_clarify = [case for case in cases if case.expected_action == "clarify"]
    expected_clarify_count = len(expected_clarify)

    legacy_correct = 0
    new_correct = 0
    legacy_false_plan_on_clarify = 0
    new_false_plan_on_clarify = 0
    new_clarify_hits = 0
    new_intent_llm_calls = 0

    by_group: dict[str, dict[str, int]] = {}

    for case in cases:
        legacy_action = _legacy_route_action(case.query)
        new_action = _new_rule_route_action(case.query)

        if legacy_action == case.expected_action:
            legacy_correct += 1
        if new_action == case.expected_action:
            new_correct += 1

        if case.expected_action == "clarify":
            if legacy_action == "plan":
                legacy_false_plan_on_clarify += 1
            if new_action == "plan":
                new_false_plan_on_clarify += 1
            if new_action == "clarify":
                new_clarify_hits += 1

        decision = detect_intent(case.query)
        if decision.confidence < RULE_SKIP_THRESHOLD:
            new_intent_llm_calls += 1

        group_stats = by_group.setdefault(
            case.group,
            {"total": 0, "legacy_correct": 0, "new_correct": 0},
        )
        group_stats["total"] += 1
        group_stats["legacy_correct"] += int(legacy_action == case.expected_action)
        group_stats["new_correct"] += int(new_action == case.expected_action)

    legacy_intent_llm_calls = total_cases

    return {
        "total_cases": total_cases,
        "expected_clarify_cases": expected_clarify_count,
        "legacy_correct": legacy_correct,
        "new_correct": new_correct,
        "legacy_accuracy": _ratio(legacy_correct, total_cases),
        "new_accuracy": _ratio(new_correct, total_cases),
        "accuracy_delta": _ratio(new_correct, total_cases) - _ratio(legacy_correct, total_cases),
        "legacy_false_plan_on_clarify": legacy_false_plan_on_clarify,
        "new_false_plan_on_clarify": new_false_plan_on_clarify,
        "false_plan_reduction": legacy_false_plan_on_clarify - new_false_plan_on_clarify,
        "new_clarify_guard_rate": _ratio(new_clarify_hits, expected_clarify_count),
        "legacy_intent_llm_calls": legacy_intent_llm_calls,
        "new_intent_llm_calls": new_intent_llm_calls,
        "intent_llm_calls_saved_vs_legacy": legacy_intent_llm_calls - new_intent_llm_calls,
        "clarify_node_llm_calls": 0,
        "by_group": by_group,
    }


def format_report(metrics: dict) -> str:
    lines = [
        "Intent routing benchmark",
        f"- total cases: {metrics['total_cases']}",
        f"- legacy accuracy: {metrics['legacy_accuracy']:.2%} ({metrics['legacy_correct']}/{metrics['total_cases']})",
        f"- new accuracy: {metrics['new_accuracy']:.2%} ({metrics['new_correct']}/{metrics['total_cases']})",
        f"- accuracy delta: {metrics['accuracy_delta']:.2%}",
        f"- expected clarify cases: {metrics['expected_clarify_cases']}",
        f"- legacy false plan on clarify cases: {metrics['legacy_false_plan_on_clarify']}",
        f"- new false plan on clarify cases: {metrics['new_false_plan_on_clarify']}",
        f"- false plan reduction: {metrics['false_plan_reduction']}",
        f"- new clarify guard rate: {metrics['new_clarify_guard_rate']:.2%}",
        f"- legacy intent LLM calls: {metrics['legacy_intent_llm_calls']}",
        f"- new intent LLM calls: {metrics['new_intent_llm_calls']}",
        f"- intent LLM calls saved vs legacy: {metrics['intent_llm_calls_saved_vs_legacy']}",
        f"- clarify node LLM calls: {metrics['clarify_node_llm_calls']}",
        "",
        "By group:",
    ]

    for group, stats in sorted(metrics["by_group"].items()):
        total = stats["total"]
        legacy_accuracy = _ratio(stats["legacy_correct"], total)
        new_accuracy = _ratio(stats["new_correct"], total)
        lines.append(
            f"- {group}: total={total}, legacy={legacy_accuracy:.2%}, new={new_accuracy:.2%}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    from app.test.test_intent_routing_accuracy import _build_cases

    print(format_report(evaluate_cases(_build_cases())))
