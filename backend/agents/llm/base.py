"""Construction et exécution d'un agent Strands, communes aux trois agents.

- name = identifiant de l'agent (sinon toutes les traces s'appellent « Strands Agent ») ;
- callback_handler=None : rien sur stdout dans Lambda ;
- limits={"turns": max_agent_cycles} et plafond d'appels d'outils par un hook ;
- délai maximal par cancel_signal (timeout_seconds du contrat) ;
- sortie structurée Pydantic (structured_output_model) ;
- une ligne agent.usage par invocation.
MODEL_FACTORY est injectable : les tests remplacent Bedrock par un faux modèle.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

from pydantic import BaseModel
from strands import Agent
from strands.hooks import BeforeInvocationEvent, BeforeToolCallEvent, HookProvider, HookRegistry

from backend.agents import models
from backend.agents.observability import log_agent_usage
from backend.agents.toolbox import MAX_TOOL_CALLS
from backend.agents.tools.agent_tools import tools_for
from backend.agents.tools.context import RequestContext

MODEL_FACTORY: Callable[[str], Any] = models.create_model


class AgentFailure(RuntimeError):
    """L'agent n'a pas produit de sortie exploitable (délai, limite, sortie invalide)."""

    def __init__(self, agent_id: str, reason: str):
        super().__init__(f"{agent_id}: {reason}")
        self.agent_id = agent_id
        self.reason = reason


class ToolCallLimit(HookProvider):
    """Refuse un appel d'outil au-delà du plafond de l'agent, avant de l'exécuter."""

    def __init__(self, limit: int):
        self.limit = limit
        self.count = 0
        self._lock = threading.Lock()

    def register_hooks(self, registry: HookRegistry, **_: Any) -> None:
        registry.add_callback(BeforeInvocationEvent, self._reset)
        registry.add_callback(BeforeToolCallEvent, self._check)

    def _reset(self, event: BeforeInvocationEvent) -> None:
        with self._lock:
            self.count = 0

    def _check(self, event: BeforeToolCallEvent) -> None:
        with self._lock:
            self.count += 1
            if self.count > self.limit:
                event.cancel_tool = (
                    "Tool call budget spent: answer now with what you have and say clearly what you could not check."
                )


def build_agent(agent_id: str, system_prompt: str, ctx: RequestContext, *, with_tools: bool = True,
                messages: list[dict[str, Any]] | None = None) -> Agent:
    tools = tools_for(agent_id) if with_tools else []
    return Agent(
        model=MODEL_FACTORY(agent_id),
        name=agent_id,
        system_prompt=system_prompt,
        tools=tools,
        messages=messages or [],
        callback_handler=None,
        hooks=[ToolCallLimit(MAX_TOOL_CALLS.get(agent_id, 0))],
        trace_attributes={"session.id": ctx.session_id, "agent.id": agent_id},
    )


def run_agent(agent_id: str, system_prompt: str, prompt: str, ctx: RequestContext, output_model: type[BaseModel], *,
              with_tools: bool = True, messages: list[dict[str, Any]] | None = None) -> BaseModel:
    """Exécute l'agent et renvoie sa sortie structurée, ou lève AgentFailure."""
    from strands.types.exceptions import StructuredOutputException

    spec = models.MODELS[agent_id]
    agent = build_agent(agent_id, system_prompt, ctx, with_tools=with_tools, messages=messages)
    cancel = threading.Event()
    timer = threading.Timer(spec.timeout_seconds, cancel.set)
    timer.daemon = True
    timer.start()
    result = None
    started = time.perf_counter()
    status = "error"
    try:
        result = agent(
            prompt,
            invocation_state={"ctx": ctx, "agent_id": agent_id},
            structured_output_model=output_model,
            limits={"turns": spec.max_turns, "structured_output_attempts": 2},
            cancel_signal=cancel,
        )
        status = "ok" if getattr(result, "structured_output", None) is not None and not cancel.is_set() else "error"
    except StructuredOutputException as exc:
        raise AgentFailure(agent_id, "invalid structured output") from exc
    finally:
        timer.cancel()
        # Étape observée pour explanation (rule-explanation-from-trace) : l'invocation elle-même,
        # même si l'agent n'a appelé aucun outil. Ce n'est pas une ligne tool.call.
        ctx.tool_calls.append({
            "agentId": agent_id, "tool": "agent_invocation", "params": {"output": output_model.__name__},
            "status": status, "durationMs": int((time.perf_counter() - started) * 1000),
        })
        try:
            model_id = models.model_id(agent_id)
        except RuntimeError:
            model_id = None
        log_agent_usage(agent_id, result, session_id=ctx.session_id, message_id=ctx.message_id or ctx.run_id, model_id=model_id)
    if cancel.is_set():
        raise AgentFailure(agent_id, "timeout")
    output = getattr(result, "structured_output", None)
    if output is None:
        raise AgentFailure(agent_id, f"no structured output (stop reason {getattr(result, 'stop_reason', None)})")
    return output
