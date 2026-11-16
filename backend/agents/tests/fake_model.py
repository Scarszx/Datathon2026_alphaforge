"""Faux modèle Strands scripté : aucun appel Bedrock dans les tests.

Chaque élément du script est la réponse d'un tour de modèle : une liste
d'appels d'outils {"name", "input"} ou un texte. Le vrai Agent Strands
exécute donc la vraie boucle (outils, hooks, sortie structurée), seul le
modèle est remplacé.
"""

from __future__ import annotations

import itertools
import json
from typing import Any, AsyncIterable

from strands.models.model import Model

_ids = itertools.count(1)


class ScriptedModel(Model):
    def __init__(self, script: list[Any]):
        self.script = list(script)
        self.calls: list[dict[str, Any]] = []  # ce que le modèle a reçu (messages, outils)

    def get_config(self) -> dict[str, Any]:
        return {}

    def update_config(self, **model_config: Any) -> None:
        return None

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):  # pragma: no cover
        raise NotImplementedError
        yield  # noqa

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs) -> AsyncIterable[dict[str, Any]]:
        self.calls.append({
            "messages": json.loads(json.dumps(messages, default=str)),
            "tools": [spec["name"] for spec in tool_specs or []],
            "system_prompt": system_prompt,
        })
        response = self.script.pop(0) if self.script else "No more scripted responses."
        if isinstance(response, Exception):
            raise response
        yield {"messageStart": {"role": "assistant"}}
        if isinstance(response, str):
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": response}}}
            yield {"contentBlockStop": {}}
            stop = "end_turn"
        else:
            for call in response:
                yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"t{next(_ids)}", "name": call["name"]}}}}
                yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(call["input"])}}}}
                yield {"contentBlockStop": {}}
            stop = "tool_use"
        yield {"messageStop": {"stopReason": stop}}
        yield {"metadata": {"usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}, "metrics": {"latencyMs": 1}}}


def output(name: str, **fields: Any) -> list[dict[str, Any]]:
    """Tour qui appelle l'outil de sortie structurée `name` (nom de la classe Pydantic)."""
    return [{"name": name, "input": fields}]


def call(name: str, **params: Any) -> list[dict[str, Any]]:
    return [{"name": name, "input": params}]


class EchoTranslator(ScriptedModel):
    """Traducteur simulé : renvoie chaque élément reçu préfixé, emplacements conservés."""

    def __init__(self, prefix: str = "FR "):
        super().__init__([])
        self.prefix = prefix

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        text = messages[-1]["content"][0].get("text", "")
        items = json.loads(text.split("<items>\n", 1)[1].split("\n</items>", 1)[0])
        self.script = [output("TranslationBatch", items=[self.prefix + item for item in items])]
        async for chunk in super().stream(messages, tool_specs, system_prompt, **kwargs):
            yield chunk


class SectionWriter(ScriptedModel):
    """Rédacteur simulé, une section par appel. Indifférent à l'ordre d'arrivée : la section demandée est lue dans
    le prompt (`<section>clé</section>`), et le texte renvoyé dépend d'elle seulement.

    `log` est partagé entre les instances d'un même run : {"calls": {clé: {"start", "end", "system", "record"}}}.
    """

    def __init__(self, log: dict[str, Any], texts: dict[str, str] | None = None, *, delay: float = 0.0,
                 fail: set[str] = frozenset(), evidence_reads: int = 0):  # type: ignore[assignment]
        super().__init__([])
        self.log, self.texts, self.delay, self.fail, self.evidence_reads = log, texts or {}, delay, fail, evidence_reads

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        import asyncio
        import time

        text = messages[0]["content"][0]["text"]
        key = text.split("<section>", 1)[1].split("</section>", 1)[0]
        entry = self.log["calls"].setdefault(key, {"start": time.perf_counter(), "system": system_prompt,
                                                   "record": json.loads(text.split("<analysis_record>\n", 1)[1].split("\n</analysis_record>", 1)[0])})
        await asyncio.sleep(self.delay)
        if key in self.fail:
            self.script = ["no output"] * 3
        else:
            final = output("SectionText", text=self.texts.get(key, f"Text of {key}."))
            # Premier tour : `evidence_reads` lectures du registre en un seul tour, puis la section.
            first = len(messages) == 1 and self.evidence_reads
            self.script = [[{"name": "read_evidence", "input": {}}] * self.evidence_reads, final] if first else [final]
        async for chunk in super().stream(messages, tool_specs, system_prompt, **kwargs):
            yield chunk
        entry["end"] = time.perf_counter()


def add_section_writers(scripts, texts: dict[str, str] | None = None, **options: Any) -> dict[str, Any]:
    """Enregistre 4 rédacteurs simulés identiques (un par section) ; renvoie le journal partagé de leurs appels."""
    log: dict[str, Any] = {"calls": {}}
    for _ in range(4):
        scripts.add("agent-writer", SectionWriter(log, texts, **options))
    return log
