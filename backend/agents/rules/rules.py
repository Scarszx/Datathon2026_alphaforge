"""module-rules : R1 à R10 (contrat rules_catalog, SOLUTION.md section 9), sans LLM.

Produit des verdicts schema-rule-verdict SANS citations : agent-auditor les
ajoute ensuite depuis la Knowledge Base. messageEn reçoit ici une phrase par
défaut, en anglais et sans chiffre (les chiffres sont dans evidence) : le
verdict reste lisible si l'auditeur échoue. Les seuils d'hypothèse viennent de
rules_config.json et sont marqués threshold.nature = team_assumption.
"""

from __future__ import annotations

from typing import Any

from backend.agents.engine.scenarios import EngineResult, ScenarioAnalysis, _crypto_refused
from backend.agents.rules.settings import settings

ORDER = {"pass": 0, "not_verified": 0, "warn": 1, "fail": 2}

# Nom de la règle en anglais (sujet KB et requête de l'auditeur).
RULE_TOPICS = {
    "R1": "risk profile is the lower of risk tolerance and risk capacity",
    "R2": "investment time horizon and maximum acceptable loss in suitability",
    "R3": "impact of an investment on the client's overall account or portfolio",
    "R4": "reasonable range of alternative actions",
    "R5": "order-execution-only services must not recommend a specific security",
    "R6": "concentration and diversification of a portfolio",
    "R7": "crypto assets risks and platform registration",
    "R8": "investment funds presenting themselves as ESG",
    "R9": "protected titles financial planner and provincial regulator",
    "R10": "use of macroeconomic data only after its publication",
}

RULE_SUBJECTS = {
    "R1": ["profil_risque", "convenance"], "R2": ["convenance"], "R3": ["convenance"], "R4": ["convenance"],
    "R5": ["oeo"], "R6": ["convenance"], "R7": ["crypto"], "R8": ["esg"], "R9": ["titres_proteges"], "R10": [],
}


def _verdict(rule: str, scenario: int | None, status: str, reason: str, message: str,
             evidence: list[str] | None = None, threshold: dict[str, Any] | None = None) -> dict[str, Any]:
    verdict: dict[str, Any] = {
        "rule": rule, "status": status, "reasonCode": reason, "evidence": [e for e in (evidence or []) if e],
        "citations": [], "messageEn": message,
    }
    if scenario is not None:
        verdict["scenario"] = scenario
    if threshold is not None:
        verdict["threshold"] = threshold
    return verdict


def _ev(scenario: ScenarioAnalysis, *keys: str) -> list[str]:
    return [scenario.evidence[k] for k in keys if k in scenario.evidence]


def r1(mandate_item: dict[str, Any], scenario: ScenarioAnalysis) -> dict[str, Any]:
    profile = int(mandate_item["riskProfile"])
    excess_portfolio = (scenario.portfolio_band or 0) - profile if scenario.portfolio_band else 0
    excess_assets = max((a["band"] - profile for a in scenario.idea_assets if a["band"]), default=0)
    excess = max(excess_portfolio, excess_assets)
    evidence = _ev(scenario, "volatility")
    if scenario.index == 0:
        status = "warn" if excess >= 2 else "pass"
    else:
        status = "fail" if excess >= 2 else "warn" if excess == 1 else "pass"
    if status == "pass":
        reason, message = "RISK_PROFILE_RESPECTED", "The scenario's risk level is consistent with the retained risk profile (the lower of tolerance and capacity)."
    elif excess_assets >= excess_portfolio and scenario.index:
        reason, message = "IDEA_EXCEEDS_RISK_PROFILE", "The tested idea implies a higher risk profile than the retained one, which is the lower of risk tolerance and risk capacity."
    else:
        reason, message = "PORTFOLIO_EXCEEDS_RISK_PROFILE", "The portfolio's volatility implies a higher risk profile than the retained one."
    return _verdict("R1", scenario.index, status, reason, message, evidence,
                    {"value": profile, "nature": "text"})


