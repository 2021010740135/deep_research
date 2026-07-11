"""工作流编排模块：定义 LangGraph 节点、条件路由与整体执行路径。"""

import logging

from langgraph.graph import StateGraph, START, END

from .nodes import (
    bind_agent,
    intent_node,
    clarify_node,
    direct_answer_node,
    plan_node,
    web_search_node,
    local_rag_node,
    deep_dive_node,
    analyze_node,
    reflect_node,
    write_node,
)
from .state import ResearchState


logger = logging.getLogger("mult_agents")


DIRECT_CONFIDENCE_THRESHOLD = 0.90
MULTIAGENT_CONFIDENCE_THRESHOLD = 0.85

TRUSTED_DIRECT_RULES = {
    "greeting_exact_match",
    "introduction_keyword",
    "simple_math",
    "joke_request",
}

TRUSTED_MULTIAGENT_RULES = {
    "year_trend",
    "strong_multiagent_keyword",
}


def _state_confidence(state: ResearchState) -> float:
    try:
        return float(state.get("confidence", 0.0))
    except (TypeError, ValueError):
        return 0.0


def route_after_intent(state: ResearchState) -> str:
    route = str(state.get("intent", "")).strip().lower()
    confidence = _state_confidence(state)
    source = str(state.get("intent_source", "")).strip().lower()
    matched_rule = str(state.get("intent_matched_rule", "")).strip()
    reason = str(state.get("intent_reason", "")).strip().lower()

    if route == "multiagent":
        if source == "user_clarification":
            return "plan"
        if source == "rule" and matched_rule in TRUSTED_MULTIAGENT_RULES:
            return "plan"
        if matched_rule == "medium_multiagent_keyword":
            logger.info(
                "[route_after_intent] medium keyword requires user clarification | confidence=%.2f | source=%s | reason=%s",
                confidence,
                source,
                reason,
            )
            return "clarify"
        if confidence >= MULTIAGENT_CONFIDENCE_THRESHOLD:
            return "plan"

        logger.info(
            "[route_after_intent] low confidence multiagent fallback | confidence=%.2f | source=%s | rule=%s | reason=%s",
            confidence,
            source,
            matched_rule,
            reason,
        )
        return "clarify"

    if route == "direct":
        if source == "user_clarification":
            return "direct_answer"
        if source == "rule" and matched_rule in TRUSTED_DIRECT_RULES:
            return "direct_answer"
        if confidence >= DIRECT_CONFIDENCE_THRESHOLD:
            return "direct_answer"

        logger.info(
            "[route_after_intent] low confidence direct fallback | confidence=%.2f | source=%s | rule=%s | reason=%s",
            confidence,
            source,
            matched_rule,
            reason,
        )
        return "direct_answer"

    logger.warning(
        "[route_after_intent] unknown intent fallback | intent=%s | confidence=%.2f | source=%s | reason=%s",
        route,
        confidence,
        source,
        reason,
    )
    return "direct_answer"


def should_continue_research(state: ResearchState) -> str:
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 2)
    
    # If we reached max iterations, stop and write report
    if iteration >= max_iter:
        return "write"
        
    # If analyst found missing gaps and requested more research, go to reflect
    if state.get("needs_more_research", False):
        return "reflect"
        
    # Otherwise, we have enough evidence, go to write report
    return "write"


def build_app(agents, checkpointer):
    workflow = StateGraph(ResearchState)
    workflow.add_node("intent", bind_agent(intent_node, agents.intent_router, "intent_router"))
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("direct_answer", bind_agent(direct_answer_node, agents.direct_responder, "direct_responder"))
    workflow.add_node("plan", bind_agent(plan_node, agents.planner, "planner"))
    workflow.add_node("web_search", bind_agent(web_search_node, agents.scout_web, "scout_web"))
    workflow.add_node("local_rag", bind_agent(local_rag_node, agents.scout_local, "scout_local"))
    workflow.add_node("deep_dive", bind_agent(deep_dive_node, agents.evidence_judge, "evidence_judge"))
    workflow.add_node("analyze", bind_agent(analyze_node, agents.analyst, "analyst"))
    workflow.add_node("reflect", bind_agent(reflect_node, agents.planner, "planner"))
    workflow.add_node("write", bind_agent(write_node, agents.writer, "writer"))
    
    workflow.add_edge(START, "intent")
    workflow.add_conditional_edges(
        "intent",
        route_after_intent,
        {
            "direct_answer": "direct_answer",
            "clarify": "clarify",
            "plan": "plan",
        },
    )
    workflow.add_edge("plan", "web_search")
    workflow.add_edge("plan", "local_rag")
    workflow.add_edge("web_search", "deep_dive")
    workflow.add_edge("local_rag", "deep_dive")
    workflow.add_edge("deep_dive", "analyze")
    
    workflow.add_conditional_edges(
        "analyze",
        should_continue_research,
        {
            "reflect": "reflect",
            "write": "write"
        }
    )
    
    workflow.add_edge("reflect", "web_search")
    workflow.add_edge("reflect", "local_rag")
    workflow.add_edge("clarify", END)
    workflow.add_edge("direct_answer", END)
    workflow.add_edge("write", END)
    
    return workflow.compile(checkpointer=checkpointer)
