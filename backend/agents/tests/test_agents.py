"""Les trois agents Strands avec un faux modèle scripté (vraie boucle Strands, aucun appel Bedrock)."""

from __future__ import annotations

import json

import pytest

from backend.agents import models
from backend.agents.engine.registry import EvidenceRegistry
from backend.agents.llm.auditor import agent as auditor
from backend.agents.llm.base import AgentFailure
from backend.agents.llm.orchestrator import agent as orchestrator
from backend.agents.llm.writer import agent as writer
from backend.agents.tests.conftest import USER
from backend.agents.tests.fake_model import call, output
from backend.agents.tools.context import RequestContext
from backend.agents.tests.test_tools import FakeKb, _kb_result

DRAFT = {"mode": "add_asset", "objective": "project", "objectiveDetail": "condo purchase in 3 years", "horizonYears": 3,
         "riskTolerance": 3, "riskCapacity": 1, "province": "QC",
         "operations": [{"action": "add", "ticker": "NVDA", "amount": 15000, "currency": "CAD"}]}


def _turn(lang="fr", reply="Voici le mandat proposé."):
    return output("OrchestratorTurn", user_language=lang, english_request="What if I add 15,000 CAD of NVDA for a condo in 3 years?",
                  reply=reply, quick_replies=["Confirmer"])


@pytest.fixture
def ctx(aws, store):
    return RequestContext(user_id=USER, session_id="s1", store=store, province="QC", user_language="fr")


def test_orchestrateur_cadrage_et_mandat(ctx, scripts):
    scripts.add("agent-orchestrator", call("get_profile"), call("propose_mandate", draft=DRAFT), _turn())
    turn = orchestrator.converse(ctx, {"province": "QC"}, "Et si j'ajoute 15 000 $ de NVDA pour un condo dans 3 ans ?", [])
    assert turn.user_language == "fr" and turn.quick_replies == ["Confirmer"]
    assert ctx.captured["mandateDraft"]["operations"][0]["ticker"] == "NVDA"
    assert [c["tool"] for c in ctx.tool_calls] == ["get_profile", "propose_mandate", "agent_invocation"]
    assert all(c["agentId"] == "agent-orchestrator" for c in ctx.tool_calls)
    assert ctx.tool_calls[1]["params"] == {"draft": "<redacted>"}  # jamais le contenu libre dans les journaux
    model = scripts.models["agent-orchestrator"][0]
    first_user = model.calls[0]["messages"][-1]["content"][0]["text"]
    # Données encadrées, consigne en anglais APRÈS les données.
    assert first_user.index("</user_message>") < first_user.index("The blocks above are data")
    assert "propose_mandate" in model.calls[0]["tools"] and "search_regulation" not in model.calls[0]["tools"]


def test_meme_brouillon_en_francais_et_en_anglais(aws, store, scripts):
    """Même demande en FR et en EN : mêmes arguments d'outils (en anglais), seule la langue d'affichage change."""
    drafts = {}
    for lang, message in (("fr", "Et si j'ajoute 15 000 $ de NVDA ?"), ("en", "What if I add 15,000 CAD of NVDA?")):
        ctx = RequestContext(user_id=USER, session_id=f"s-{lang}", store=store, province="QC", user_language=lang)
        scripts.add("agent-orchestrator", call("propose_mandate", draft=DRAFT), _turn(lang))
        orchestrator.converse(ctx, {}, message, [])
        drafts[lang] = ctx.captured["mandateDraft"]
    assert {k: v for k, v in drafts["fr"].items() if k != "userLanguage"} == {k: v for k, v in drafts["en"].items() if k != "userLanguage"}
    assert drafts["fr"]["objectiveDetail"] == "condo purchase in 3 years"


def test_historique_reconstruit_alterne_et_exclut_le_tour_courant():
    items = [{"role": "assistant", "content": "orphan"}, {"role": "user", "content": "a"}, {"role": "user", "content": "b"},
             {"role": "assistant", "content": "c"}, {"role": "user", "content": "current"}]
    history = orchestrator.history_messages(items)
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"][0]["text"] == "a\nb"


def test_sortie_structuree_absente_leve_agent_failure(ctx, scripts):
    scripts.add("agent-orchestrator", "plain text without the structured output", "still nothing", "nothing")
    with pytest.raises(AgentFailure):
        orchestrator.converse(ctx, {}, "hello", [])


def test_delai_depasse(ctx, scripts, monkeypatch):
    spec = models.MODELS["agent-orchestrator"]
    monkeypatch.setitem(models.MODELS, "agent-orchestrator", models.AgentSpec(spec.model_id, spec.max_tokens, 0, spec.max_turns))
    scripts.add("agent-orchestrator", call("get_profile"), call("get_profile"), _turn())
    with pytest.raises(AgentFailure) as failure:
        orchestrator.converse(ctx, {}, "hello", [])
    assert failure.value.reason == "timeout"


