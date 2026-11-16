"""Rédacteur en 4 appels parallèles : data_used et limits partent avec l'auditeur, why et what_would_change après lui."""

from __future__ import annotations

import time

from backend.agents import app, pipeline
from backend.agents.tests.conftest import body_of, event
from backend.agents.tests.fake_model import add_section_writers
from backend.agents.tests.test_routes import RUN, _start_run

KEYS = ("data_used", "why", "limits", "what_would_change")
AUDIT_SECONDS = 0.6
WRITE_SECONDS = 0.1


class SlowAuditor:
    """Faux auditeur lent : inscrit KB-01 au registre, ajoute la citation à R1 et note ses instants de début et de fin."""

    def __init__(self, seconds: float = AUDIT_SECONDS):
        self.seconds, self.start, self.end = seconds, None, None

    def __call__(self, ctx, verdicts, registry):
        self.start = time.perf_counter()
        time.sleep(self.seconds)
        kb_id = registry.add_regulation(document="NI 31-103", section="s", excerpt="Know your client.", jurisdiction="CA",
                                        url=None, as_of=None, document_type=None, regulator=None, status=None,
                                        section_title=None, language="en", source="test")
        ctx.tool_calls.append({"agentId": "agent-auditor", "tool": "search_regulation", "params": {}, "status": "ok", "durationMs": 1})
        self.end = time.perf_counter()
        return [{**v, "citations": [kb_id] if v["rule"] == "R1" and v["status"] == "fail" else v["citations"]} for v in verdicts]


def _complete(robert_session, store, scripts, monkeypatch, *, auditor=None, **writer_options):
    auditor = auditor or SlowAuditor()
    monkeypatch.setattr(pipeline.auditor, "audit", auditor)
    response, sent = _start_run(store, robert_session)
    log = add_section_writers(scripts, **writer_options)
    app.handle_internal(sent[0], store=store)
    run = body_of(app.handle_request(event(RUN, path={"sessionId": robert_session, "runId": body_of(response)["runId"]}), store=store))
    return run, log, auditor


def test_les_sections_precoces_demarrent_avant_la_fin_de_l_auditeur(robert_session, store, scripts, monkeypatch):
    run, log, auditor = _complete(robert_session, store, scripts, monkeypatch, delay=WRITE_SECONDS)
    assert run["status"] == "done" and [s["key"] for s in run["narrative"]["sections"]] == list(KEYS)
    early = [log["calls"][k] for k in ("data_used", "limits")]
    late = [log["calls"][k] for k in ("why", "what_would_change")]
    # Chevauchement réel : les deux sections précoces commencent pendant l'audit, et finissent avant lui (0,1 s < 0,6 s).
    assert all(auditor.start <= c["start"] < auditor.end for c in early)
    assert all(c["end"] < auditor.end for c in early)
    # Les tardives attendent l'auditeur, puis tournent ensemble (le temps total est d'environ 0,6 + 0,1 s, pas 0,6 + 0,2 s).
    assert all(c["start"] >= auditor.end for c in late)
    assert abs(late[0]["start"] - late[1]["start"]) < WRITE_SECONDS


def test_sections_precoces_sans_citation_tardives_avec(robert_session, store, scripts, monkeypatch):
    run, log, _ = _complete(robert_session, store, scripts, monkeypatch)
    for key in ("data_used", "limits"):
        record = log["calls"][key]["record"]
        assert all(v["citations"] == [] for v in record["verdicts"]) and not any(e["id"].startswith("KB-") for e in record["evidence"])
        assert "do not use any {KB-nn} placeholder" in log["calls"][key]["system"]
    for key in ("why", "what_would_change"):
        record = log["calls"][key]["record"]
        assert any(v["citations"] == ["KB-01"] for v in record["verdicts"]) and any(e["id"] == "KB-01" for e in record["evidence"])
        assert "do not use any {KB-nn} placeholder" not in log["calls"][key]["system"]
    assert any(e["id"] == "KB-01" for e in run["evidence"])


def test_une_section_en_echec_donne_status_error_sans_recit(robert_session, store, scripts, monkeypatch):
    run, log, _ = _complete(robert_session, store, scripts, monkeypatch, fail={"data_used"})
    assert run["status"] == "error" and "narrative" not in run
    assert run["scenarios"] and any(v["citations"] == ["KB-01"] for v in run["verdicts"])  # le reste du run est utilisable
    assert set(log["calls"]) == set(KEYS)  # les trois autres sections ont tout de même été écrites


def test_plafond_de_quatre_lectures_dans_toute_la_chaine(robert_session, store, scripts, monkeypatch):
    run, _, _ = _complete(robert_session, store, scripts, monkeypatch, evidence_reads=3)
    steps = run["explanation"]["steps"]
    assert len([s for s in steps if s["tool"] == "read_evidence"]) == 4
    invocations = [s for s in steps if s["agentId"] == "agent-writer" and s["tool"] == "agent_invocation"]
    assert sorted(s["params"]["section"] for s in invocations) == sorted(KEYS) and all(s["status"] == "ok" for s in invocations)


def test_registre_fige_pour_les_sections_precoces(robert_session, store, scripts, monkeypatch):
    """read_evidence d'une section précoce ne voit jamais KB-01, même si l'auditeur l'inscrit pendant qu'elle tourne."""
    seen = {}
    from backend.agents.tools import catalog

    real = catalog.TOOL_FUNCTIONS["read_evidence"]

    def spy(ctx, evidence_id=None):
        seen.setdefault(id(ctx), []).append({e["id"] for e in real(ctx)["items"]})
        return real(ctx, evidence_id)

    monkeypatch.setattr(pipeline.TOOLBOX, "_tools", {**pipeline.TOOLBOX._tools, "read_evidence": spy})
    # Les sections précoces lisent le registre APRÈS que l'auditeur a inscrit KB-01 (délai d'écriture > durée d'audit).
    _complete(robert_session, store, scripts, monkeypatch, auditor=SlowAuditor(0.1), delay=0.4, evidence_reads=1)
    all_reads = [ids for reads in seen.values() for ids in reads]
    assert len(all_reads) == 4
    assert sum("KB-01" in ids for ids in all_reads) == 2  # les deux tardives seulement
