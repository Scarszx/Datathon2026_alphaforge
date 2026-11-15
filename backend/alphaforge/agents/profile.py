"""InvestorProfileAgent: CONTEXTUALISE. Turns a (fictional) investor profile into an explicit, inspectable policy.

Why it exists: "adapt to context" must be visible and testable. Every threshold below is an ASSUMPTION of
ours, written in plain language in the trace, so the user can see why Amira and Robert get different answers.
"""
from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from ..trace import Trace

AGENT_ID = "investor-profile"

# risk level -> (annualised vol budget %, historical drawdown tolerance %, buckets, max single security %)
RISK_TABLE = {
    "low":          (5.0, 12.0, {"defensive": 70, "core": 25, "satellite": 5, "crypto": 0}, 4.0),
    "low_moderate": (7.0, 18.0, {"defensive": 55, "core": 35, "satellite": 10, "crypto": 0}, 5.0),
    "moderate":     (10.0, 28.0, {"defensive": 35, "core": 45, "satellite": 20, "crypto": 0}, 6.0),
    "high":         (16.0, 45.0, {"defensive": 10, "core": 42, "satellite": 40, "crypto": 8}, 8.0),
}
RISK_LABEL = {"low": "faible", "low_moderate": "faible à modéré", "moderate": "modéré", "high": "élevé"}
CLASS_WORDS = {"crypto": "crypto", "cryptomonnaie": "crypto", "bitcoin": "crypto", "obligation": "etf_bond", "bond": "etf_bond",
               "or": "etf_gold", "gold": "etf_gold", "action": "equity", "equity": "equity"}


def norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


@dataclass
class Policy:
    risk_level: str
    horizon_min: int
    horizon_max: Optional[int]
    vol_budget: float
    dd_tolerance: float
    buckets: Dict[str, float]
    max_single: float
    max_fund: float = 30.0
    max_sector: float = 30.0
    max_crypto: float = 0.0
    min_defensive: float = 0.0
    min_holdings: int = 8
    esg: bool = False
    avoid_controversy: bool = False
    no_speculative: bool = False
    established_only: bool = False
    wants_crypto: bool = False
    tilts: List[str] = field(default_factory=list)
    excluded_classes: List[str] = field(default_factory=list)
    profile_source: str = "user"

    def to_api(self) -> dict:
        return asdict(self)


def build_policy(profile: Optional[dict], trace: Trace, source: str = "user") -> Policy:
    with trace.step(AGENT_ID, "derive_policy", {"source": source, "riskLevel": (profile or {}).get("riskLevel")}) as st:
        if not profile:
            st["status"] = "empty"
            trace.check(AGENT_ID, "profile_present", "warn",
                        "Aucun profil investisseur : politique « modéré, 5 ans » appliquée par défaut. Complétez le profil pour une analyse adaptée.")
            profile = {"riskLevel": "moderate", "horizonMinYears": 5, "objective": "non précisé"}
        else:
            trace.check(AGENT_ID, "profile_present", "pass", "Profil investisseur fourni (fictif).")
        rl = profile.get("riskLevel") if profile.get("riskLevel") in RISK_TABLE else "moderate"
        vol_b, dd_t, buckets, max_single = RISK_TABLE[rl]
        buckets = dict(buckets)
        hmin = int(profile.get("horizonMinYears") or 0)
        hmax = profile.get("horizonMaxYears")
        text = norm(" ".join([profile.get("objective", "")] + list(profile.get("preferences") or []) + list(profile.get("constraints") or [])))
        excluded = []
        for e in profile.get("excludedAssetClasses") or []:
            for w, c in CLASS_WORDS.items():
                if w in norm(e).split() or norm(e).startswith(w):
                    excluded.append(c)
        p = Policy(rl, hmin, hmax, vol_b, dd_t, buckets, max_single, profile_source=source,
                   excluded_classes=sorted(set(excluded)))
        trace.claim(f"Risque {RISK_LABEL[rl]} → budget de volatilité annualisée ≤ {vol_b:.0f} %, baisse historique tolérée ≤ {dd_t:.0f} %, "
                    f"poches cibles défensive {buckets['defensive']} % / cœur {buckets['core']} % / satellite {buckets['satellite']} % / crypto {buckets['crypto']} %.",
                    "assumption", agent_id=AGENT_ID)

        p.esg = any(k in text for k in ("esg", "durable", "responsable", "sustainab"))
        p.avoid_controversy = "controvers" in text
        p.no_speculative = "specul" in text
        p.established_only = any(k in text for k in ("etabli", "comprehensible", "established"))
        p.wants_crypto = "crypto" in text and "crypto" not in p.excluded_classes
        if any(k in text for k in (" ia", "ia ", "tech", "technolog", " ai ")):
            p.tilts.append("tech")
        if "dividend" in text:
            p.tilts.append("dividend")
        if any(k in text for k in ("stabil", "preserv")):
            p.tilts.append("low_vol")
        if p.esg:
            p.tilts.append("esg")

        # Horizon rules
        if hmin < 5:
            move = 10
            take = min(move, buckets["satellite"] / 2)  # keep some room for "un peu de croissance"
            buckets["satellite"] -= take
            buckets["core"] -= move - take
            buckets["defensive"] += move
            trace.decide(AGENT_ID, "Poche défensive +10 points", f"Horizon court ({hmin} ans < 5) : moins de temps pour se remettre d'une baisse.")
        if p.no_speculative or "crypto" in p.excluded_classes or hmin < 5 or not p.wants_crypto:
            if buckets["crypto"]:
                buckets["satellite"] += buckets["crypto"]
                trace.decide(AGENT_ID, "Poche crypto → satellite", "Crypto non demandée, exclue, spéculative ou incompatible avec l'horizon.")
            buckets["crypto"] = 0
        p.max_crypto = 10.0 if buckets["crypto"] else 0.0
        p.min_defensive = buckets["defensive"]
        if rl == "high":
            p.max_sector = 30.0
        if p.established_only:
            trace.decide(AGENT_ID, "Titres individuels limités aux sociétés établies", "Contrainte « entreprises établies et compréhensibles » : volatilité 3 ans < 30 % et dividende versé.")
        if p.esg:
            trace.decide(AGENT_ID, "Filtre ESG actif", "Préférence ESG : exclusion des activités « exclude_candidate » (extraction fossile)"
                         + (" et des titres sous surveillance (« watch ») car le profil évite les controverses." if p.avoid_controversy else "."))
        p.buckets = buckets
        st["output"] = {"buckets": buckets, "volBudget": vol_b, "tilts": p.tilts, "excluded": p.excluded_classes,
                        "esg": p.esg, "avoidControversy": p.avoid_controversy, "noSpeculative": p.no_speculative}
    trace.assume("Les seuils de la politique (budgets de volatilité, poches, plafonds de 8 % par titre et 30 % par secteur ou fonds) sont des choix "
                 "de l'équipe inspirés des pratiques de diversification courantes; ce ne sont pas des normes réglementaires.")
    return p
