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


# --- lot A : jugements de conformité ou de convenance ------------------------------------------------------------

@pytest.mark.parametrize("sentence", [
    "The scenario is compliant.", "This portfolio complies with the guidance.", "This idea is suitable.",
    "These bonds are suitable for you.", "This suits you.", "It is compatible with your risk profile.",
    "This idea is not suitable for you.", "Le scénario est conforme.", "Ce scénario n'est pas conforme.",
    "Non conforme.", "Ce titre vous convient.", "Adapté à votre profil.", "Compatible avec votre profil.",
    "The current portfolio passes.", "Its volatility fits the retained risk profile.",
    "Les obligations conviennent à ce mandat.",
])
def test_jugements_de_conformite_masques(sentence):
    _, hidden, report = verify_narrative([_section(sentence)], IDS, MANDATE)
    assert hidden and hidden[0]["reason"] == "forbidden_phrase" and report["forbiddenPhrases"] >= 1


@pytest.mark.parametrize("sentence", [
    "AlphaForge does not assess whether this suits you.",
    "AlphaForge takes no position on whether the output is suitable for the user.",
    "AlphaForge ne se prononce pas sur ce qui vous convient.",
    "Conformément à la note 31-368, le profil retenu est le plus bas des deux.",
    "The rule was not triggered.", "La règle n'a pas été déclenchée.",
])
def test_phrases_ou_l_outil_ne_juge_pas_conservees(sentence):
    cleaned, hidden, _ = verify_narrative([_section(sentence)], IDS, MANDATE)
    assert hidden == [] and cleaned[0]["text"] == sentence


def test_les_recommandations_restent_masquees_meme_avec_un_avertissement():
    cleaned, hidden, _ = verify_narrative(
        [_section("AlphaForge does not assess suitability, but we recommend this fund.")], IDS, MANDATE)
    assert hidden[0]["reason"] == "forbidden_phrase" and cleaned[0]["text"] == ""


def test_recits_reels_de_langfuse_du_15_novembre():
    """Phrases écrites par le rédacteur et la traduction (runs de démonstration) : celles qui approuvent sont masquées."""
    import json
    from pathlib import Path

    data = json.loads((Path(__file__).parent / "fixtures" / "langfuse_narratives_2026-11-15.json").read_text())
    for narrative in data["narratives"]:
        sections = [_section(text, key="why") for text in narrative["sections"]]
        cleaned, hidden, _ = verify_narrative(sections, set(), {})
        kept = " ".join(s["text"] for s in cleaned)
        for phrase in narrative["mustBeHidden"]:
            assert phrase not in kept, phrase


# --- lot B : symboles de l'univers ----------------------------------------------------------------------------------

UNIVERSE = {"ZST.TO", "XBB.TO", "NVDA", "SPY", "ON", "T", "V", "R6", "BTC-USD"}


def _symbols(text, held=frozenset({"XBB.TO"})):
    cleaned, hidden, report = verify_narrative([_section(text)], IDS, MANDATE, UNIVERSE, set(held))
    return cleaned[0]["text"], hidden, report


@pytest.mark.parametrize("sentence", [
    "The comparison uses ZST.TO only as an approximation.",
    "L'alternative utilise un fonds (ZST.TO) pour le calcul.",
    "The reference is SPY.", "Crypto assets such as BTC-USD are volatile.",
])
def test_symbole_non_ecrit_ni_detenu_masque(sentence):
    text, hidden, report = _symbols(sentence)
    assert text == "" and hidden[0]["reason"] == "forbidden_phrase" and report["forbiddenPhrases"] >= 1


@pytest.mark.parametrize("sentence", [
    "NVDA is the security you typed.", "XBB.TO is already in your portfolio.",
    "Rule R6 applies in ON.", "The T and V symbols are not searched.", "The zst fund is lowercase text.",
    "Volatility reaches {EV-07} for ZSTX.", "Securities regulators in QC publish guidance.",
])
def test_symboles_ecrits_detenus_exclus_ou_hors_perimetre_conserves(sentence):
    text, hidden, _ = _symbols(sentence)
    assert hidden == [] and text == sentence


def test_sans_univers_le_controle_de_symbole_est_inactif():
    cleaned, hidden, _ = verify_narrative([_section("The comparison uses ZST.TO.")], IDS, MANDATE)
    assert hidden == [] and cleaned[0]["text"] == "The comparison uses ZST.TO."


def test_recits_langfuse_le_fnb_d_approximation_est_masque():
    """Traces du 2026-11-15 : « (ZST.TO) » et « (XBB.TO) » dans le récit alors que l'utilisateur n'a écrit que NVDA/TSLA."""
    sentence = "The alternative uses a Canadian short-term bond fund (ZST.TO) only as an approximation of the asset category."
    text, hidden, _ = _symbols(sentence, held=set())
    assert text == "" and hidden
