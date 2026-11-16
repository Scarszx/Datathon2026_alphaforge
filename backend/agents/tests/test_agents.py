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
from backend.agents.tests.fake_model import add_section_writers, call, output
from backend.agents.toolbox import MAX_TOOL_CALLS
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


def test_max_tokens_leve_agent_failure(ctx, scripts):
    from strands.types.exceptions import MaxTokensReachedException

    scripts.add("agent-orchestrator", MaxTokensReachedException("max tokens reached"))
    with pytest.raises(AgentFailure) as failure:
        orchestrator.converse(ctx, {}, "hello", [])
    assert failure.value.reason == "max_tokens"


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


def test_auditeur_cite_seulement_les_passages_des_candidats(ctx, scripts):
    ctx.clients["kb"] = FakeKb([_kb_result()])
    registry = EvidenceRegistry("fr", [{"id": "EV-01", "kind": "metric", "label": "v", "source": "s"}])
    ctx.evidence = registry.items
    scripts.add("agent-auditor",
                output("AuditReport", items=[
                    {"key": "R1:fail", "passage_refs": ["P1", "P99"], "message_en": "The idea implies a higher risk profile than the retained one."},
                    {"key": "R6:warn", "passage_refs": [], "message_en": "Concentration above 10% is a team assumption."},
                    {"key": "R9:pass", "passage_refs": ["P1"], "message_en": "Unknown group."},
                ]))
    enriched = auditor.audit(ctx, VERDICTS, registry)
    r1_fail, r1_pass, r6 = enriched
    assert r1_fail["citations"] == ["KB-01"] and r1_fail["messageEn"].startswith("The idea implies")
    kb_item = registry.get("KB-01")
    assert kb_item["kind"] == "regulation" and kb_item["jurisdiction"] == "CA" and "lower of risk tolerance" in kb_item["excerpt"]
    assert r1_pass["citations"] == [] and r1_pass["messageEn"] == "Default R1 pass."
    assert r6["messageEn"] == "Default R6."  # un chiffre dans le motif : phrase par défaut
    assert [i["id"] for i in registry.items if i["kind"] == "regulation"] == ["KB-01"]
    assert scripts.models["agent-auditor"][0].calls[0]["tools"] == ["AuditReport"]  # le modèle ne cherche plus


def test_le_code_lance_une_recherche_par_sujet_de_la_regle(ctx, scripts):
    """R1 : profil_risque et convenance, une recherche chacun, phrase = titre de la règle + motif calculé."""
    from backend.agents.rules.rules import RULE_SUBJECTS, RULE_TOPICS

    ctx.clients["kb"] = FakeKb([_kb_result()])
    scripts.add("agent-auditor", output("AuditReport", items=[]))
    auditor.audit(ctx, VERDICTS, EvidenceRegistry("en"))
    searches = [c for c in ctx.tool_calls if c["tool"] == "search_regulation"]
    by_subject = {tuple(c["params"]["subjects"]): c["params"]["query"] for c in searches}
    # R1 (fail + pass) et R6 (warn) : 2 + 1 recherches, un sujet chacune, exactement ceux de la règle.
    assert sorted(by_subject) == [("convenance",), ("profil_risque",)]
    assert len(searches) == len(RULE_SUBJECTS["R1"]) + len(RULE_SUBJECTS["R6"]) == 3
    r1_query = next(c["params"]["query"] for c in searches if c["params"]["subjects"] == ["profil_risque"])
    assert r1_query.startswith(RULE_TOPICS["R1"]) and "Default R1." in r1_query  # motif du verdict le plus grave
    r6_query = next(c["params"]["query"] for c in searches if c["params"]["query"].startswith(RULE_TOPICS["R6"]))
    assert "Default R6." in r6_query
    for kb_call in ctx.clients["kb"].calls:
        flt = kb_call["retrievalConfiguration"]["vectorSearchConfiguration"]["filter"]
        assert flt["andAll"][1]["listContains"]["key"] == "sujets"  # un seul sujet par recherche, jamais orAll


