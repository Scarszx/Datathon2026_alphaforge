"""Traduction de la restitution du run par Amazon Translate (faux client) : aucun appel réseau ni modèle réel.

Couvre le HTML protégé, la table fixe, la traduction section par section sans attente, les contrôles en code, la
correction LLM des seuls textes signalés, le repli sur l'anglais et les spans Langfuse.
"""

from __future__ import annotations

import contextvars
import json
import threading
import time
from concurrent.futures import Future

import pytest
from botocore.exceptions import ClientError
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from strands.telemetry import StrandsTelemetry

from backend.agents import app, telemetry
from backend.agents.rules import fr as fixed_fr
from backend.agents.tests.conftest import USER, body_of, event
from backend.agents.tests.fake_model import FakeTranslate, add_section_writers, output
from backend.agents.tests.test_routes import RUN, _start_run
from backend.agents.tests.test_writer_parallel import SlowAuditor
from backend.agents.tools.context import RequestContext
from backend.agents.translate import RunTranslator, service
from backend.common.mandates import evaluate_mandate
from backend.common.repositories import analyses

KEYS = ("data_used", "why", "limits", "what_would_change")


# --- protection HTML et appel à Translate --------------------------------------------------------------------------


def test_les_emplacements_et_les_citations_sont_proteges_en_html():
    html_out = service.protect('Volatility {EV-07} for "financial planner" & “Grow”, see {KB-01}.')
    assert html_out.startswith("<p>") and html_out.endswith("</p>")
    assert '<span translate="no">{EV-07}</span>' in html_out and '<span translate="no">{KB-01}</span>' in html_out
    assert '<span translate="no">"financial planner"</span>' in html_out
    assert '<span translate="no">“Grow”</span>' in html_out
    assert "&amp;" in html_out and " & " not in html_out  # entités échappées avant l'envoi


def test_au_retour_les_balises_sont_retirees_et_les_entites_decodees():
    returned = '<p>Rendement de <span translate="no">{EV-07}</span> &amp; l&#39;indice &quot;large&quot; &lt;b&gt;</p>'
    assert service.unprotect(returned) == 'Rendement de {EV-07} & l\'indice "large" <b>'


def test_un_passage_cite_contenant_un_emplacement_est_protege_d_un_bloc():
    assert service.protect('The text says "see {KB-01} here".').count("translate=\"no\"") == 1


def test_la_requete_envoie_du_html_vers_fr_ca_avec_la_terminologie(translate_fake):
    french, used = service.translate(translate_fake, "Volatility is {EV-07}.", "grow-finance-en-fr")
    assert french == "FR Volatility is {EV-07}." and used is True
    params = translate_fake.calls[0]["params"]
    assert params["Document"]["ContentType"] == "text/html"
    assert (params["SourceLanguageCode"], params["TargetLanguageCode"]) == ("en", "fr-CA")
    assert params["TerminologyNames"] == ["grow-finance-en-fr"]
    assert '<span translate="no">{EV-07}</span>' in translate_fake.calls[0]["html"]


def test_sans_terminologie_configuree_la_requete_n_en_cite_aucune(translate_fake):
    service.translate(translate_fake, "Text.", None)
    assert "TerminologyNames" not in translate_fake.calls[0]["params"]


def test_terminologie_absente_du_compte_un_deuxieme_essai_sans_elle(translate_fake):
    translate_fake.terminology_missing = True
    french, used = service.translate(translate_fake, "Text.", "grow-finance-en-fr")
    assert french == "FR Text." and used is False
    assert ["TerminologyNames" in c["params"] for c in translate_fake.calls] == [True, False]


def test_une_autre_erreur_de_translate_n_est_pas_rattrapee(translate_fake):
    translate_fake.errors["Text."] = ClientError({"Error": {"Code": "AccessDeniedException"}}, "TranslateDocument")
    with pytest.raises(ClientError):
        service.translate(translate_fake, "Text.", "grow-finance-en-fr")


# --- contrôles après traduction -------------------------------------------------------------------------------------