def r2(mandate_item: dict[str, Any], scenario: ScenarioAnalysis) -> dict[str, Any]:
    limit = float(mandate_item["effectiveMaxLossPct"])
    user_set = "maxAcceptableLossPct" in mandate_item["mandate"]
    # Valeur saisie par l'utilisateur : ni texte réglementaire ni hypothèse d'équipe,
    # donc sans `nature` (écart noté dans NOTES-agents.md).
    threshold = {"value": limit} if user_set else {"value": limit, "nature": "team_assumption"}
    if "maxDrawdown" not in scenario.metrics:
        return _verdict("R2", scenario.index, "not_verified", "DRAWDOWN_NOT_COMPUTED",
                        "The historical drawdown could not be computed for this scenario.", [], threshold)
    loss = abs(scenario.metrics["maxDrawdown"])
    evidence = _ev(scenario, "maxDrawdown", "stress2022", "stressRates", "stressCovid2020", "stressCrypto")
    ratio = float(settings()["maxLossWarnRatio"])
    if loss > limit:
        status, reason, message = "fail", "MAX_LOSS_EXCEEDED", "The worst simulated historical decline exceeds the maximum acceptable loss for this mandate."
    elif loss >= ratio * limit:
        status, reason, message = "warn", "MAX_LOSS_NEAR_LIMIT", "The worst simulated historical decline comes close to the maximum acceptable loss for this mandate."
    else:
        status, reason, message = "pass", "MAX_LOSS_WITHIN_LIMIT", "The worst simulated historical decline stays within the maximum acceptable loss for this mandate."
    return _verdict("R2", scenario.index, status, reason, message, evidence, threshold)


def r3(scenario: ScenarioAnalysis) -> dict[str, Any]:
    if not scenario.weights:
        return _verdict("R3", scenario.index, "warn", "EMPTY_PORTFOLIO",
                        "The portfolio is empty: the impact cannot be measured on an existing portfolio.")
    return _verdict("R3", scenario.index, "pass", "PORTFOLIO_LEVEL_IMPACT",
                    "The impact is measured on the whole portfolio, not on the added security alone.",
                    _ev(scenario, "volatility", "maxDrawdown"))


def r6(scenario: ScenarioAnalysis) -> dict[str, Any]:
    conf = settings()["singleSecurity"]
    threshold = {"value": conf["warnPct"], "nature": "team_assumption"}
    top = (scenario.concentration or {}).get("topSingle") or {}
    weight = float(top.get("weight") or 0.0)
    evidence = _ev(scenario, "topSingleWeight")
    if weight > conf["failPct"]:
        threshold = {"value": conf["failPct"], "nature": "team_assumption"}
        status, reason, message = "fail", "CONCENTRATION_HIGH", "A single security, including through fund holdings, carries a very large share of the portfolio."
    elif weight > conf["warnPct"]:
        status, reason, message = "warn", "CONCENTRATION_ELEVATED", "A single security, including through fund holdings, carries a large share of the portfolio."
    else:
        status, reason, message = "pass", "CONCENTRATION_OK", "No single security, including through fund holdings, dominates the portfolio."
    if scenario.concentration and not scenario.concentration.get("lookThroughComplete", True):
        message += " Fund look-through is incomplete for some funds."
    return _verdict("R6", scenario.index, status, reason, message, evidence, threshold)


def r7(mandate_item: dict[str, Any], scenario: ScenarioAnalysis) -> dict[str, Any]:
    caps = settings()["cryptoCapPct"]
    profile = int(mandate_item["riskProfile"])
    if _crypto_refused(mandate_item["mandate"]):
        cap = caps["excluded"]
    else:
        cap = caps["profileUpTo3"] if profile <= 3 else caps["profileAbove3"]
    weight = float((scenario.concentration or {}).get("cryptoWeight") or 0.0)
    evidence = _ev(scenario, "cryptoWeight", "stressCrypto")
    threshold = {"value": cap, "nature": "team_assumption"}
    if weight <= 0:
        return _verdict("R7", scenario.index, "pass", "NO_CRYPTO_EXPOSURE", "The scenario holds no crypto assets.", evidence, threshold)
    if weight > cap:
        return _verdict("R7", scenario.index, "fail", "CRYPTO_CAP_EXCEEDED",
                        "Crypto-asset exposure exceeds the cap for this mandate; crypto assets carry specific platform and custody risks.",
                        evidence, threshold)
    return _verdict("R7", scenario.index, "warn", "CRYPTO_WITHIN_CAP",
                    "Crypto-asset exposure stays within the cap for this mandate, but crypto assets carry specific platform and custody risks.",
                    evidence, threshold)


def r8(store, mandate_item: dict[str, Any], scenario: ScenarioAnalysis) -> dict[str, Any]:
    preferences = mandate_item["mandate"].get("preferences") or {}
    if not preferences.get("esg"):
        return _verdict("R8", scenario.index, "pass", "ESG_NOT_REQUESTED", "No ESG preference in the mandate.")
    enriched = store.etf_enriched()
    unverified = []
    for ticker in scenario.weights:
        asset_class = (store.asset(ticker).get("asset_class") or "").lower()
        sheet = enriched.get(ticker) or {}
        if asset_class.startswith("etf") and (sheet.get("exclusions") or sheet.get("esgMethodologyUrl")):
            continue
        unverified.append(ticker)
    if not unverified:
        return _verdict("R8", scenario.index, "pass", "ESG_SOURCED",
                        "Every fund presented as ESG has a published issuer methodology.")
    return _verdict("R8", scenario.index, "warn", "ESG_NOT_VERIFIED",
                    "Some holdings have no published ESG methodology: for equities only the sector is known and controversies are not verified.")


