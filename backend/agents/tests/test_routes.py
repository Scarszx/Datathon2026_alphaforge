"""Routes de srv-agent-runtime et cycle d'un run (partial → done), sans AWS ni modèle."""

from __future__ import annotations

import pytest

from backend.agents import app, guardrails
from backend.agents.tests.conftest import USER, body_of, event
from backend.agents.tests.fake_model import EchoTranslator, call, output
from backend.agents.tests.test_tools import FakeKb, _kb_result
from backend.agents.tools import kb
from backend.common.repositories import analyses, conversations, messages

RUNS = "POST /v1/conversations/{sessionId}/runs"
RUN = "GET /v1/conversations/{sessionId}/runs/{runId}"
MESSAGES = "POST /v1/conversations/{sessionId}/messages"


class FakeGuardrail:
    """ApplyGuardrail simulé : bloque par sujet ou par renseignement personnel (PII / regex)."""

    def __init__(self, blocked_word: str | None = None, pii_word: str | None = None):
        self.blocked_word = blocked_word
        self.pii_word = pii_word
        self.calls = []

    def apply_guardrail(self, **kwargs):
        text = kwargs["content"][0]["text"]["text"]
        self.calls.append((kwargs["source"], text))
        if self.pii_word and self.pii_word in text:
            return {"action": "GUARDRAIL_INTERVENED", "outputs": [{"text": "Sorry, personal banking details are not allowed."}],
                    "assessments": [{"sensitiveInformationPolicy": {"regexes": [{"name": "ca-bank-account", "action": "BLOCKED"}]}}]}
        if self.blocked_word and self.blocked_word in text:
            return {"action": "GUARDRAIL_INTERVENED", "outputs": [{"text": "Sorry, this simulation cannot place orders."}],
                    "assessments": [{"topicPolicy": {"topics": [{"name": "Orders", "action": "BLOCKED"}]}}]}
        return {"action": "NONE", "outputs": [], "assessments": []}


@pytest.fixture
def guard(monkeypatch):
    fake = FakeGuardrail()
    monkeypatch.setenv("GUARDRAIL_ID", "gr-1")
    monkeypatch.setenv("GUARDRAIL_VERSION", "1")
    monkeypatch.setattr(guardrails, "_client", lambda: fake)
    return fake


@pytest.fixture
def kb_fake(monkeypatch):
    fake = FakeKb([_kb_result()])
    monkeypatch.setattr(kb, "_client", lambda: fake)
    return fake


def _start_run(store, session, version=1):
    sent = []
    response = app.handle_request(event(RUNS, path={"sessionId": session}, body={"mandateVersion": version}),
                                  store=store, dispatcher=sent.append)
    return response, sent


def _script_completion(scripts, *, writer_ok=True):
    scripts.add("agent-auditor",
                call("search_regulation", query="risk profile is the lower of risk tolerance and risk capacity", subjects=["profil_risque"]),
                output("AuditReport", items=[{"key": "R1:fail", "passage_refs": ["P1"],
                                              "message_en": "The idea implies a higher risk profile than the retained one."}]))
    if writer_ok:
        scripts.add("agent-writer", output(
            "WriterSections",
            data_used="Daily adjusted prices over {EV-01} were used, converted to CAD.",
            why="The idea fails because its volatility reaches {EV-01}, above the retained profile {KB-01}. It is up 12% too.",
            limits="The past does not predict the future.",
            what_would_change="A longer horizon, such as the 3 years you gave, would change the loss limit."))
    else:
        scripts.add("agent-writer", "no output", "no output", "no output")
    # Traduction (agent-orchestrator) : sections, puis motifs et mentions.
    scripts.add("agent-orchestrator", output("TranslationBatch", items=[
        "Des prix ajustés quotidiens sur {EV-01} ont été utilisés, convertis en CAD.",
        "L'idée échoue car sa volatilité atteint {EV-01}, au-dessus du profil retenu {KB-01}. Elle a aussi gagné 12 %.",
        "Le passé ne prédit pas l'avenir.",
        "Un horizon plus long, comme les 3 ans indiqués, changerait la limite de perte."]))
    for _ in range(4):  # motifs de verdict et mentions : lots de taille variable
        scripts.add("agent-orchestrator", EchoTranslator())