@pytest.mark.parametrize("english, french, code", [
    ("Volatility is {EV-07}.", "La volatilité est élevée.", "placeholders"),
    ("Volatility is {EV-07}.", "La volatilité est {EV-07} et {EV-08}.", "placeholders"),
    ("The scenario was not triggered.", "Le scénario est conforme.", "forbidden_phrase"),
    ("The rule was not triggered.", "Nous vous recommandons ce scénario.", "forbidden_phrase"),
    ("The decline stays contained.", "La baisse reste limitée à 12 %.", "added_number"),
    ("Anything.", "  ", "empty"),
])
def test_les_defauts_de_traduction_sont_signales(english, french, code):
    assert service.problem(english, french)[0] == code


def test_une_bonne_traduction_passe_les_controles():
    assert service.problem("Volatility is {EV-07}, about 15,000 $ in {KB-01}.", "La volatilité est {EV-07}, environ 15 000 $ dans {KB-01}.") is None


def test_une_formule_deja_dans_la_source_n_est_pas_un_defaut_de_la_traduction():
    assert service.problem('The title "financial planner" is reserved.', "Le titre « planificateur financier » est réservé.") is None


# --- RunTranslator : table fixe, langues, erreurs ------------------------------------------------------------------


def _ctx(store, language="fr"):
    return RequestContext(user_id=USER, session_id="s1", store=store, province="QC", user_language=language)


def test_la_table_fixe_ne_fait_aucun_appel_et_garde_planificateur_financier(store, translate_fake):
    notice = next(n for n in fixed_fr.NOTICES_FR if n.startswith("In Québec"))
    message = "The scenario holds no crypto assets: the rule does not apply."
    with RunTranslator(_ctx(store), "fr") as translator:
        translator.submit_text(notice, "notice", "notice:0")
        translator.submit_text(message, "message", "R7:pass")
        translator.finalize()
    assert translator.text(notice).text == fixed_fr.NOTICES_FR[notice] and "planificateur financier" in translator.text(notice).text
    assert translator.text(message).text == fixed_fr.MESSAGES_FR[message]
    assert translate_fake.calls == []


def test_un_motif_reformule_passe_par_translate(store, translate_fake):
    with RunTranslator(_ctx(store), "fr") as translator:
        translator.submit_text("The idea implies a higher risk profile.", "message", "R1:fail")
        translator.finalize()
    item = translator.text("The idea implies a higher risk profile.")
    assert item.text == "FR The idea implies a higher risk profile." and item.status == "ok"
    assert [c["english"] for c in translate_fake.calls] == ["The idea implies a higher risk profile."]


def test_anglais_aucun_appel_translate(store, translate_fake):
    with RunTranslator(_ctx(store, "en"), "en") as translator:
        translator.submit_text("Some reason.", "message", "R1:fail")
        done = Future()
        done.set_result("A section.")
        translator.follow("data_used", done)
        translator.finalize()
    assert translator.text("Some reason.").text == "Some reason." and translator.section("data_used", "A section.").text == "A section."
    assert translate_fake.calls == []


def test_autre_langue_l_anglais_est_affiche_et_signale(store, translate_fake, capsys):
    with RunTranslator(_ctx(store, "de"), "de") as translator:
        translator.submit_text("Some reason.", "message", "R1:fail")
        translator.finalize()
    assert translator.text("Some reason.").text == "Some reason." and translate_fake.calls == []
    assert '"event": "translate.unsupported_language"' in capsys.readouterr().out


def test_une_erreur_de_translate_donne_l_anglais_et_un_log_sans_texte(store, translate_fake, capsys):
    translate_fake.errors["Secret reason."] = ClientError({"Error": {"Code": "AccessDeniedException"}}, "TranslateDocument")
    with RunTranslator(_ctx(store), "fr") as translator:
        translator.submit_text("Secret reason.", "message", "R1:fail")
        translator.finalize()
    item = translator.text("Secret reason.")
    assert (item.text, item.status, item.reason) == ("Secret reason.", "fallback", "error:AccessDeniedException")
    out = capsys.readouterr().out
    assert '"event": "translate.error"' in out and "AccessDeniedException" in out and "Secret reason" not in out


# --- chaque section part sans attendre les autres -------------------------------------------------------------------


