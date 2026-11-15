"""module-verifier : emplacement inconnu, chiffre écrit à la main, formules interdites (EN et FR)."""

from __future__ import annotations

import pytest

from backend.agents.verifier.verifier import handwritten_numbers, verify_narrative

MANDATE = {"horizonYears": 3, "operations": [{"action": "add", "ticker": "NVDA", "amount": 15000}]}
IDS = {"EV-01", "EV-07", "KB-03"}


def _section(text_en, text=None, key="why"):
    return {"key": key, "textEn": text_en, "text": text if text is not None else text_en}


def test_phrases_conformes_conservees_et_score():
    sections = [_section("Volatility reaches {EV-07} in scenario one. Notice 31-368 says the lower of the two applies {KB-03}.")]
    cleaned, hidden, report = verify_narrative(sections, IDS, MANDATE)
    assert hidden == [] and cleaned[0]["text"] == sections[0]["text"]
    assert report == {"placeholdersResolved": 2, "placeholdersTotal": 2, "handwrittenNumbers": 0,
                      "forbiddenPhrases": 0, "placeholdersMatch": True}


def test_emplacement_inconnu_masque():
    cleaned, hidden, report = verify_narrative([_section("It fell {EV-99}. It is diversified.")], IDS, MANDATE)
    assert cleaned[0]["text"] == "It is diversified."
    assert hidden == [{"section": "why", "reason": "unknown_placeholder"}]
    assert report["placeholdersResolved"] == 0 and report["placeholdersTotal"] == 1


@pytest.mark.parametrize("sentence", [
    "Volatility is 15.2% here.", "La volatilité atteint 15,2 % ici.", "It lost 3 500 $ in a month.",
    "Rates rose by 25 bps.", "The ratio is 1.5x.", "It returned 42 over the period.",
])
def test_chiffre_ecrit_a_la_main_masque(sentence):
    _, hidden, report = verify_narrative([_section(sentence)], IDS, MANDATE)
    assert hidden and hidden[0]["reason"] == "handwritten_number" and report["handwrittenNumbers"] >= 1


@pytest.mark.parametrize("sentence", [
    "Your horizon of 3 years is short.", "Adding 15 000 $ changes the risk.", "Adding $15,000 changes the risk.",
    "Notice 31-368 applies.", "The 2022 stress test is shown.", "Rule R6 is a team assumption.",
    "CIRO guidance GN-3200-26-001 frames this tool.", "Two scenarios are compared.",
])
def test_constantes_et_references_autorisees(sentence):
    assert handwritten_numbers(sentence, {3.0, 15000.0}) == []


@pytest.mark.parametrize("sentence", [
    "You should buy this stock.", "Returns are guaranteed.", "Vous devriez acheter ce titre.",
    "Ce rendement est garanti.", "Nous recommandons ce fonds.", "Ask your financial planner.",
])
def test_formules_interdites_en_et_fr(sentence):
    _, hidden, report = verify_narrative([_section(sentence)], IDS, MANDATE)
    assert hidden[0]["reason"] == "forbidden_phrase" and report["forbiddenPhrases"] == 1


def test_traduction_qui_perd_un_emplacement():
    sections = [_section("It fell {EV-07}, see {KB-03}.", "Il a baissé, voir {KB-03}.")]
    _, _, report = verify_narrative(sections, IDS, MANDATE)
    assert report["placeholdersMatch"] is False


def test_controle_sur_le_texte_traduit_affiche():
    sections = [_section("It fell {EV-07}.", "Il a baissé de 12 % {EV-07}.")]
    cleaned, hidden, _ = verify_narrative(sections, IDS, MANDATE)
    assert cleaned[0]["text"] == "" and hidden[0]["reason"] == "handwritten_number"
