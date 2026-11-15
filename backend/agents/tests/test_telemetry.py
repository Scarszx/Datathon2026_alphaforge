"""Tests unitaires de backend/agents/telemetry.py : résolution des clés, spans et propagation."""

from __future__ import annotations

import json

from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from strands.telemetry import StrandsTelemetry

from backend.agents import guardrails, telemetry
from backend.agents.llm.base import build_agent
from backend.agents.tools import kb
from backend.agents.tools.context import RequestContext


class _FakeSSM:
    def __init__(self, value: str | None = None, error: Exception | None = None):
        self.value = value
        self.error = error
        self.calls: list[tuple[str, bool]] = []

    def get_parameter(self, *, Name: str, WithDecryption: bool = False):
        self.calls.append((Name, WithDecryption))
        if self.error:
            raise self.error
        return {"Parameter": {"Value": self.value}}


def test_resolve_credentials_ignore_placeholder_and_read_ssm(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-a2d4308e-ebc7-41b4-b0e5-69afc46d74cd")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-*")
    monkeypatch.setenv("LANGFUSE_SECRET_PARAM", "/alphaforge/langfuse/secret-key")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com/")

    ssm = _FakeSSM(value="sk-lf-real-secret-from-ssm")
    pub, sec, url = telemetry.resolve_credentials(ssm_client=ssm)
    assert pub == "pk-lf-a2d4308e-ebc7-41b4-b0e5-69afc46d74cd"
    assert sec == "sk-lf-real-secret-from-ssm"
    assert url == "https://us.cloud.langfuse.com"
    assert ssm.calls == [("/alphaforge/langfuse/secret-key", True)]


def test_resolve_credentials_ssm_json_and_fail_open(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_SECRET_PARAM", "/alphaforge/langfuse/keys")

    ssm_json = _FakeSSM(value=json.dumps({"publicKey": "pk-lf-json", "secretKey": "sk-lf-json"}))
    pub, sec, _ = telemetry.resolve_credentials(ssm_client=ssm_json)
    assert (pub, sec) == ("pk-lf-json", "sk-lf-json")

    ssm_err = _FakeSSM(error=RuntimeError("SSM unreachable"))
    pub_err, sec_err, _ = telemetry.resolve_credentials(ssm_client=ssm_err)
    assert (pub_err, sec_err) == (None, None)


def test_trace_span_hierarchy_and_context_propagation(store, scripts, monkeypatch):
    exporter = InMemorySpanExporter()
    st = StrandsTelemetry()
    st.tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    telemetry.reset_for_tests(st)
    try:
        with telemetry.trace_span(
            "analysis-run",
            trace_name="analysis-run",
            observation_type="chain",
            session_id="sess-123",
            user_id="user-456",
            tags=["feature:analysis-run"],
            input_data={"mandateVersion": 1},
        ) as root_span:
            carrier = telemetry.inject_trace_context()
            telemetry.set_span_output(root_span, {"status": "partial"})

        assert "traceparent" in carrier

        with telemetry.trace_span(
            "analysis-complete-run",
            trace_name="analysis-run",
            observation_type="chain",
            session_id="sess-123",
            user_id="user-456",
            parent_carrier=carrier,
            input_data={"runId": "01RUN"},
        ) as child_span:
            monkeypatch.setenv("GUARDRAIL_ID", "gr-1")
            monkeypatch.setenv("GUARDRAIL_VERSION", "1")
            guardrails.apply(
                "What if I add 10% XIU?",
                "INPUT",
                client=type("G", (), {"apply_guardrail": staticmethod(lambda **_: {"action": "NONE"})})(),
            )
            monkeypatch.setenv("KB_ID", "kb-1")
            kb.retrieve(
                "risk profile",
                ["CA", "QC"],
                ["profil_risque"],
                client=type(
                    "K",
                    (),
                    {
                        "retrieve": staticmethod(
                            lambda **_: {
                                "retrievalResults": [
                                    {
                                        "content": {"text": "Excerpt"},
                                        "location": {"s3Location": {"uri": "s3://b/CA_31-368.pdf"}},
                                        "metadata": {"juridiction": "CA", "regulateur": "CSA"},
                                        "score": 0.91,
                                    }
                                ]
                            }
                        )
                    },
                )(),
            )
            telemetry.set_span_output(child_span, {"status": "done"})

        telemetry.flush_telemetry()
        spans = {s.name: s for s in exporter.get_finished_spans()}
        assert {"analysis-run", "analysis-complete-run", "guardrail.input", "kb.retrieve"} <= set(spans)

        # Le span asynchrone complete_run partage exactement le même trace_id que analysis-run
        assert spans["analysis-complete-run"].context.trace_id == spans["analysis-run"].context.trace_id
        assert spans["analysis-complete-run"].parent.span_id == spans["analysis-run"].context.span_id

        assert spans["analysis-run"].attributes["langfuse.observation.type"] == "chain"
        assert spans["analysis-run"].attributes["langfuse.trace.name"] == "analysis-run"
        assert spans["analysis-run"].attributes["langfuse.session.id"] == "sess-123"
        assert spans["analysis-run"].attributes["langfuse.user.id"] == "user-456"
        assert spans["guardrail.input"].attributes["langfuse.observation.type"] == "guardrail"
        assert spans["kb.retrieve"].attributes["langfuse.observation.type"] == "retriever"

        ctx = RequestContext(user_id="user-456", session_id="sess-123", store=store)
        agent = build_agent("agent-orchestrator", "System prompt", ctx, with_tools=False)
        assert agent.trace_attributes["langfuse.session.id"] == "sess-123"
        assert agent.trace_attributes["langfuse.user.id"] == "user-456"
        assert agent.trace_attributes["langfuse.observation.type"] == "agent"
    finally:
        telemetry.reset_for_tests(None)
