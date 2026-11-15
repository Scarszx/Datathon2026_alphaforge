"""agent-auditor : fonde chaque verdict sur un passage de la KB (citations KB-nn) et formule messageEn.

Les verdicts sont regroupés par (règle, statut) : une recherche sert tous les
scénarios d'une même règle. L'auditeur ne renvoie que des références de
passages (P1…) ; le code reconstruit la citation à partir de ce que la KB a
réellement renvoyé (ctx.passages). Une référence inconnue est ignorée : aucune
citation ne peut être inventée. Fail-closed : si l'auditeur échoue, les
verdicts gardent leur motif par défaut et restent sans citation
(« fondement : hypothèse d'équipe » ou not_verified côté affichage).
"""

from __future__ import annotations

import json
from typing import Any

from backend.agents.engine.registry import EvidenceRegistry
from backend.agents.llm.auditor import prompts
from backend.agents.llm.auditor.schemas import AuditReport
from backend.agents.llm.base import AgentFailure, run_agent
from backend.agents.observability import log_event
from backend.agents.rules.rules import RULE_SUBJECTS, RULE_TOPICS
from backend.agents.tools.context import RequestContext
from backend.agents.verifier.verifier import forbidden_phrases, handwritten_numbers

AGENT_ID = "agent-auditor"


def verdict_groups(verdicts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for verdict in verdicts:
        key = f"{verdict['rule']}:{verdict['status']}"
        group = groups.setdefault(key, {
            "key": key, "rule": verdict["rule"], "status": verdict["status"], "reasonCode": verdict["reasonCode"],
            "defaultMessage": verdict["messageEn"], "suggestedTopic": RULE_TOPICS.get(verdict["rule"]),
            "suggestedSubjects": RULE_SUBJECTS.get(verdict["rule"], []), "scenarios": [],
            "thresholdNature": (verdict.get("threshold") or {}).get("nature"),
        })
        if "scenario" in verdict:
            group["scenarios"].append(verdict["scenario"])
    return groups


def _safe_message(message: str, fallback: str) -> str:
    """Un motif avec un chiffre ou une formule interdite retombe sur la phrase par défaut."""
    if not message.strip() or handwritten_numbers(message, set()) or forbidden_phrases(message):
        return fallback
    return message.strip()


def audit(ctx: RequestContext, verdicts: list[dict[str, Any]], registry: EvidenceRegistry) -> list[dict[str, Any]]:
    """Renvoie les verdicts enrichis (citations, messageEn) ; inscrit les KB-nn au registre."""
    groups = verdict_groups(verdicts)
    try:
        report = run_agent(AGENT_ID, prompts.SYSTEM_PROMPT, prompts.audit_prompt(json.dumps(list(groups.values()), ensure_ascii=False)), ctx, AuditReport)
    except AgentFailure as failure:
        log_event("agent.failure", agentId=AGENT_ID, reason=failure.reason, sessionId=ctx.session_id)
        return verdicts
    kb_by_ref: dict[str, str] = {}
    by_key: dict[str, tuple[list[str], str]] = {}
    for item in report.items:
        if item.key not in groups:
            continue
        citations = []
        for ref in item.passage_refs:
            passage = ctx.passages.get(ref)
            if passage is None:
                continue  # référence inventée : ignorée
            if ref not in kb_by_ref:
                kb_by_ref[ref] = registry.add_regulation(
                    document=passage["document"], section=passage.get("section"), excerpt=passage["excerpt"],
                    jurisdiction=passage.get("jurisdiction") or "CA", url=passage.get("url"),
                    as_of=passage.get("version"),
                    source=f"Bedrock Knowledge Base: {passage.get('file') or passage['document']}",
                )
            citations.append(kb_by_ref[ref])
        by_key[item.key] = (citations, _safe_message(item.message_en, groups[item.key]["defaultMessage"]))
    enriched = []
    for verdict in verdicts:
        citations, message = by_key.get(f"{verdict['rule']}:{verdict['status']}", ([], verdict["messageEn"]))
        enriched.append({**verdict, "citations": citations, "messageEn": message})
    return enriched