def test_une_section_est_traduite_des_qu_elle_est_ecrite_sans_attendre_les_autres(store, translate_fake):
    fast, slow = Future(), Future()
    with RunTranslator(_ctx(store), "fr") as translator:
        translator.follow("data_used", fast)
        translator.follow("why", slow)
        fast.set_result("Fast section.")
        deadline = time.perf_counter() + 5
        while not any("end" in c for c in translate_fake.calls) and time.perf_counter() < deadline:
            time.sleep(0.01)
        # La section lente n'est pas écrite : la rapide est déjà traduite.
        assert [c["english"] for c in translate_fake.calls] == ["Fast section."] and not slow.done()
        slow.set_result("Slow section.")
        translator.finalize()
    assert translator.section("data_used", "Fast section.").text == "FR Fast section."
    assert translator.section("why", "Slow section.").text == "FR Slow section."


def test_le_contexte_opentelemetry_est_copie_dans_les_threads(store, translate_fake):
    marker = contextvars.ContextVar("marker", default="absent")
    seen: list[str] = []
    original = translate_fake.translate_document

    def spy(**params):
        seen.append(marker.get())
        return original(**params)

    translate_fake.translate_document = spy
    marker.set("ctx-du-run")
    source = Future()
    with RunTranslator(_ctx(store), "fr") as translator:
        translator.follow("data_used", source)
        translator.submit_text("Reformulated reason.", "message", "R1:fail")
        # La future se termine dans un autre thread, dont le contexte n'a pas la valeur.
        threading.Thread(target=lambda: source.set_result("A section.")).start()
        translator.finalize()
    assert seen == ["ctx-du-run", "ctx-du-run"]


# --- correction LLM des seuls textes signalés ---------------------------------------------------------------------


def _flag_two(translate_fake):
    translate_fake.raw = {
        "Prices over {EV-01} were used.": "<p>Les prix ont été utilisés.</p>",  # emplacement perdu
        "The rule was triggered.": "<p>La règle est conforme.</p>",  # formule de conformité
    }


def test_les_textes_signales_vont_en_un_seul_appel_llm_avec_application_des_corrections(store, translate_fake, scripts):
    _flag_two(translate_fake)
    scripts.add("agent-orchestrator", output("TranslationFixes", fixes=[
        {"item": 0, "find": "Les prix", "replace": "Les prix sur {EV-01}"},
        {"item": 1, "find": "est conforme", "replace": "a été déclenchée"},
    ]))
    with RunTranslator(_ctx(store), "fr") as translator:
        done = Future()
        done.set_result("Prices over {EV-01} were used.")
        translator.follow("data_used", done)
        translator.submit_text("The rule was triggered.", "message", "R1:warn")
        translator.finalize()
    fixed = translator.section("data_used", "Prices over {EV-01} were used.")
    assert (fixed.text, fixed.status) == ("Les prix sur {EV-01} ont été utilisés.", "fixed")
    assert translator.text("The rule was triggered.").text == "La règle a été déclenchée." and translator.text("The rule was triggered.").status == "fixed"
    assert len(scripts.models["agent-orchestrator"]) == 1  # un seul agent, donc un seul appel pour les deux textes
    model = scripts.models["agent-orchestrator"][0]
    assert model.calls[0]["tools"] == ["TranslationFixes"] and len(model.calls) == 1
    sent = json.dumps(model.calls[0]["messages"], ensure_ascii=False)
    assert "Prices over {EV-01} were used." in sent and "placeholders" in sent.lower() and "La règle est conforme." in sent


def test_une_correction_qui_ne_regle_rien_donne_l_anglais(store, translate_fake, scripts):
    _flag_two(translate_fake)
    scripts.add("agent-orchestrator", output("TranslationFixes", fixes=[{"item": 0, "find": "inexistant", "replace": "x"}]))
    with RunTranslator(_ctx(store), "fr") as translator:
        done = Future()
        done.set_result("Prices over {EV-01} were used.")
        translator.follow("data_used", done)
        translator.finalize()
    item = translator.section("data_used", "Prices over {EV-01} were used.")
    assert (item.text, item.status, item.reason) == ("Prices over {EV-01} were used.", "fallback", "placeholders")


