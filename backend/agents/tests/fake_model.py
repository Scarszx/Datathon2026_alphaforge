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


class FakeTranslate:
    """Faux client boto3 `translate` : traduit en renvoyant `translations[anglais]` ou « FR » + l'anglais.

    Il reçoit le HTML réellement envoyé (balises translate="no" comprises), le garde dans `calls`, et renvoie du HTML
    comme Amazon Translate : les segments protégés restent enveloppés, `&` redevient `&amp;`.
    `delays` : secondes d'attente par texte anglais ; `errors` : texte anglais -> exception à lever ;
    `raw` : texte anglais -> HTML renvoyé tel quel (pour simuler des défauts de traduction)."""

    def __init__(self, translations: dict[str, str] | None = None, *, delays: dict[str, float] | None = None,
                 errors: dict[str, Exception] | None = None, raw: dict[str, str] | None = None):
        self.translations = dict(translations or {})
        self.delays, self.errors, self.raw = delays or {}, errors or {}, raw or {}
        self.calls: list[dict[str, Any]] = []
        self.terminology_missing = False

    def translate_document(self, **params: Any) -> dict[str, Any]:
        import time

        from backend.agents.translate import service

        html_in = params["Document"]["Content"].decode("utf-8")
        english = service.unprotect(html_in)
        self.calls.append({"english": english, "html": html_in, "params": params, "start": time.perf_counter()})
        if params.get("TerminologyNames") and self.terminology_missing:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "ResourceNotFoundException", "Message": "no terminology"}}, "TranslateDocument")
        time.sleep(self.delays.get(english, 0.0))
        if english in self.errors:
            raise self.errors[english]
        self.calls[-1]["end"] = time.perf_counter()
        if english in self.raw:
            return {"TranslatedDocument": {"Content": self.raw[english].encode("utf-8")}}
        french = self.translations.get(english, "FR " + english)
        return {"TranslatedDocument": {"Content": service.protect(french).encode("utf-8")}}


class SectionWriter(ScriptedModel):
    """Rédacteur simulé, une section par appel. Indifférent à l'ordre d'arrivée : la section demandée est lue dans
    le prompt (`<section>clé</section>`), et le texte renvoyé dépend d'elle seulement.

    `log` est partagé entre les instances d'un même run : {"calls": {clé: {"start", "end", "system", "record"}}}.
    """

    def __init__(self, log: dict[str, Any], texts: dict[str, str] | None = None, *, delay: float | dict[str, float] = 0.0,
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
        await asyncio.sleep(self.delay.get(key, 0.0) if isinstance(self.delay, dict) else self.delay)
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
