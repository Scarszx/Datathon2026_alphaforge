"""Préfixe de contexte du Guardrail : envoyé en entrée seulement, jamais renvoyé."""

from backend.agents import guardrails


class Recorder:
    def __init__(self, response):
        self.response = response
        self.sent = []

    def apply_guardrail(self, **kwargs):
        self.sent.append((kwargs["source"], kwargs["content"][0]["text"]["text"]))
        return self.response


def _configure(monkeypatch):
    monkeypatch.setenv("GUARDRAIL_ID", "gr-1")
    monkeypatch.setenv("GUARDRAIL_VERSION", "1")


def test_entree_recoit_le_prefixe(monkeypatch):
    _configure(monkeypatch)
    rec = Recorder({"action": "NONE"})
    res = guardrails.apply("How can you help me?", "INPUT", client=rec)
    assert rec.sent == [("INPUT", guardrails.INPUT_CONTEXT_PREFIX + "How can you help me?")]
    assert not res.blocked and res.checked
    assert res.text == "How can you help me?"  # le texte conservé reste celui de l'utilisateur


def test_sortie_sans_prefixe(monkeypatch):
    _configure(monkeypatch)
    rec = Recorder({"action": "NONE"})
    guardrails.apply("Scenario 1 fails rule R2.", "OUTPUT", client=rec)
    assert rec.sent == [("OUTPUT", "Scenario 1 fails rule R2.")]


def test_texte_masque_sans_prefixe(monkeypatch):
    _configure(monkeypatch)
    masked = guardrails.INPUT_CONTEXT_PREFIX + "my account is {ACCOUNT}"
    rec = Recorder({"action": "GUARDRAIL_INTERVENED", "outputs": [{"text": masked}], "assessments": []})
    res = guardrails.apply("my account is 12345-678-1234567", "INPUT", client=rec)
    assert not res.blocked
    assert res.text == "my account is {ACCOUNT}"


def test_blocage_conserve(monkeypatch):
    _configure(monkeypatch)
    rec = Recorder({"action": "GUARDRAIL_INTERVENED", "outputs": [{"text": "Refus."}],
                    "assessments": [{"topicPolicy": {"topics": [{"name": "Orders", "action": "BLOCKED"}]}}]})
    res = guardrails.apply("Buy 100 shares for me.", "INPUT", client=rec)
    assert res.blocked and res.blocked_by_topic and not res.blocked_by_pii
    assert res.text == "Refus."
