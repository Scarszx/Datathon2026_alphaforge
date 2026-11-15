"""agent-writer : 4 sections en anglais (textEn), avec emplacements {EV-nn}/{KB-nn} seulement.

Fail-open : en cas d'échec, le run reste utilisable (scénarios, verdicts,
citations) et le texte narratif est absent (contrat agents.agent-writer.fail_mode).
"""

from __future__ import annotations

import json
from typing import Any

from backend.agents.engine.scenarios import HOLDING_LABEL_PREFIX
from backend.agents.llm.base import run_agent
from backend.agents.llm.writer import prompts
from backend.agents.llm.writer.schemas import WriterSections
from backend.agents.tools.context import RequestContext
from backend.agents.verifier.verifier import SECTION_KEYS

AGENT_ID = "agent-writer"


def analysis_record(mandate: dict[str, Any], scenarios: list[dict[str, Any]], verdicts: list[dict[str, Any]],
                    evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Ce que lit le rédacteur : tout en anglais, valeurs incluses pour comparer, jamais pour recopier."""
    return {
        "mandate": {k: mandate.get(k) for k in ("mode", "objective", "objectiveDetail", "horizonYears", "province",
                                                 "operations", "subjectTicker", "compareCategory", "preferences", "fieldSources") if mandate.get(k) is not None},
        "scenarios": [{k: s.get(k) for k in ("index", "label", "description", "proxyNote", "verdict", "metrics", "parameters") if s.get(k) is not None} for s in scenarios],
        "verdicts": [{k: v.get(k) for k in ("rule", "scenario", "status", "reasonCode", "messageEn", "evidence", "citations", "threshold") if v.get(k) is not None} for v in verdicts],
        "evidence": [{k: e.get(k) for k in ("id", "kind", "label", "scenario", "value", "window", "currency", "document", "section", "caveats") if e.get(k) is not None}
                     for e in evidence if not str(e.get("label", "")).startswith(HOLDING_LABEL_PREFIX)],
    }


def write(ctx: RequestContext, record: dict[str, Any]) -> list[dict[str, str]]:
    """Renvoie [{key, textEn}] pour les 4 sections ; lève AgentFailure en cas d'échec."""
    output = run_agent(AGENT_ID, prompts.SYSTEM_PROMPT, prompts.write_prompt(json.dumps(record, ensure_ascii=False)), ctx, WriterSections)
    return [{"key": key, "textEn": getattr(output, key).strip()} for key in SECTION_KEYS]
