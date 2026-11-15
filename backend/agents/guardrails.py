"""Bedrock Guardrails en entrée et en sortie (ApplyGuardrail), contrat srv-bedrock-guardrails.

- Fail-closed sur une décision explicite : un blocage n'est jamais ignoré.
- Fail-open sur une panne (Guardrail non configuré, erreur réseau) : la
  disponibilité de la démo prime ; le prompt de l'orchestrateur et le
  vérificateur restent en place. La panne est journalisée.
Un masquage (ANONYMIZE) n'est pas un blocage : le texte masqué est renvoyé.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.agents.observability import log_event
from backend.common import config

_CLIENT = None


@dataclass
class GuardrailResult:
    blocked: bool
    text: str  # texte d'origine, ou masqué, ou message de refus si blocked
    checked: bool  # False si le Guardrail n'a pas pu s'exécuter (fail-open)
    blocked_by_pii: bool = False
    blocked_by_topic: bool = False


def _client():
    global _CLIENT
    if _CLIENT is None:
        import boto3

        _CLIENT = boto3.client("bedrock-runtime", region_name="us-east-1")
    return _CLIENT


def _has_blocked_action(node: Any) -> bool:
    if isinstance(node, dict):
        if node.get("action") == "BLOCKED":
            return True
        return any(_has_blocked_action(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_blocked_action(v) for v in node)
    return False


def _policy_blocked(assessments: Any, policy_key: str) -> bool:
    if not isinstance(assessments, list):
        return False
    return any(_has_blocked_action(a.get(policy_key)) for a in assessments if isinstance(a, dict))


def apply(text: str, source: str, client=None) -> GuardrailResult:
    """source = 'INPUT' (message utilisateur) ou 'OUTPUT' (texte affiché)."""
    guardrail_id, version = config.guardrail_id(), config.guardrail_version()
    if not text or not guardrail_id or not version:
        return GuardrailResult(False, text, False)
    try:
        response = (client or _client()).apply_guardrail(
            guardrailIdentifier=guardrail_id, guardrailVersion=version, source=source,
            content=[{"text": {"text": text}}],
        )
    except Exception as exc:  # panne : fail-open, journalisée sans le texte
        log_event("guardrail.error", source=source, error=type(exc).__name__)
        return GuardrailResult(False, text, False)
    outputs = response.get("outputs") or []
    replacement = outputs[0].get("text") if outputs else None
    if response.get("action") != "GUARDRAIL_INTERVENED":
        return GuardrailResult(False, text, True)
    assessments = response.get("assessments")
    if _has_blocked_action(assessments):
        by_pii = _policy_blocked(assessments, "sensitiveInformationPolicy")
        by_topic = _policy_blocked(assessments, "topicPolicy")
        log_event("guardrail.blocked", source=source, byPii=by_pii, byTopic=by_topic)
        return GuardrailResult(
            True,
            replacement or "This request is outside what this simulation can do.",
            True,
            blocked_by_pii=by_pii,
            blocked_by_topic=by_topic,
        )
    return GuardrailResult(False, replacement or text, True)