def test_cycle_d_un_run_partial_puis_done(robert_session, store, scripts, kb_fake, guard):
    response, sent = _start_run(store, robert_session)
    assert response["statusCode"] == 201
    run = body_of(response)
    assert run["status"] == "partial" and run["mandateVersion"] == 1 and run["datasetVersion"] == "fixture-synthetic"
    assert [s["index"] for s in run["scenarios"]] == [0, 1, 2]
    assert run["scenarios"][1]["verdict"] == "fail" and run["scenarios"][2]["verdict"] != "fail"
    assert all(v["citations"] == [] for v in run["verdicts"]) and "narrative" not in run
    assert run["jurisdictionNotices"][0].startswith("In Québec")
    assert {s["agentId"] for s in run["explanation"]["steps"]} == {"module-engine", "module-rules"}
    assert sent == [{"internal": "complete_run", "userId": USER, "sessionId": robert_session, "runId": run["runId"]}]

    # Complétion asynchrone : événement interne reçu par le handler de la Lambda.
    _script_completion(scripts)
    app.handle_internal(sent[0], store=store)
    done = body_of(app.handle_request(event(RUN, path={"sessionId": robert_session, "runId": run["runId"]}), store=store))
    assert done["status"] == "done" and done["completedAt"]
    r1 = next(v for v in done["verdicts"] if v["rule"] == "R1" and v["scenario"] == 1)
    assert r1["citations"] == ["KB-01"] and r1["message"].startswith("FR")
    assert any(e["id"] == "KB-01" and e["kind"] == "regulation" for e in done["evidence"])
    narrative = done["narrative"]
    assert narrative["language"] == "fr" and [s["key"] for s in narrative["sections"]] == ["data_used", "why", "limits", "what_would_change"]
    why = narrative["sections"][1]
    assert "12 %" not in why["text"] and why["text"].startswith("L'idée échoue")  # phrase au chiffre écrit à la main masquée
    assert narrative["hiddenSentences"] == [{"section": "why", "reason": "handwritten_number"}]
    assert done["verifier"]["placeholdersMatch"] is True and done["verifier"]["handwrittenNumbers"] == 1
    assert done["verifier"]["placeholdersResolved"] == done["verifier"]["placeholdersTotal"]
    assert done["jurisdictionNotices"][0].startswith("FR")
    assert {"agent-auditor", "agent-writer"} <= {s["agentId"] for s in done["explanation"]["steps"]} | {c["agentId"] for c in done["explanation"]["checks"]}
    assert kb_fake.calls[0]["retrievalConfiguration"]["vectorSearchConfiguration"]["filter"]["andAll"][0]["in"]["value"] == ["CA", "QC"]
    assert ("OUTPUT", guard.calls[-1][1]) == guard.calls[-1]


def test_redacteur_en_echec_le_run_reste_utilisable(robert_session, store, scripts, kb_fake):
    response, sent = _start_run(store, robert_session)
    _script_completion(scripts, writer_ok=False)
    app.handle_internal(sent[0], store=store)
    run = analyses.get_run(robert_session, USER, body_of(response)["runId"])
    assert run["status"] == "error" and "narrative" not in run
    assert run["scenarios"] and any(v["citations"] for v in run["verdicts"])


def test_run_erreurs(robert_session, store):
    assert body_of(_start_run(store, robert_session, 7)[0])["error"]["code"] == "MANDATE_NOT_FOUND"
    bad = app.handle_request(event(RUNS, path={"sessionId": robert_session}, body={"mandateVersion": "1"}), store=store, dispatcher=None)
    assert body_of(bad)["error"]["code"] == "VALIDATION_ERROR"
    other = app.handle_request(event(RUNS, path={"sessionId": robert_session}, body={"mandateVersion": 1},
                                     claims={"sub": "intrus"}), store=store, dispatcher=None)
    assert body_of(other)["error"]["code"] == "CONVERSATION_NOT_FOUND"
    missing = app.handle_request(event(RUN, path={"sessionId": robert_session, "runId": "01NOPE"}), store=store)
    assert missing["statusCode"] == 404 and body_of(missing)["error"]["code"] == "RUN_NOT_FOUND"


def test_mandat_non_confirme(robert_session, store, monkeypatch):
    original = analyses.get_mandate
    monkeypatch.setattr(analyses, "get_mandate", lambda *a: {**original(*a), "confirmedAt": None})
    response = _start_run(store, robert_session)[0]
    assert response["statusCode"] == 409 and body_of(response)["error"]["code"] == "MANDATE_NOT_CONFIRMED"


def test_run_d_un_autre_utilisateur_invisible(robert_session, store):
    run = body_of(_start_run(store, robert_session)[0])
    response = app.handle_request(event(RUN, path={"sessionId": robert_session, "runId": run["runId"]}, claims={"sub": "intrus"}), store=store)
    assert response["statusCode"] == 404


