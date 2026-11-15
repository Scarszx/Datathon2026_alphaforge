"""GovernanceAgent: CONTROL. Verifies outputs against the investor's constraints AND the simulation-only boundary.

Why it exists: the allocation agent optimises; something independent must say "no" when a result or a request
breaks the profile (Robert asking for 40 % in a hyped stock), when data is too thin, or when wording drifts into
advice. Its checks are shown verbatim to the user (pass / warn / fail / not_verified).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from ..trace import Trace
from .allocation import GROWTH_SECTORS, is_fund, pocket_of
from .profile import RISK_LABEL, Policy, norm

AGENT_ID = "governance"

TRADE_PATTERNS = [r"\bach[eè]te(?:r)? pour moi\b", r"\bpasse(?:r)? (?:un |l')?ordre\b", r"\bex[eé]cute(?:r)?\b.*\b(?:ordre|transaction|achat|vente)\b",
                  r"\bvends? (?:mes|tout)\b", r"\bbuy (?:it )?for me\b", r"\bplace (?:an |the )?order\b", r"\bvirement\b",
                  r"\bmon (?:vrai|v[ée]ritable) compte\b", r"\bnum[ée]ro de compte\b"]
ADVICE_WORDS = ["garanti", "sans risque", "vous devez acheter", "achetez", "vendez", "certainement", "rendement assuré", "guaranteed",
                "you should buy", "conseil personnalis"]


def boundary(question: str, trace: Trace) -> Optional[str]:
    q = norm(question)
    for p in TRADE_PATTERNS:
        if re.search(norm(p), q):
            trace.check(AGENT_ID, "simulation_only", "fail",
                        "Demande de transaction réelle ou de données de compte : hors du cadre (simulation seulement).")
            return "trade"
    trace.check(AGENT_ID, "simulation_only", "pass", "Aucune transaction exécutée; analyse fictive sur données publiques.")
    return None


def check_allocation(alloc: dict, p: Policy, stats: Dict[str, dict], trace: Trace) -> None:
    w: Dict[str, float] = alloc["_weights"]
    ps = alloc["stats"]
    singles = {t: v for t, v in w.items() if not is_fund(stats[t]) and stats[t]["assetClass"] != "crypto"}
    top = max(singles.items(), key=lambda x: x[1]) if singles else None
    trace.check(AGENT_ID, "max_single_security", "pass" if not top or top[1] <= p.max_single + 0.01 else "fail",
                f"Plus grosse position individuelle : {top[0]} {top[1]:.1f} % (plafond {p.max_single:.0f} %)." if top else "Aucun titre individuel.",
                top[1] if top else 0, p.max_single)
    funds = {t: v for t, v in w.items() if is_fund(stats[t])}
    ftop = max(funds.items(), key=lambda x: x[1]) if funds else None
    if ftop:
        trace.check(AGENT_ID, "max_fund", "pass" if ftop[1] <= p.max_fund + 0.5 else "warn",
                    f"Plus gros fonds : {ftop[0]} {ftop[1]:.1f} % (repère {p.max_fund:.0f} %, un fonds indiciel est déjà diversifié).", ftop[1], p.max_fund)
    g = alloc["growthShare"]
    trace.check(AGENT_ID, "sector_concentration", "pass" if g <= p.max_sector + 0.5 else "warn",
                f"Technologie et croissance : {g:.1f} % (repère {p.max_sector:.0f} %).", g, p.max_sector)
    crypto = sum(v for t, v in w.items() if stats[t]["assetClass"] == "crypto")
    trace.check(AGENT_ID, "crypto_cap", "pass" if crypto <= p.max_crypto + 0.01 else "fail",
                f"Crypto-actifs : {crypto:.1f} % (plafond {p.max_crypto:.0f} %).", crypto, p.max_crypto)
    d = alloc["byPocket"].get("defensive", 0)
    trace.check(AGENT_ID, "defensive_floor", "pass" if d >= p.min_defensive - 0.5 else "warn",
                f"Poche défensive (obligations, or) : {d:.1f} % (plancher {p.min_defensive:.0f} %).", d, p.min_defensive)
    n = ps["effectiveN"]
    trace.check(AGENT_ID, "diversification", "pass" if n >= p.min_holdings else "warn",
                f"Nombre effectif de positions : {n:.1f} (repère ≥ {p.min_holdings}).", n, p.min_holdings)
    v = ps["vol3y"]
    trace.check(AGENT_ID, "volatility_budget", "pass" if v is not None and v <= p.vol_budget + 0.05 else "warn",
                f"Volatilité historique 3 ans : {v} % (budget {p.vol_budget:.0f} % pour un risque {RISK_LABEL[p.risk_level]}).", v, p.vol_budget)
    dd = ps["maxDrawdown5y"]
    trace.check(AGENT_ID, "drawdown_tolerance", "pass" if dd is not None and -dd <= p.dd_tolerance else "warn",
                f"Pire baisse historique sur 5 ans : {dd} % (tolérance {p.dd_tolerance:.0f} %).", dd, -p.dd_tolerance)
    if p.esg:
        bad = [t for t in w if stats[t]["esgScreen"] == "exclude_candidate" or (p.avoid_controversy and stats[t]["esgScreen"] == "watch")]
        trace.check(AGENT_ID, "esg_preferences", "pass" if not bad else "fail",
                    "Aucun titre exclu par le filtre ESG d'activités." if not bad else f"Titres contraires au filtre ESG : {', '.join(bad)}.")
        fossil_funds = [t for t in w if "fossil_fuel_extraction" in stats[t]["esgTags"]]
        if fossil_funds:
            trace.check(AGENT_ID, "esg_indirect_exposure", "warn",
                        f"{', '.join(fossil_funds)} : fonds indiciel large qui contient des producteurs d'énergie. Aucun fonds américain filtré ESG "
                        "dans l'univers : exposition indirecte résiduelle.")
    if p.horizon_min < 5 and crypto > 0:
        trace.check(AGENT_ID, "horizon_fit", "fail", "Crypto-actifs incompatibles avec un horizon inférieur à 5 ans.")


def check_request(ticker: str, pct: Optional[float], s: dict, p: Policy, base: dict, variant: Optional[dict], trace: Trace) -> dict:
    """Evaluate a user request for a specific asset against the profile. Returns verdict data."""
    issues: List[str] = []
    status = "pass"
    asked = pct if pct is not None else None
    single_cap = p.max_fund if is_fund(s) else (p.max_crypto if s["assetClass"] == "crypto" else p.max_single)
    if s["assetClass"] in p.excluded_classes or (s["assetClass"] == "crypto" and p.max_crypto == 0):
        status = "fail"
        issues.append(f"{ticker} appartient à une classe d'actifs exclue par le profil ou hors politique ({s['assetClass']}).")
    if p.esg and (s["esgScreen"] == "exclude_candidate" or (p.avoid_controversy and s["esgScreen"] == "watch")):
        status = "fail"
        issues.append(f"{ticker} est contraire aux préférences ESG du profil ({', '.join(s['esgTags']) or s['esgScreen']}).")
    if asked is not None and asked > single_cap + 0.01:
        status = "fail"
        issues.append(f"{asked:.0f} % dans une seule position dépasse le plafond de {single_cap:.0f} % retenu pour ce profil.")
    if (s["vol3y"] or 0) > 2 * p.vol_budget and pocket_of(s) != "core":
        status = "fail" if status == "fail" or p.risk_level in ("low", "low_moderate") else "warn"
        issues.append(f"Volatilité 3 ans de {ticker} : {s['vol3y']:.0f} %, plus du double du budget du profil ({p.vol_budget:.0f} %).")
    if s["maxDrawdown"] is not None and -s["maxDrawdown"] > p.dd_tolerance:
        rec = f", récupérée en {s['recoveryDays']} jours" if s.get("recoveryDays") else ", non récupérée à la date d'analyse"
        if status != "fail":
            status = "warn"
        issues.append(f"Pire baisse historique de {ticker} : {s['maxDrawdown']:.0f} % ({s['peakDate']} → {s['troughDate']}{rec}); tolérance du profil {p.dd_tolerance:.0f} %.")
    if p.horizon_min < 5 and s.get("recoveryDays") and s["recoveryDays"] > 365 * min(p.horizon_min, 3) / 2:
        issues.append(f"Le temps de récupération observé ({s['recoveryDays']} jours) occupe une grande partie de l'horizon de {p.horizon_min} ans.")
    if p.established_only and pocket_of(s) == "satellite" and ((s["vol3y"] or 99) >= 30 or not s["dividendYield"]):
        if status == "pass":
            status = "warn"
        issues.append("Ne correspond pas au critère « entreprise établie et compréhensible » retenu (volatilité 3 ans < 30 % et dividende versé).")
    if s["stale"]:
        status = "not_verified"
        issues.append("Cours ancien : vérification impossible.")
    if variant:
        dv = (variant["stats"]["vol3y"] or 0) - (base["stats"]["vol3y"] or 0)
        issues.append(f"Avec {asked:.0f} % dans {ticker}, la volatilité historique du portefeuille fictif passe de {base['stats']['vol3y']} % à "
                      f"{variant['stats']['vol3y']} % ({'+' if dv >= 0 else ''}{dv:.1f} pt) et la part de risque venant de {ticker} atteint "
                      f"{variant['stats']['riskContributions'].get(ticker, 0)} %.")
    msg = " ".join(issues) if issues else f"{ticker} est compatible avec les contraintes du profil."
    trace.check(AGENT_ID, "request_profile_consistency", status, msg)
    return {"status": status, "issues": issues, "singleCap": single_cap}


def max_compatible_weight(ticker: str, s: dict, p: Policy) -> float:
    """Largest weight compatible with caps (illustrative, not a recommendation)."""
    if s["assetClass"] in p.excluded_classes or (s["assetClass"] == "crypto" and p.max_crypto == 0):
        return 0.0
    if p.esg and (s["esgScreen"] == "exclude_candidate" or (p.avoid_controversy and s["esgScreen"] == "watch")):
        return 0.0
    cap = p.max_fund if is_fund(s) else (p.max_crypto if s["assetClass"] == "crypto" else p.max_single)
    if (s["vol3y"] or 0) > 2 * p.vol_budget and p.risk_level in ("low", "low_moderate"):
        cap = min(cap, 3.0)
    return cap


def check_narrative(text: str, facts_numbers: List[float], trace: Trace) -> bool:
    """Faithfulness check on the LLM narrative: every number must come from the fact sheet; no advice wording."""
    t = norm(text)
    bad_words = [w for w in ADVICE_WORDS if norm(w) in t]
    nums = []
    for m in re.finditer(r"(?<![\w.])[-−]?\d+(?:[ \u202f\u00a0]\d{3})*(?:[.,]\d+)?", text):
        raw = m.group(0).replace("−", "-").replace(" ", "").replace("\u202f", "").replace("\u00a0", "").replace(",", ".")
        try:
            nums.append(float(raw))
        except ValueError:
            pass
    allowed = set()
    for x in facts_numbers:
        for v in (x, -x, abs(x)):
            allowed.update({round(v, 0), round(v, 1), round(v, 2)})
    unknown = [n for n in nums if not (round(n, 2) in allowed or round(n, 1) in allowed or round(n, 0) in allowed or (n.is_integer() and 0 <= n <= 5) or 1990 <= n <= 2030)]
    ok = not bad_words and not unknown
    trace.check(AGENT_ID, "narrative_faithfulness", "pass" if ok else "warn",
                "Texte généré vérifié : chaque chiffre provient de la fiche de faits, aucun langage de conseil." if ok else
                f"Texte généré rejeté ({'chiffres non traçables : ' + ', '.join(str(n) for n in unknown[:5]) if unknown else ''}"
                f"{' ; termes interdits : ' + ', '.join(bad_words) if bad_words else ''}); texte déterministe utilisé à la place.")
    return ok