def test_r5_une_recherche_par_sujet_et_cinq_extraits_differents(ctx, scripts):
    verdicts = [{"rule": "R5", "scenario": 1, "status": "fail", "reasonCode": "SECURITY_NAMED", "evidence": [],
                 "citations": [], "messageEn": "The scenario 2 texts name a specific security."}]
    results = [_kb_result(f"Passage number {i} about order execution only services.") for i in range(3)]
    ctx.clients["kb"] = FakeKb(results + results)  # chaque sujet renvoie les mêmes passages
    scripts.add("agent-auditor", output("AuditReport", items=[{"key": "R5:fail", "passage_refs": ["P1"], "message_en": "The rule is inspired by the ban on naming a security."}]))
    enriched = auditor.audit(ctx, verdicts, EvidenceRegistry("en"))
    searches = [c for c in ctx.tool_calls if c["tool"] == "search_regulation"]
    assert sorted(c["params"]["subjects"][0] for c in searches) == ["aide_decision", "oeo", "recommandation"]
    prompt = scripts.models["agent-auditor"][0].calls[0]["messages"][-1]["content"][0]["text"]
    group = json.loads(prompt.split("<verdict_groups>\n", 1)[1].split("\n</verdict_groups>", 1)[0])[0]
    excerpts = [p["excerpt"] for p in group["passages"]]
    assert len(excerpts) == len(set(excerpts)) == 3  # 3 sujets × les mêmes 3 passages : jamais deux fois le même extrait
    assert len(enriched[0]["citations"]) == 1 and enriched[0]["messageEn"].startswith("The rule is inspired")


def test_un_motif_d_approbation_du_modele_retombe_sur_la_phrase_par_defaut(ctx, scripts):
    ctx.clients["kb"] = FakeKb([_kb_result()])
    scripts.add("agent-auditor", output("AuditReport", items=[{"key": "R1:fail", "passage_refs": ["P1"], "message_en": "The idea is not suitable for the investor."}]))
    enriched = auditor.audit(ctx, [VERDICTS[0]], EvidenceRegistry("en"))
    assert enriched[0]["messageEn"] == "Default R1." and len(enriched[0]["citations"]) == 1


def test_aucune_citation_ni_recherche_pour_pass_et_not_verified(ctx, scripts):
    """Lot A : un extrait du régulateur à côté d'une règle non déclenchée se lirait comme un accord."""
    from backend.agents.rules.rules import RULE_SUBJECTS

    ctx.clients["kb"] = FakeKb([_kb_result()])
    verdicts = [
        {"rule": r, "scenario": 1, "status": status, "reasonCode": "X", "evidence": [], "citations": [], "messageEn": f"Default {r}."}
        for r in RULE_SUBJECTS for status in ("pass", "not_verified")
    ]
    registry = EvidenceRegistry("en")
    assert auditor.audit(ctx, verdicts, registry) == verdicts
    assert not [c for c in ctx.tool_calls if c["tool"] == "search_regulation"]
    assert "agent-auditor" not in scripts.models and ctx.clients["kb"].calls == []
    assert not [i for i in registry.items if i["kind"] == "regulation"]


def test_un_passage_sans_juridiction_ou_hors_mandat_est_jete(ctx, scripts):
    ctx.clients["kb"] = FakeKb([_kb_result(juris="ON"), {**_kb_result(), "metadata": {"date_version": "2025"}}])
    scripts.add("agent-auditor", output("AuditReport", items=[]))
    verdicts = [VERDICTS[0]]
    # Province QC : le passage ON et le passage sans juridiction sont écartés ; rien ne reste, aucun modèle appelé.
    assert auditor.audit(ctx, verdicts, EvidenceRegistry("en")) == verdicts
    assert "agent-auditor" not in scripts.models
    assert ctx.passages == {}


def test_auditeur_sans_passage_candidat_ne_cite_rien(ctx, scripts):
    ctx.clients["kb"] = FakeKb([_kb_result()])
    scripts.add("agent-auditor", output("AuditReport", items=[{"key": "R1:fail", "passage_refs": [], "message_en": "No passage grounds this."}]))
    registry = EvidenceRegistry("en")
    enriched = auditor.audit(ctx, [VERDICTS[0]], registry)
    assert enriched[0]["citations"] == [] and not [i for i in registry.items if i["kind"] == "regulation"]


