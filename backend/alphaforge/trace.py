"""Execution trace shared by all agents. It IS the explanation: nothing is written after the fact.

Each agent appends the tool calls it really made (steps), the data it really read (sources),
the hypotheses it applied (assumptions), known limits, governance checks and claims.
A claim is a sentence shown to the user, tagged with its epistemic status:
  fact        - read or computed from a cited dataset (sourceIds required)
  assumption  - a modelling choice of ours (e.g. bond duration, policy thresholds)
  hypothesis  - a fictitious scenario (e.g. "rates +200 bps")
"""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

log = logging.getLogger("alphaforge.trace")


class Trace:
    def __init__(self, request_id: str = "local"):
        self.request_id = request_id
        self.steps: List[dict] = []
        self.sources: Dict[str, dict] = {}
        self.assumptions: List[str] = []
        self.limitations: List[str] = []
        self.checks: List[dict] = []
        self.claims: List[dict] = []
        self.uncertainties: List[str] = []
        self.decisions: List[dict] = []  # intermediate decisions (e.g. rebalancing iterations)

    @contextmanager
    def step(self, agent_id: str, tool: str, params: Optional[dict] = None):
        rec = {"agentId": agent_id, "tool": tool, "params": params or {}, "status": "ok"}
        t0 = time.perf_counter()
        try:
            yield rec
        except Exception:
            rec["status"] = "error"
            raise
        finally:
            rec["durationMs"] = int((time.perf_counter() - t0) * 1000)
            self.steps.append(rec)
            # Structured log line -> CloudWatch Logs (searchable by requestId)
            log.info(json.dumps({"requestId": self.request_id, "type": "agent_step", **{k: v for k, v in rec.items() if k != "output"}},
                                default=str))

    def source(self, sid: str, dataset: str, as_of: str, note: str = "") -> str:
        self.sources.setdefault(sid, {"id": sid, "dataset": dataset, "asOf": as_of, "note": note})
        return sid

    def assume(self, text: str):
        if text not in self.assumptions:
            self.assumptions.append(text)

    def limit(self, text: str):
        if text not in self.limitations:
            self.limitations.append(text)

    def uncertain(self, text: str):
        if text not in self.uncertainties:
            self.uncertainties.append(text)

    def check(self, agent_id: str, rule: str, status: str, message: str, value: Any = None, threshold: Any = None):
        c = {"agentId": agent_id, "rule": rule, "status": status, "message": message}
        if value is not None:
            c["value"] = value
        if threshold is not None:
            c["threshold"] = threshold
        self.checks.append(c)

    def claim(self, text: str, kind: str = "fact", source_ids: Optional[List[str]] = None, agent_id: str = ""):
        self.claims.append({"text": text, "kind": kind, "sourceIds": source_ids or [], "agentId": agent_id})

    def decide(self, agent_id: str, decision: str, reason: str):
        self.decisions.append({"agentId": agent_id, "decision": decision, "reason": reason})

    def to_explanation(self) -> dict:
        return {
            "requestId": self.request_id,
            "sources": list(self.sources.values()),
            "assumptions": self.assumptions,
            "limitations": self.limitations,
            "steps": self.steps,
            "checks": self.checks,
            "claims": self.claims,
            "uncertainties": self.uncertainties,
            "decisions": self.decisions,
        }