def test_une_correction_qui_introduit_un_defaut_est_rejetee_par_le_nouveau_controle(store, translate_fake, scripts):
    _flag_two(translate_fake)
    scripts.add("agent-orchestrator", output("TranslationFixes", fixes=[
        {"item": 0, "find": "Les prix ont", "replace": "Les prix sur {EV-01} {EV-99} ont"}]))
    with RunTranslator(_ctx(store), "fr") as translator:
        done = Future()
        done.set_result("Prices over {EV-01} were used.")
        translator.follow("data_used", done)
        translator.finalize()
    assert translator.section("data_used", "Prices over {EV-01} were used.").status == "fallback"


def test_un_echec_de_la_correction_donne_l_anglais_sans_echec_du_run(store, translate_fake, scripts, capsys):
    _flag_two(translate_fake)
    scripts.add("agent-orchestrator", "no output", "no output", "no output")
    with RunTranslator(_ctx(store), "fr") as translator:
        translator.submit_text("The rule was triggered.", "message", "R1:warn")
        translator.finalize()
    item = translator.text("The rule was triggered.")
    assert (item.text, item.status) == ("The rule was triggered.", "fallback")
    assert '"event": "translate.fix_failed"' in capsys.readouterr().out


def test_sans_texte_signale_le_llm_n_est_pas_appele(store, translate_fake, scripts):
    with RunTranslator(_ctx(store), "fr") as translator:
        translator.submit_text("A reformulated reason.", "message", "R1:fail")
        translator.finalize()
    assert "agent-orchestrator" not in scripts.models


# --- dans la chaîne d'un run ---------------------------------------------------------------------------------------


def _run_in(robert_session, store, scripts, monkeypatch, *, language="fr", auditor=None, texts=None, **writer_options):
    from backend.agents import pipeline

    monkeypatch.setattr(pipeline.auditor, "audit", auditor or SlowAuditor(0.05))
    version = 1
    if language != "fr":
        mandate = {**analyses.get_mandate(robert_session, USER, 1)["mandate"], "userLanguage": language}
        analyses.put_mandate(robert_session, USER, {"mandate": mandate, **evaluate_mandate(mandate), "changedFields": [],
                                                    "confirmedAt": "2026-11-15T14:02:00Z"})
        version = 2
    response, sent = _start_run(store, robert_session, version)
    log = add_section_writers(scripts, texts, **writer_options)
    app.handle_internal(sent[0], store=store)
    run = body_of(app.handle_request(event(RUN, path={"sessionId": robert_session, "runId": body_of(response)["runId"]}), store=store))
    return run, log


def test_run_en_francais_phrases_fixes_en_table_et_sections_par_translate(robert_session, store, scripts, monkeypatch, translate_fake):
    run, _ = _run_in(robert_session, store, scripts, monkeypatch)
    assert run["status"] == "done"
    sent_to_translate = {c["english"] for c in translate_fake.calls}
    assert sent_to_translate == {f"Text of {k}." for k in KEYS}  # ni motifs par défaut, ni mentions
    assert all(c["params"]["TerminologyNames"] == ["grow-finance-en-fr"] for c in translate_fake.calls)
    assert [s["text"] for s in run["narrative"]["sections"]] == [f"FR Text of {k}." for k in KEYS]
    assert run["narrative"]["language"] == "fr" and run["verifier"]["placeholdersMatch"] is True
    assert run["jurisdictionNotices"] == [fixed_fr.NOTICES_FR[n] for n in
                                           ("In Québec, securities activities are overseen by the Autorité des marchés financiers (AMF). The title \"financial planner\" is reserved by law; this tool is not a financial planner or a registered adviser. For personalized advice, consult a registered professional.",
                                            "Educational simulation only, not financial advice. No order is placed.")]
    assert "planificateur financier" in run["jurisdictionNotices"][0]
    for verdict in run["verdicts"]:
        assert verdict["message"] == fixed_fr.fixed_message(verdict["messageEn"]) and verdict["message"] != verdict["messageEn"]