def test_plafond_de_recherches_de_l_auditeur(ctx, scripts):
    ctx.clients["kb"] = FakeKb([_kb_result()])
    every_rule = [
        {"rule": r, "scenario": 1, "status": "fail", "reasonCode": "X", "evidence": [], "citations": [], "messageEn": f"Default {r}."}
        for r in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9")
    ]
    scripts.add("agent-auditor", output("AuditReport", items=[]))
    auditor.audit(ctx, every_rule, EvidenceRegistry("en"))
    assert len([c for c in ctx.tool_calls if c["tool"] == "search_regulation"]) == 15 <= 16


def test_auditeur_en_echec_garde_les_verdicts(ctx, scripts):
    ctx.clients["kb"] = FakeKb([_kb_result()])
    scripts.add("agent-auditor", "no output", "no output", "no output")
    assert auditor.audit(ctx, VERDICTS, EvidenceRegistry("en")) == VERDICTS


def test_redacteur_quatre_sections(ctx, scripts):
    texts = {"data_used": "Prices over {EV-01}.", "why": "Scenario one fails {KB-01}.",
             "limits": "The past does not predict the future.", "what_would_change": "A longer horizon."}
    log = add_section_writers(scripts, texts)
    sections = writer.write(ctx, {"evidence": []})
    assert sections == [{"key": k, "textEn": texts[k]} for k in ("data_used", "why", "limits", "what_would_change")]
    assert set(log["calls"]) == set(texts)
    for key, call_ in log["calls"].items():
        assert call_["record"] == {"evidence": []}
        # Aucune perte : tout le prompt d'origine, plus la section demandée et ce que couvrent les trois autres.
        assert writer.prompts.SYSTEM_PROMPT.rstrip() in call_["system"]
        assert f"Section to write: {key}," in call_["system"]
        assert sum(f"{other}: " in call_["system"] for other in texts if other != key) == 3
    assert sorted(c["params"]["section"] for c in ctx.tool_calls if c["tool"] == "agent_invocation") == sorted(texts)


def test_un_appel_par_section_nomme_dans_la_trace(ctx, scripts):
    from backend.agents.llm.base import build_agent

    agent = build_agent("agent-writer", "p", ctx, label="why", tool_call_limit=1)
    assert agent.name == "agent-writer" and agent.trace_attributes["agent.section"] == "why"
    assert build_agent("agent-writer", "p", ctx).trace_attributes.get("agent.section") is None


def test_redacteur_une_section_en_echec_fait_echouer_l_ensemble(ctx, scripts):
    add_section_writers(scripts, fail={"limits"})
    with pytest.raises(AgentFailure):
        writer.write(ctx, {"evidence": []})
    assert len([c for c in ctx.tool_calls if c["tool"] == "agent_invocation"]) == 4  # les trois autres ont fini et sont journalisées


def test_plafond_total_de_quatre_lectures_du_registre(ctx, scripts):
    ctx.evidence = [{"id": "EV-01", "kind": "metric", "label": "x"}]
    add_section_writers(scripts, evidence_reads=3)  # chaque section tente 3 lectures en un tour
    writer.write(ctx, {"evidence": []})
    reads = [c for c in ctx.tool_calls if c["tool"] == "read_evidence"]
    assert len(reads) == 4 <= MAX_TOOL_CALLS["agent-writer"]


def test_auditeur_ne_cherche_pas_les_verdicts_sans_objet(ctx, scripts):
    """R7 sans cryptoactif, R8 sans préférence ESG et R10 (aucun sujet) n'ouvrent aucune recherche ni appel de modèle."""
    verdicts = [
        {"rule": "R7", "scenario": 0, "status": "pass", "reasonCode": "NO_CRYPTO_EXPOSURE", "evidence": [], "citations": [], "messageEn": "No crypto."},
        {"rule": "R8", "scenario": 0, "status": "pass", "reasonCode": "ESG_NOT_REQUESTED", "evidence": [], "citations": [], "messageEn": "No ESG."},
        {"rule": "R10", "status": "pass", "reasonCode": "MACRO_PUBLICATION_RESPECTED", "evidence": [], "citations": [], "messageEn": "Macro ok."},
    ]
    assert auditor.audit(ctx, verdicts, EvidenceRegistry("en")) == verdicts  # aucun script d'agent consommé