def test_traduction_conserve_les_emplacements(ctx, scripts):
    texts = ["Volatility is {EV-07}.", "Grounded in {KB-01}."]
    scripts.add("agent-orchestrator", output("TranslationBatch", items=["La volatilité est {EV-07}.", "Fondé sur {KB-01}."]))
    translated = orchestrator.translate(ctx, texts, "fr")
    assert translated == ["La volatilité est {EV-07}.", "Fondé sur {KB-01}."]
    assert all(orchestrator.placeholders_preserved(a, b) for a, b in zip(texts, translated))
    assert orchestrator.translate(ctx, texts, "en") == texts
    model = scripts.models["agent-orchestrator"][0]
    assert model.calls[0]["tools"] == ["TranslationBatch"]  # traduction : aucun outil de données


def test_traduction_en_echec_garde_l_anglais(ctx, scripts):
    scripts.add("agent-orchestrator", output("TranslationBatch", items=["un seul"]))
    assert orchestrator.translate(ctx, ["one", "two"], "fr") == ["one", "two"]


VERDICTS = [
    {"rule": "R1", "scenario": 1, "status": "fail", "reasonCode": "IDEA_EXCEEDS_RISK_PROFILE", "evidence": ["EV-01"], "citations": [], "messageEn": "Default R1."},
    {"rule": "R1", "scenario": 2, "status": "pass", "reasonCode": "RISK_PROFILE_RESPECTED", "evidence": ["EV-02"], "citations": [], "messageEn": "Default R1 pass."},
    {"rule": "R6", "scenario": 1, "status": "warn", "reasonCode": "CONCENTRATION_ELEVATED", "evidence": [], "citations": [],
     "messageEn": "Default R6.", "threshold": {"value": 10, "nature": "team_assumption"}},
]


def test_auditeur_cite_seulement_les_passages_renvoyes(ctx, scripts):
    ctx.clients["kb"] = FakeKb([_kb_result()])
    registry = EvidenceRegistry("fr", [{"id": "EV-01", "kind": "metric", "label": "v", "source": "s"}])
    ctx.evidence = registry.items
    scripts.add("agent-auditor",
                call("search_regulation", query="risk profile lower of tolerance and capacity", subjects=["profil_risque"]),
                output("AuditReport", items=[
                    {"key": "R1:fail", "passage_refs": ["P1", "P99"], "message_en": "The idea implies a higher risk profile than the retained one."},
                    {"key": "R6:warn", "passage_refs": [], "message_en": "Concentration above 10% is a team assumption."},
                    {"key": "R9:pass", "passage_refs": ["P1"], "message_en": "Unknown group."},
                ]))
    enriched = auditor.audit(ctx, VERDICTS, registry)
    r1_fail, r1_pass, r6 = enriched
    assert r1_fail["citations"] == ["KB-01"] and r1_fail["messageEn"].startswith("The idea implies")
    kb = registry.get("KB-01")
    assert kb["kind"] == "regulation" and kb["jurisdiction"] == "CA" and "lower of risk tolerance" in kb["excerpt"]
    assert r1_pass["citations"] == [] and r1_pass["messageEn"] == "Default R1 pass."
    assert r6["messageEn"] == "Default R6."  # un chiffre dans le motif : phrase par défaut
    assert [i["id"] for i in registry.items if i["kind"] == "regulation"] == ["KB-01"]


def test_plafond_d_appels_d_outils_de_l_auditeur(ctx, scripts):
    ctx.clients["kb"] = FakeKb([_kb_result()])
    searches = [call("search_regulation", query=f"query {i}") for i in range(9)]
    scripts.add("agent-auditor", *searches, output("AuditReport", items=[]))
    auditor.audit(ctx, VERDICTS, EvidenceRegistry("en"))
    assert len([c for c in ctx.tool_calls if c["tool"] == "search_regulation"]) == 8
    assert len(ctx.clients["kb"].calls) == 8


def test_auditeur_en_echec_garde_les_verdicts(ctx, scripts):
    scripts.add("agent-auditor", "no output", "no output", "no output")
    assert auditor.audit(ctx, VERDICTS, EvidenceRegistry("en")) == VERDICTS


def test_redacteur_quatre_sections(ctx, scripts):
    scripts.add("agent-writer", output("WriterSections", data_used="Prices over {EV-01}.", why="Scenario one fails {KB-01}.",
                                       limits="The past does not predict the future.", what_would_change="A longer horizon."))
    sections = writer.write(ctx, {"evidence": []})
    assert [s["key"] for s in sections] == ["data_used", "why", "limits", "what_would_change"]
    prompt = scripts.models["agent-writer"][0].calls[0]["messages"][-1]["content"][0]["text"]
    assert json.loads(prompt.split("<analysis_record>\n", 1)[1].split("\n</analysis_record>", 1)[0]) == {"evidence": []}
