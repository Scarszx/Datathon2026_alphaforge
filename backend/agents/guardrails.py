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

from backend.agents import telemetry
from backend.agents.observability import log_event
from backend.common import config

_CLIENT = None


@dataclass
class GuardrailResult:
    blocked: bool
    text: str  # texte d'origine, ou masqué, ou message de refus si blocked
    checked: bool  # False si le Guardrail n'a pas pu s'exécuter (fail-open)


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


def apply(text: str, source: str, client=None) -> GuardrailResult:
    """source = 'INPUT' (message utilisateur) ou 'OUTPUT' (texte affiché)."""
    guardrail_id, version = config.guardrail_id(), config.guardrail_version()
    if not text or not guardrail_id or not version:
        return GuardrailResult(False, text, False)
    with telemetry.trace_span(
        f"guardrail.{source.lower()}",
        observation_type="guardrail",
        input_data={"source": source, "textLength": len(text)},
    ) as span:
        try:
            response = (client or _client()).apply_guardrail(
                guardrailIdentifier=guardrail_id, guardrailVersion=version, source=source,
                content=[{"text": {"text": text}}],
            )
        except Exception as exc:  # panne : fail-open, journalisée sans le texte
            log_event("guardrail.error", source=source, error=type(exc).__name__)
            res = GuardrailResult(False, text, False)
            telemetry.set_span_output(span, {"blocked": res.blocked, "checked": res.checked, "error": type(exc).__name__})
            return res
        outputs = response.get("outputs") or []
        replacement = outputs[0].get("text") if outputs else None
        if response.get("action") != "GUARDRAIL_INTERVENED":
            res = GuardrailResult(False, text, True)
            telemetry.set_span_output(span, {"blocked": res.blocked, "checked": res.checked})
            return res
        if _has_blocked_action(response.get("assessments")):
            log_event("guardrail.blocked", source=source)
            res = GuardrailResult(True, replacement or "This request is outside what this simulation can do.", True)
            telemetry.set_span_output(span, {"blocked": res.blocked, "checked": res.checked})
            return res
        res = GuardrailResult(False, replacement or text, True)
        telemetry.set_span_output(span, {"blocked": res.blocked, "checked": res.checked, "anonymized": True})
        return res
