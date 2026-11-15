"""Journaux JSON vers CloudWatch (contrat : observability).

Deux événements : agent.usage (une ligne par invocation d'agent) et tool.call
(une ligne par appel d'outil). Compteurs et paramètres d'outils seulement,
jamais le texte des questions ni des réponses. Une seule fonction par événement,
partagée par tous les composants : un renommage de champ casserait les requêtes
Logs Insights sans erreur.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def log_tool_call(record: dict[str, Any], *, session_id: str | None, message_id: str | None) -> None:
    _emit({
        "event": "tool.call", "agentId": record["agentId"], "sessionId": session_id, "messageId": message_id,
        "tool": record["tool"], "params": record.get("params"), "status": record["status"],
        "durationMs": record["durationMs"], "source": record.get("source"),
    })


def log_agent_usage(agent_id: str, result: Any, *, session_id: str | None, message_id: str | None, model_id: str | None) -> None:
    """Lit result.metrics (Strands AgentResult) ; tolère un résultat sans métriques (tests)."""
    metrics = getattr(result, "metrics", None)
    usage = getattr(metrics, "accumulated_usage", None) or {}
    _emit({
        "event": "agent.usage", "agentId": agent_id, "sessionId": session_id, "messageId": message_id,
        "modelId": model_id, "inputTokens": usage.get("inputTokens", 0), "outputTokens": usage.get("outputTokens", 0),
        "cycles": getattr(metrics, "cycle_count", 0), "stopReason": getattr(result, "stop_reason", None),
    })


def log_event(name: str, **fields: Any) -> None:
    """Événement technique (erreur, repli) : jamais de texte utilisateur."""
    _emit({"event": name, **fields})