def _send(store, session, content="Et si j'ajoute 15 000 $ de NVDA pour un condo dans 3 ans ?"):
    return app.handle_request(event(MESSAGES, path={"sessionId": session}, body={"content": content}), store=store)


def test_message_de_cadrage(robert_session, store, scripts, guard):
    draft = {"mode": "add_asset", "objective": "project", "horizonYears": 3, "riskTolerance": 3, "riskCapacity": 1,
             "province": "QC", "operations": [{"action": "add", "ticker": "NVDA", "amount": 15000, "currency": "CAD"}]}
    scripts.add("agent-orchestrator", call("propose_mandate", draft=draft),
                output("OrchestratorTurn", user_language="fr", english_request="What if I add 15,000 CAD of NVDA?",
                       reply="Voici le mandat proposé, à confirmer.", quick_replies=["Confirmer", "Modifier"]))
    response = _send(store, robert_session)
    assert response["statusCode"] == 200
    body = body_of(response)
    assistant = body["assistantMessage"]
    assert body["userMessage"]["role"] == "user" and assistant["quickReplies"] == ["Confirmer", "Modifier"]
    assert assistant["mandateDraft"]["userLanguage"] == "fr" and assistant["explanation"]["steps"][0]["tool"] == "propose_mandate"
    assert body["userMessage"]["messageId"] < assistant["messageId"]
    stored = messages.list_messages(robert_session)["items"]
    assert [m["role"] for m in stored] == ["user", "assistant"] and stored[1]["mandateDraft"]["mode"] == "add_asset"
    assert conversations.get_conversation(USER, robert_session)["userLanguage"] == "fr"
    sources = [source for source, _ in guard.calls]
    assert sources == ["INPUT", "INPUT", "OUTPUT"]  # original, traduction anglaise, réponse


def test_message_bloque_n_entre_pas_dans_l_historique(robert_session, store, scripts, guard):
    guard.pii_word = "12345-678-1234567"
    response = _send(store, robert_session, "Mon compte bancaire est 12345-678-1234567")
    assert response["statusCode"] == 422 and body_of(response)["error"]["code"] == "GUARDRAIL_BLOCKED"
    assert messages.list_messages(robert_session)["items"] == []
    assert "agent-orchestrator" not in scripts.models  # PII / regex refusé avant tout appel de modèle


def test_blocage_sujet_non_anglais_retenu_seulement_si_confirme_sur_english_request(robert_session, store, scripts, guard):
    guard.blocked_word = "Et si j'ajoute"
    scripts.add("agent-orchestrator", output("OrchestratorTurn", user_language="fr",
                                             english_request="What if I add 10% XIU to my portfolio?",
                                             reply="Voici la simulation.", quick_replies=[]))
    response = _send(store, robert_session, "Et si j'ajoute 10 % de XIU à mon portefeuille ?")
    assert response["statusCode"] == 200
    assert body_of(response)["assistantMessage"]["content"] == "Voici la simulation."


def test_traduction_bloquee(robert_session, store, scripts, guard):
    guard.blocked_word = "buy it for me"
    scripts.add("agent-orchestrator", output("OrchestratorTurn", user_language="fr", english_request="Please buy it for me",
                                             reply="...", quick_replies=[]))
    response = _send(store, robert_session, "Prends-le pour moi stp")
    assert response["statusCode"] == 422 and body_of(response)["error"]["code"] == "GUARDRAIL_BLOCKED"
    assert messages.list_messages(robert_session)["items"] == []


def test_blocage_sujet_texte_anglais_est_final(robert_session, store, scripts, guard):
    guard.blocked_word = "Buy 100 shares"
    scripts.add("agent-orchestrator", output("OrchestratorTurn", user_language="en",
                                             english_request="Simulate 100 shares of NVDA",
                                             reply="...", quick_replies=[]))
    response = _send(store, robert_session, "Buy 100 shares of NVDA for me")
    assert response["statusCode"] == 422 and body_of(response)["error"]["code"] == "GUARDRAIL_BLOCKED"
    assert messages.list_messages(robert_session)["items"] == []


def test_sortie_controlee_par_guardrail(robert_session, store, scripts, guard):
    guard.blocked_word = "guaranteed 20%"
    scripts.add("agent-orchestrator", output("OrchestratorTurn", user_language="fr",
                                             english_request="What is the past volatility?",
                                             reply="You have a guaranteed 20% return.", quick_replies=[]))
    response = _send(store, robert_session, "Quelle est la volatilité passée ?")
    assert response["statusCode"] == 200
    assert body_of(response)["assistantMessage"]["content"] == "Sorry, this simulation cannot place orders."