def run_level_rules(result: EngineResult, scenario_verdicts: list[dict[str, Any]], mandate_item: dict[str, Any],
                    universe_tickers: set[str]) -> list[dict[str, Any]]:
    verdicts = []
    # R4 : une alternative dès qu'un scénario de l'idée est en WARN ou FAIL.
    idea_status = max((ORDER[v["status"]] for v in scenario_verdicts if v.get("scenario") == 1), default=0)
    has_alternative = any(s.index == 2 for s in result.scenarios)
    if idea_status == 0:
        verdicts.append(_verdict("R4", None, "pass", "ALTERNATIVE_NOT_REQUIRED", "The idea raises no warning: no alternative is required."))
    elif has_alternative:
        verdicts.append(_verdict("R4", None, "pass", "ALTERNATIVE_PRESENTED", "At least one reasonable alternative by asset category is presented."))
    else:
        verdicts.append(_verdict("R4", None, "fail", "ALTERNATIVE_MISSING", "The idea raises a warning but no compatible alternative category was found in the dataset."))

    # R5 : l'alternative ne nomme aucun titre (description et libellé).
    texts = " ".join(filter(None, [s.description for s in result.scenarios if s.index == 2] + [s.label for s in result.scenarios]))
    named = sorted(t for t in universe_tickers if t and _contains_ticker(texts, t))
    if named:
        verdicts.append(_verdict("R5", None, "fail", "SECURITY_NAMED", "The alternative names a specific security."))
    else:
        verdicts.append(_verdict("R5", None, "pass", "NO_SECURITY_RECOMMENDED", "The alternative is expressed by asset category; no specific security is recommended."))

    # R9 : mentions de la province (texte dans jurisdictionNotices).
    verdicts.append(_verdict("R9", None, "pass", "PROVINCE_NOTICES_ADDED",
                             "Province-specific notices name the regulator and the protected titles this tool does not use."))

    # R10 : aucune donnée macro avant sa date de publication.
    late = [u for u in result.macro_usage if u.get("publication") is not None and u["publication"] > u["asOf"]]
    if late:
        verdicts.append(_verdict("R10", None, "fail", "MACRO_USED_BEFORE_PUBLICATION", "A macroeconomic value was used before its publication date."))
    else:
        verdicts.append(_verdict("R10", None, "pass", "MACRO_PUBLICATION_RESPECTED",
                                 "Only daily macroeconomic series, known on their observation date, were used."))
    return verdicts


def _contains_ticker(text: str, ticker: str) -> bool:
    import re

    return re.search(rf"(?<![A-Za-z0-9.\-]){re.escape(ticker)}(?![A-Za-z0-9\-])", text) is not None


def check_rules(store, mandate_item: dict[str, Any], result: EngineResult) -> list[dict[str, Any]]:
    """Applique R1-R10 ; renvoie la liste des verdicts (sans citations)."""
    scenario_verdicts: list[dict[str, Any]] = []
    for scenario in result.scenarios:
        scenario_verdicts.extend([
            r1(mandate_item, scenario), r2(mandate_item, scenario), r3(scenario),
            r6(scenario), r7(mandate_item, scenario), r8(store, mandate_item, scenario),
        ])
    universe = set(store.universe().index)
    return scenario_verdicts + run_level_rules(result, scenario_verdicts, mandate_item, universe)


def scenario_verdicts(verdicts: list[dict[str, Any]]) -> dict[int, str]:
    """Verdict d'un scénario = le pire statut de ses règles (not_verified ne compte pas)."""
    worst: dict[int, int] = {}
    for verdict in verdicts:
        if "scenario" not in verdict:
            continue
        worst[verdict["scenario"]] = max(worst.get(verdict["scenario"], 0), ORDER[verdict["status"]])
    names = {0: "pass", 1: "warn", 2: "fail"}
    return {index: names[level] for index, level in worst.items()}


def jurisdiction_notices(province: str) -> list[str]:
    conf = settings()
    notices = conf["provinceNotices"]
    return [notices.get(province, notices["default"]), conf["baseNotice"]]
