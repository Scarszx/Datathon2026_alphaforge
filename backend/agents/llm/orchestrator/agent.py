"""agent-orchestrator : tour de conversation (cadrage) et traduction de la restitution."""

from __future__ import annotations

import json
from typing import Any

from backend.agents.llm.base import AgentFailure, run_agent
from backend.agents.llm.orchestrator import prompts
from backend.agents.llm.orchestrator.schemas import OrchestratorTurn, TranslationBatch
from backend.agents.tools.context import RequestContext
from backend.agents.verifier.verifier import placeholders

AGENT_ID = "agent-orchestrator"
TRANSLATION_BATCH = 6  # quelques textes par appel : rester sous max_tokens (1024)


def history_messages(items: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    """Historique Strands reconstruit depuis la table Messages (texte seulement).

    Les rôles doivent alterner et commencer par l'utilisateur ; un message refusé
    n'est jamais dans la table, donc jamais dans l'historique.
    """
    messages: list[dict[str, Any]] = []
    for item in items[-limit:]:
        role = item.get("role")
        text = (item.get("content") or "").strip()
        if role not in ("user", "assistant") or not text:
            continue
        if not messages and role != "user":
            continue
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"][0]["text"] += "\n" + text
            continue
        messages.append({"role": role, "content": [{"text": text}]})
    if messages and messages[-1]["role"] == "user":
        messages.pop()  # le tour courant est envoyé à part
    return messages


def converse(ctx: RequestContext, session_context: dict[str, Any], user_message: str,
             history: list[dict[str, Any]]) -> OrchestratorTurn:
    prompt = prompts.turn_prompt(json.dumps(session_context, ensure_ascii=False), user_message)
    output = run_agent(AGENT_ID, prompts.SYSTEM_PROMPT, prompt, ctx, OrchestratorTurn, messages=history)
    assert isinstance(output, OrchestratorTurn)
    return output


def translate(ctx: RequestContext, texts: list[str], target_language: str) -> list[str]:
    """Traduit des textes en conservant les emplacements ; un texte dont les emplacements
    changent garde sa version anglaise (le vérificateur le signalera par placeholdersMatch)."""
    if target_language == "en" or not texts:
        return list(texts)
    translated: list[str] = []
    for start in range(0, len(texts), TRANSLATION_BATCH):
        batch = texts[start:start + TRANSLATION_BATCH]
        try:
            output = run_agent(
                AGENT_ID, prompts.TRANSLATE_PROMPT,
                prompts.translate_prompt(target_language, json.dumps(batch, ensure_ascii=False)),
                ctx, TranslationBatch, with_tools=False,
            )
            items = list(output.items) if len(output.items) == len(batch) else list(batch)
        except AgentFailure:
            items = list(batch)
        translated.extend(items)
    return translated


def placeholders_preserved(source: str, target: str) -> bool:
    return sorted(placeholders(source)) == sorted(placeholders(target))