def test_run_en_anglais_aucun_appel_translate(robert_session, store, scripts, monkeypatch, translate_fake):
    run, _ = _run_in(robert_session, store, scripts, monkeypatch, language="en")
    assert run["status"] == "done" and translate_fake.calls == []
    assert [s["text"] for s in run["narrative"]["sections"]] == [f"Text of {k}." for k in KEYS]
    assert all(v["message"] == v["messageEn"] for v in run["verdicts"])
    assert run["jurisdictionNotices"][0].startswith("In Québec")


def test_run_dans_une_autre_langue_affiche_l_anglais(robert_session, store, scripts, monkeypatch, translate_fake):
    run, _ = _run_in(robert_session, store, scripts, monkeypatch, language="de")
    assert run["status"] == "done" and translate_fake.calls == []
    assert [s["text"] for s in run["narrative"]["sections"]] == [f"Text of {k}." for k in KEYS]
    assert run["narrative"]["language"] == "de" and run["verifier"]["placeholdersMatch"] is True


def test_un_motif_reformule_par_l_auditeur_passe_par_translate(robert_session, store, scripts, monkeypatch, translate_fake):
    base = SlowAuditor(0.05)

    def auditor(ctx, verdicts, registry):
        return [{**v, "messageEn": "The idea sits above the retained profile."} if v["rule"] == "R1" and v["status"] == "fail" else v
                for v in base(ctx, verdicts, registry)]

    run, _ = _run_in(robert_session, store, scripts, monkeypatch, auditor=auditor)
    r1 = next(v for v in run["verdicts"] if v["rule"] == "R1" and v["scenario"] == 1)
    assert r1["message"] == "FR The idea sits above the retained profile."
    assert "The idea sits above the retained profile." in {c["english"] for c in translate_fake.calls}


def test_chaque_section_est_traduite_sans_attendre_la_plus_lente(robert_session, store, scripts, monkeypatch, translate_fake):
    run, log = _run_in(robert_session, store, scripts, monkeypatch, delay={"why": 0.8})
    assert run["status"] == "done"
    slow_end = log["calls"]["why"]["end"]
    by_text = {c["english"]: c for c in translate_fake.calls}
    for key in ("data_used", "limits", "what_would_change"):
        assert by_text[f"Text of {key}."]["end"] < slow_end  # déjà traduite pendant que « why » s'écrit encore
    assert by_text["Text of why."]["start"] >= slow_end


def test_une_erreur_de_translate_sur_une_section_n_echoue_pas_le_run(robert_session, store, scripts, monkeypatch, translate_fake, capsys):
    translate_fake.errors["Text of limits."] = ClientError({"Error": {"Code": "ThrottlingException"}}, "TranslateDocument")
    run, _ = _run_in(robert_session, store, scripts, monkeypatch)
    assert run["status"] == "done"
    texts = {s["key"]: s["text"] for s in run["narrative"]["sections"]}
    assert texts["limits"] == "Text of limits." and texts["data_used"] == "FR Text of data_used."
    assert run["verifier"]["placeholdersMatch"] is False  # une section affichée en anglais
    assert '"event": "translate.error"' in capsys.readouterr().out


def test_aucune_permission_translate_le_run_s_affiche_en_anglais(robert_session, store, scripts, monkeypatch, translate_fake):
    for key in KEYS:
        translate_fake.errors[f"Text of {key}."] = ClientError({"Error": {"Code": "AccessDeniedException"}}, "TranslateDocument")
    run, _ = _run_in(robert_session, store, scripts, monkeypatch)
    assert run["status"] == "done" and [s["text"] for s in run["narrative"]["sections"]] == [f"Text of {k}." for k in KEYS]


def test_emplacement_perdu_corrige_par_le_llm_dans_le_run(robert_session, store, scripts, monkeypatch, translate_fake):
    translate_fake.raw = {"Prices over {EV-01} were used.": "<p>Les prix ont été utilisés.</p>"}
    scripts.add("agent-orchestrator", output("TranslationFixes", fixes=[{"item": 0, "find": "Les prix", "replace": "Les prix sur {EV-01}"}]))
    run, _ = _run_in(robert_session, store, scripts, monkeypatch, texts={"data_used": "Prices over {EV-01} were used."})
    section = next(s for s in run["narrative"]["sections"] if s["key"] == "data_used")
    assert section["text"] == "Les prix sur {EV-01} ont été utilisés." and run["verifier"]["placeholdersMatch"] is True


