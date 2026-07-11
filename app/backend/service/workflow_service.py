import asyncio
from threading import Lock, Thread
from typing import AsyncIterator, Callable

from mult_agents.config import AppConfig
from mult_agents.graph import build_app as build_workflow_app
from mult_agents.main import build_agents, build_checkpointer, build_memory_manager
from mult_agents.state import create_initial_state


class WorkflowService:
    def __init__(self, config_path: str):
        self._config_path = config_path
        self._lock = Lock()
        self._initialized = False
        self._base_config: AppConfig | None = None
        self._memory_manager = None
        self._app = None
        self._pending_clarifications: dict[tuple[str, str, str], dict] = {}

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            base_config = AppConfig.from_file(self._config_path)
            self._memory_manager = build_memory_manager(base_config)
            agents = build_agents(base_config.model, base_config.api_key, base_config)
            checkpointer = build_checkpointer(base_config)
            self._app = build_workflow_app(agents, checkpointer)
            self._base_config = base_config
            self._initialized = True

    def _build_runtime_config(
        self,
        user_id: str,
        thread_id: str,
        tenant_id: str,
        max_iterations: int | None,
        enable_memory: bool | None,
    ) -> AppConfig:
        if self._base_config is None:
            raise RuntimeError("service not initialized")
        overrides = {
            "user_id": user_id,
            "thread_id": thread_id,
            "tenant_id": tenant_id,
            "max_iterations": max_iterations if max_iterations is not None else self._base_config.max_iterations,
        }
        if enable_memory is not None:
            overrides["enable_memory"] = enable_memory
        return self._base_config.with_overrides(**overrides)

    def _run_sync(
        self,
        query: str,
        user_id: str,
        thread_id: str,
        tenant_id: str,
        max_iterations: int | None,
        enable_memory: bool | None,
        clarification_action: str | None = None,
        original_query: str | None = None,
    ) -> tuple[str, str]:
        self._ensure_initialized()
        clarification_key = (tenant_id, user_id, thread_id)
        pending_clarification = self._pending_clarifications.get(clarification_key)
        action = (clarification_action or "").strip()
        if action and action not in {"direct_answer", "deep_research"}:
            raise ValueError(f"invalid clarification_action: {action}")
        if pending_clarification and not action:
            raise ValueError("clarification_required")
        effective_query = query
        if action:
            effective_query = (
                str((pending_clarification or {}).get("original_query") or original_query or query).strip()
            )
            if not effective_query:
                raise ValueError("missing original query for clarification")
        runtime_config = self._build_runtime_config(
            user_id=user_id,
            thread_id=thread_id,
            tenant_id=tenant_id,
            max_iterations=max_iterations,
            enable_memory=enable_memory,
        )
        memory_context = ""
        if self._memory_manager and runtime_config.enable_memory and route != "clarify":
            memory_context = self._memory_manager.build_personalized_prompt_context(
                user_id=runtime_config.user_id,
                thread_id=runtime_config.thread_id,
                query=effective_query,
                tenant_id=runtime_config.tenant_id,
                max_memories=runtime_config.memory_top_k,
            )
        state = create_initial_state(
            query=effective_query,
            max_iterations=runtime_config.max_iterations,
            user_id=runtime_config.user_id,
            tenant_id=runtime_config.tenant_id,
            memory_context=memory_context,
        )
        state["clarification_action"] = action
        state["original_query"] = effective_query if action else (original_query or "")
        result = self._app.invoke(
            state,
            {"configurable": {"thread_id": runtime_config.thread_id}},
        )
        final = result.get("final", "")
        route = str(result.get("intent", "multiagent"))
        if route == "clarify":
            self._pending_clarifications[clarification_key] = result.get("pending_clarification", {})
        elif action:
            self._pending_clarifications.pop(clarification_key, None)
        if self._memory_manager and runtime_config.enable_memory and route != "clarify":
            self._memory_manager.persist_turn(
                tenant_id=runtime_config.tenant_id,
                user_id=runtime_config.user_id,
                thread_id=runtime_config.thread_id,
                query=effective_query,
                answer=final,
            )
        return final, route

    @staticmethod
    def _node_message(node_name: str) -> str:
        mapping = {
            "intent": "Intent Router 正在识别问题意图",
            "direct_answer": "Direct Responder 正在快速作答",
            "plan": "Planner 正在拆解问题",
            "web_search": "Web Scout 正在检索网络证据",
            "local_rag": "Local Scout 正在检索本地知识库",
            "deep_dive": "Evidence Judge 正在进行证据裁判",
            "analyze": "Analyst 正在生成结论",
            "reflect": "Reflect 正在生成补搜计划",
            "write": "Writer 正在撰写最终报告",
        }
        return mapping.get(node_name, f"{node_name} 正在执行")

    def _run_sync_with_events(
        self,
        query: str,
        user_id: str,
        thread_id: str,
        tenant_id: str,
        max_iterations: int | None,
        enable_memory: bool | None,
        emit: Callable[[dict], None],
        clarification_action: str | None = None,
        original_query: str | None = None,
    ) -> tuple[str, str]:
        self._ensure_initialized()
        clarification_key = (tenant_id, user_id, thread_id)
        pending_clarification = self._pending_clarifications.get(clarification_key)
        action = (clarification_action or "").strip()
        if action and action not in {"direct_answer", "deep_research"}:
            raise ValueError(f"invalid clarification_action: {action}")
        if pending_clarification and not action:
            raise ValueError("clarification_required")
        effective_query = query
        if action:
            effective_query = str(
                (pending_clarification or {}).get("original_query") or original_query or query
            ).strip()
            if not effective_query:
                raise ValueError("missing original query for clarification")
        runtime_config = self._build_runtime_config(
            user_id=user_id,
            thread_id=thread_id,
            tenant_id=tenant_id,
            max_iterations=max_iterations,
            enable_memory=enable_memory,
        )
        memory_context = ""
        if self._memory_manager and runtime_config.enable_memory:
            memory_context = self._memory_manager.build_personalized_prompt_context(
                user_id=runtime_config.user_id,
                thread_id=runtime_config.thread_id,
                query=effective_query,
                tenant_id=runtime_config.tenant_id,
                max_memories=runtime_config.memory_top_k,
            )
        state = create_initial_state(
            query=effective_query,
            max_iterations=runtime_config.max_iterations,
            user_id=runtime_config.user_id,
            tenant_id=runtime_config.tenant_id,
            memory_context=memory_context,
        )
        state["clarification_action"] = action
        state["original_query"] = effective_query if action else (original_query or "")
        final = ""
        route = "multiagent"
        config = {"configurable": {"thread_id": runtime_config.thread_id}}
        for update in self._app.stream(state, config, stream_mode="updates"):
            if not isinstance(update, dict):
                continue
            for node_name, node_output in update.items():
                emit({"type": "phase", "node": node_name, "message": self._node_message(str(node_name))})
                if isinstance(node_output, dict):
                    if node_name == "intent":
                        detected = str(node_output.get("intent", route)).strip().lower()
                        if detected in {"direct", "multiagent", "clarify"}:
                            route = detected
                    if node_name == "clarify":
                        route = "clarify"
                        self._pending_clarifications[clarification_key] = node_output.get("pending_clarification", {})
                        emit(
                            {
                                "type": "clarify",
                                "query": effective_query,
                                "user_id": runtime_config.user_id,
                                "thread_id": runtime_config.thread_id,
                                "tenant_id": runtime_config.tenant_id,
                                "final": str(node_output.get("final", "")),
                                "phase": str(node_output.get("phase", "clarification_required")),
                                "clarify_options": node_output.get("clarify_options", []),
                                "pending_clarification": node_output.get("pending_clarification", {}),
                            }
                        )
                    value = node_output.get("final")
                    if value:
                        final = str(value)
        if not final:
            result = self._app.invoke(state, config)
            final = str(result.get("final", ""))
            route = str(result.get("intent", route)).strip().lower()
            if route == "clarify":
                self._pending_clarifications[clarification_key] = result.get("pending_clarification", {})
        if route != "clarify" and action:
            self._pending_clarifications.pop(clarification_key, None)
        if self._memory_manager and runtime_config.enable_memory:
            self._memory_manager.persist_turn(
                tenant_id=runtime_config.tenant_id,
                user_id=runtime_config.user_id,
                thread_id=runtime_config.thread_id,
                query=effective_query,
                answer=final,
            )
        return final, route

    async def run(
        self,
        query: str,
        user_id: str,
        thread_id: str,
        tenant_id: str,
        max_iterations: int | None,
        enable_memory: bool | None,
        clarification_action: str | None = None,
        original_query: str | None = None,
    ) -> str:
        final, _ = await asyncio.to_thread(
            self._run_sync,
            query,
            user_id,
            thread_id,
            tenant_id,
            max_iterations,
            enable_memory,
            clarification_action,
            original_query,
        )
        return final

    async def run_with_route(
        self,
        query: str,
        user_id: str,
        thread_id: str,
        tenant_id: str,
        max_iterations: int | None,
        enable_memory: bool | None,
        clarification_action: str | None = None,
        original_query: str | None = None,
    ) -> tuple[str, str]:
        return await asyncio.to_thread(
            self._run_sync,
            query,
            user_id,
            thread_id,
            tenant_id,
            max_iterations,
            enable_memory,
            clarification_action,
            original_query,
        )

    async def stream_events(
        self,
        query: str,
        user_id: str,
        thread_id: str,
        tenant_id: str,
        max_iterations: int | None,
        enable_memory: bool | None,
        clarification_action: str | None = None,
        original_query: str | None = None,
    ) -> AsyncIterator[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def emit(event: dict) -> None:
            asyncio.run_coroutine_threadsafe(queue.put(event), loop)

        def worker() -> None:
            try:
                final, route = self._run_sync_with_events(
                    query=query,
                    user_id=user_id,
                    thread_id=thread_id,
                    tenant_id=tenant_id,
                    max_iterations=max_iterations,
                    enable_memory=enable_memory,
                    emit=emit,
                    clarification_action=clarification_action,
                    original_query=original_query,
                )
                route_messages = {
                    "direct": "已走直接回答路径",
                    "multiagent": "已走多智能体研究路径",
                    "clarify": "需要你选择直接回答或深度研究",
                }
                emit({"type": "route", "message": route_messages.get(route, f"已走 {route} 路径")})
                emit(
                    {
                        "type": "final",
                        "query": query,
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "tenant_id": tenant_id,
                        "final": final,
                        "route": route,
                    }
                )
            except Exception as exc:
                emit({"type": "error", "message": str(exc)})
            finally:
                emit({"type": "__done__"})

        Thread(target=worker, daemon=True).start()
        while True:
            event = await queue.get()
            if event.get("type") == "__done__":
                break
            yield event