def test_question_de_suivi_lit_le_registre(robert_session, store, scripts):
    run = body_of(_start_run(store, robert_session)[0])
    scripts.add("agent-orchestrator", call("read_evidence", evidence_id="EV-05"),
                output("OrchestratorTurn", user_language="fr", english_request="Where does EV-05 come from?",
                       reply="Ce chiffre {EV-05} vient des prix ajustés.", quick_replies=[]))
    assistant = body_of(_send(store, robert_session, "D'où vient EV-05 ?"))["assistantMessage"]
    assert assistant["runId"] == run["runId"] and "{EV-05}" in assistant["content"]


def test_message_delai_depasse(robert_session, store, scripts, monkeypatch):
    from backend.agents import models

    spec = models.MODELS["agent-orchestrator"]
    monkeypatch.setitem(models.MODELS, "agent-orchestrator", models.AgentSpec(spec.model_id, spec.max_tokens, 0, spec.max_turns))
    scripts.add("agent-orchestrator", call("get_profile"), call("get_profile"))
    response = _send(store, robert_session, "Bonjour")
    assert response["statusCode"] == 504 and body_of(response)["error"]["code"] == "AGENT_TIMEOUT"
    assert messages.list_messages(robert_session)["items"] == []


@pytest.mark.parametrize("body,code", [({"content": ""}, "VALIDATION_ERROR"), ({"content": "x" * 2001}, "VALIDATION_ERROR"),
                                       ({"content": "hi", "role": "assistant"}, "VALIDATION_ERROR")])
def test_message_validation(robert_session, store, body, code):
    response = app.handle_request(event(MESSAGES, path={"sessionId": robert_session}, body=body), store=store)
    assert body_of(response)["error"]["code"] == code


SUMMARY = "GET /v1/portfolios/{portfolioId}/summary"


def test_resume_du_portefeuille(robert_session, store):
    body = body_of(app.handle_request(event(SUMMARY, path={"portfolioId": "main"}, query={"range": "5y"}), store=store))
    assert body["baseCurrency"] == "CAD" and body["totals"]["value"] == pytest.approx(92000, rel=1e-4)
    assert sum(h["weight"] for h in body["holdings"]) == pytest.approx(100, abs=0.05)
    assert len(body["performance"]["points"]) <= 260 and body["risk"]["volatility"] > 0
    assert {a["label"] for a in body["allocation"]["byAssetClass"]} == {"etf_equity", "equity", "etf_bond"}
    assert body["explanation"]["sources"][0]["dataset"].endswith("@fixture-synthetic")


def test_resume_erreurs(robert_session, store):
    assert body_of(app.handle_request(event(SUMMARY, path={"portfolioId": "autre"}), store=store))["error"]["code"] == "PORTFOLIO_NOT_FOUND"
    assert body_of(app.handle_request(event(SUMMARY, path={"portfolioId": "main"}, query={"range": "3y"}), store=store))["error"]["code"] == "VALIDATION_ERROR"


def test_recherche_d_actifs(aws, store):
    body = body_of(app.handle_request(event("GET /v1/market/search", query={"q": "ry"}), store=store))
    assert body["items"][0]["ticker"] == "RY.TO" and body["items"][0]["market"] == "TSX"
    assert body_of(app.handle_request(event("GET /v1/market/search", query={}), store=store))["error"]["code"] == "VALIDATION_ERROR"


def test_handler_route_inconnue_et_identite(aws, store):
    assert body_of(app.handle_request(event("GET /v1/nope"), store=store))["error"]["code"] == "VALIDATION_ERROR"
    assert body_of(app.handle_request(event("GET /v1/market/search", query={"q": "x"}, claims=None), store=store))["error"]["code"] == "UNAUTHORIZED"
    assert app.handle_internal({"internal": "other"}, store=store) == {"ok": False}


def test_auto_invocation_en_echec(robert_session, store):
    def broken(payload):
        raise RuntimeError("AccessDenied")

    response = app.handle_request(event(RUNS, path={"sessionId": robert_session}, body={"mandateVersion": 1}),
                                  store=store, dispatcher=broken)
    assert response["statusCode"] == 201 and body_of(response)["scenarios"]
    assert analyses.get_run(robert_session, USER, body_of(response)["runId"])["status"] == "error"