def test_emplacement_perdu_non_corrige_la_section_reste_en_anglais(robert_session, store, scripts, monkeypatch, translate_fake):
    translate_fake.raw = {"Prices over {EV-01} were used.": "<p>Les prix ont été utilisés.</p>"}
    scripts.add("agent-orchestrator", output("TranslationFixes", fixes=[]))
    run, _ = _run_in(robert_session, store, scripts, monkeypatch, texts={"data_used": "Prices over {EV-01} were used."})
    section = next(s for s in run["narrative"]["sections"] if s["key"] == "data_used")
    assert run["status"] == "done" and section["text"] == "Prices over {EV-01} were used." and run["verifier"]["placeholdersMatch"] is False


# --- Langfuse ------------------------------------------------------------------------------------------------------


def test_un_span_par_appel_translate_et_un_pour_la_correction(robert_session, store, scripts, monkeypatch, translate_fake):
    exporter = InMemorySpanExporter()
    provider = StrandsTelemetry()
    provider.tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    telemetry.reset_for_tests(provider)
    try:
        translate_fake.raw = {"Limits {EV-01}.": "<p>Des limites.</p>", "The past stays contained.": "<p>Le passé reste limité à 25 %.</p>"}
        scripts.add("agent-orchestrator", output("TranslationFixes", fixes=[]))
        _run_in(robert_session, store, scripts, monkeypatch, texts={"limits": "Limits {EV-01}.", "why": "The past stays contained."})
        spans = exporter.get_finished_spans()
        translate_spans = [s for s in spans if s.name == "translate.text"]
        assert len(translate_spans) == 4
        assert {s.attributes["langfuse.observation.type"] for s in translate_spans} == {"tool"}
        keys = {json.loads(s.attributes["langfuse.observation.input"])["key"] for s in translate_spans}
        assert keys == {f"section:{k}" for k in KEYS}
        for span in translate_spans:
            payload = json.loads(span.attributes["langfuse.observation.input"])
            assert set(payload) == {"key", "chars"}  # jamais le texte
            output_payload = json.loads(span.attributes["langfuse.observation.output"])
            assert {"result", "durationMs", "chars", "terminology"} <= set(output_payload)
        results = {json.loads(s.attributes["langfuse.observation.input"])["key"]: json.loads(s.attributes["langfuse.observation.output"])["result"]
                   for s in translate_spans}
        assert results["section:limits"] == "flagged:placeholders" and results["section:why"] == "flagged:added_number"
        fix = [s for s in spans if s.name == "translate.fix"]
        assert len(fix) == 1 and json.loads(fix[0].attributes["langfuse.observation.output"])["flagged"] == 2
        root = next(s for s in spans if s.name == "analysis-complete-run")
        assert {s.context.trace_id for s in translate_spans + fix} == {root.context.trace_id}  # sous l'analyse, pas orphelins
    finally:
        telemetry.reset_for_tests(None)


# --- configuration et glossaire -------------------------------------------------------------------------------------


def test_nom_de_terminologie_par_defaut_vide_ou_surcharge(monkeypatch):
    from backend.common import config

    monkeypatch.delenv("TRANSLATE_TERMINOLOGY", raising=False)
    assert config.translate_terminology() == "grow-finance-en-fr"
    monkeypatch.setenv("TRANSLATE_TERMINOLOGY", "   ")
    assert config.translate_terminology() is None
    monkeypatch.setenv("TRANSLATE_TERMINOLOGY", "autre-nom")
    assert config.translate_terminology() == "autre-nom"


def test_le_glossaire_est_un_csv_valide_pour_translate():
    import csv
    from pathlib import Path

    path = Path(service.__file__).parent / "terminology" / "grow-finance-en-fr.csv"
    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    assert rows[0] == ["en", "fr-CA"]
    assert all(len(r) == 2 and r[0].strip() and r[1].strip() for r in rows)
    sources = [r[0] for r in rows[1:]]
    assert len(sources) == len(set(sources)) <= 256  # une terminologie compte 256 termes au plus
    assert "maximum drawdown" in sources and ("ETF", "FNB") in {tuple(r) for r in rows}
