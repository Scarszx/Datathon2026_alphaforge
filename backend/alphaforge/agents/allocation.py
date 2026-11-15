"""AllocationAgent: proposes a FICTITIOUS, rules-based allocation that satisfies the policy.

Why it exists: it is the only component that turns a policy into weights, with a method simple enough to
explain in one sentence: "pick eligible assets per pocket by profile fit (never by past return), weight them by
inverse volatility, cap concentration, then shift weight to the defensive pocket until the historical
volatility fits the budget". Each exclusion and each rebalancing iteration is logged as a decision.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .. import metrics as M
from ..data import DataStore
from ..trace import Trace
from .profile import Policy

AGENT_ID = "allocation"
CORE_FUNDS = ["XIU.TO", "VFV.TO", "XEF.TO", "XEC.TO", "XESG.TO"]
GROWTH_SECTORS = {"Information Technology", "Communication Services", "Growth / Technology"}
SATELLITE_K = {"low": 3, "low_moderate": 4, "moderate": 6, "high": 7}
# Team-curated theme tag: companies whose latest 10-K (Item 1, Business) describes AI products as a core offering
# (data-centre GPUs/accelerators, AI cloud platforms). Used only as a PREFERENCE match, never as a return signal.
AI_THEME = {"NVDA", "MSFT", "GOOGL", "AMZN"}
MIN_WEIGHT = 1.0  # positions below 1 % are dropped (dust) and their weight redistributed


def pocket_of(stats: dict) -> str:
    c = stats["assetClass"]
    if c in ("etf_bond", "etf_gold"):
        return "defensive"
    if c == "crypto":
        return "crypto"
    if stats["ticker"] in CORE_FUNDS:
        return "core"
    return "satellite"


def is_fund(stats: dict) -> bool:
    return stats["assetClass"].startswith("etf")


def eligible(stats: Dict[str, dict], p: Policy, trace: Trace) -> Dict[str, dict]:
    out = {}
    for t, s in stats.items():
        reason = None
        if s["assetClass"] in p.excluded_classes or (s["assetClass"] == "equity" and "equity" in p.excluded_classes):
            reason = f"classe d'actifs exclue par le profil ({s['assetClass']})"
        elif s["assetClass"] == "crypto" and p.max_crypto == 0:
            reason = "crypto hors politique (non demandée, spéculative ou horizon court)"
        elif p.esg and s["esgScreen"] == "exclude_candidate":
            reason = f"filtre ESG : activité {', '.join(s['esgTags']) or 'controversée'}"
        elif p.avoid_controversy and s["esgScreen"] == "watch":
            reason = f"profil qui évite les controverses : titre sous surveillance ({', '.join(s['esgTags'])})"
        elif p.esg and t == "XIU.TO" and "XESG.TO" in stats:
            reason = "préférence ESG : remplacé par XESG.TO (même marché canadien, filtre ESG MSCI)"
        elif p.no_speculative and pocket_of(s) == "satellite" and (s["vol3y"] or 0) > 45:
            reason = f"profil non spéculatif : volatilité 3 ans de {s['vol3y']:.0f} % > 45 %"
        elif p.established_only and pocket_of(s) == "satellite" and ((s["vol3y"] or 99) >= 30 or not s["dividendYield"]):
            reason = f"sociétés établies seulement : volatilité 3 ans {s['vol3y']:.0f} % ou aucun dividende versé"
        elif s["stale"]:
            reason = "cours ancien (plus de 5 jours) : donnée insuffisante"
        if reason:
            trace.decide(AGENT_ID, f"Exclure {t}", reason)
        else:
            out[t] = s
    return out


def fit_score(s: dict, p: Policy) -> float:
    sc = 0.0
    if "tech" in p.tilts and (s["sector"] in GROWTH_SECTORS):
        sc += 2
        if s["ticker"] in AI_THEME:
            sc += 1
    if "dividend" in p.tilts and (s["dividendYield"] or 0) >= 2:
        sc += 2
    if "low_vol" in p.tilts and (s["vol3y"] or 99) < 25:
        sc += 1
    if "esg" in p.tilts:
        sc += {"leader": 2, "neutral": 0, "watch": -1}.get(s["esgScreen"], 0)
    if "fossil_fuel_financing" in s["esgTags"] and p.esg:
        sc -= 0.5
    return sc


def _inv_vol(items: List[dict]) -> Dict[str, float]:
    iv = {s["ticker"]: 1 / max(s["vol3y"] or 20, 1) for s in items}
    tot = sum(iv.values())
    return {t: v / tot for t, v in iv.items()}


def _cap(weights: Dict[str, float], caps: Dict[str, float]) -> Dict[str, float]:
    """Iteratively cap weights and redistribute the excess pro rata to uncapped names (same pocket)."""
    w = dict(weights)
    for _ in range(20):
        over = {t: w[t] - caps[t] for t in w if w[t] > caps[t] + 1e-9}
        if not over:
            break
        free = [t for t in w if w[t] < caps[t] - 1e-9 and t not in over]
        excess = sum(over.values())
        for t in over:
            w[t] = caps[t]
        if not free:
            break
        tot = sum(w[t] for t in free)
        for t in free:
            w[t] += excess * w[t] / tot
    return w


def portfolio_stats(weights: Dict[str, float], store: DataStore) -> dict:
    cal = store.calendar
    import datetime as dt
    y3 = (dt.date.fromisoformat(store.as_of) - dt.timedelta(days=3 * 365)).isoformat()
    y1 = (dt.date.fromisoformat(store.as_of) - dt.timedelta(days=365)).isoformat()
    w = {t: v / 100 for t, v in weights.items() if v > 0}
    series = {t: store.cad_series(t) for t in w}
    vals = M.portfolio_values(w, series)
    v3 = M.window(vals, cal, y3)
    v1 = M.window(vals, cal, y1)
    rets = M.returns(vals)
    rc = M.risk_contributions(w, {t: M.window(series[t], cal, y3) for t in w})
    return {
        "vol1y": M.r2(M.vol(M.returns(v1))), "vol3y": M.r2(M.vol(M.returns(v3))), "vol5y": M.r2(M.vol(rets)),
        "maxDrawdown5y": M.r2(M.max_drawdown(vals)), "return2022": M.r2(M.total_return(M.window(vals, cal, "2022-01-01", "2022-12-31"))),
        "var95_1d": M.r2(M.hist_var(M.returns(v3))), "effectiveN": M.r2(M.effective_n(w), 1),
        "riskContributions": {t: M.r2(v, 1) for t, v in sorted(rc.items(), key=lambda x: -x[1])},
        "index": [{"date": d, "value": round(v, 2)} for d, v in zip(cal[::5], vals[::5])],
    }


def exposures(weights: Dict[str, float], stats: Dict[str, dict]) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    by_pocket, by_sector, by_ccy = {}, {}, {}
    for t, w in weights.items():
        s = stats[t]
        by_pocket[pocket_of(s)] = by_pocket.get(pocket_of(s), 0) + w
        by_sector[s["sector"]] = by_sector.get(s["sector"], 0) + w
        by_ccy[s["currency"]] = by_ccy.get(s["currency"], 0) + w
    rnd = lambda d: {k: round(v, 2) for k, v in sorted(d.items(), key=lambda x: -x[1])}  # noqa: E731
    return rnd(by_pocket), rnd(by_sector), rnd(by_ccy)


def growth_share(weights: Dict[str, float], stats: Dict[str, dict]) -> float:
    return sum(w for t, w in weights.items() if stats[t]["sector"] in GROWTH_SECTORS)


def propose(stats: Dict[str, dict], p: Policy, store: DataStore, trace: Trace) -> dict:
    with trace.step(AGENT_ID, "screen_universe", {"universe": len(stats)}) as st:
        el = eligible(stats, p, trace)
        st["output"] = {"eligible": len(el), "excluded": len(stats) - len(el)}
    with trace.step(AGENT_ID, "build_pockets", {"buckets": p.buckets, "method": "fit_score puis volatilité inverse"}) as st:
        pockets: Dict[str, List[dict]] = {"defensive": [], "core": [], "satellite": [], "crypto": []}
        for s in el.values():
            pockets[pocket_of(s)].append(s)
        k = SATELLITE_K[p.risk_level]
        sat = sorted(pockets["satellite"], key=lambda s: (-fit_score(s, p), s["vol3y"] or 99))
        chosen, per_sector = [], {}
        for s in sat:  # diversification: at most 2 single names per sector (3 for a sector the profile explicitly favours)
            limit = 3 if ("tech" in p.tilts and s["sector"] in GROWTH_SECTORS and p.risk_level == "high") else 2
            if per_sector.get(s["sector"], 0) >= limit:
                continue
            chosen.append(s)
            per_sector[s["sector"]] = per_sector.get(s["sector"], 0) + 1
            if len(chosen) >= k:
                break
        pockets["satellite"] = chosen
        if "tech" in p.tilts and "QQQ" in el and el["QQQ"] not in chosen and p.risk_level == "high":
            pockets["satellite"].append(el["QQQ"])
        weights: Dict[str, float] = {}
        target = dict(p.buckets)
        empty = [b for b, items in pockets.items() if target.get(b, 0) > 0 and not items]
        for b in empty:  # pocket without eligible asset -> its weight goes to core (or defensive)
            dest = "core" if pockets["core"] else "defensive"
            target[dest] += target[b]
            trace.decide(AGENT_ID, f"Poche {b} vide → {dest}", "Aucun actif admissible dans cette poche après filtrage.")
            target[b] = 0
        for b, items in pockets.items():
            if not target.get(b):
                continue
            if b == "satellite" and p.risk_level == "high":
                iv = {s["ticker"]: 1 / len(items) for s in items}  # equal weight: inverse-vol would tilt a growth profile to its least volatile names
            else:
                iv = _inv_vol(items)
            caps = {t: (p.max_fund if is_fund(el[t]) else (p.max_crypto if b == "crypto" else p.max_single)) / target[b] for t in iv}
            iv = _cap(iv, {t: min(1.0, c) for t, c in caps.items()})
            for t, w in iv.items():
                weights[t] = weights.get(t, 0) + w * target[b]
        leftover = 100 - sum(weights.values())
        if leftover > 0.05:  # caps left part of a pocket unallocated -> diversified funds (core, then defensive)
            sink = [t for t in weights if pocket_of(el[t]) in ("core", "defensive")]
            tot = sum(weights[t] for t in sink)
            for t in sink:
                weights[t] += leftover * weights[t] / tot
            trace.decide(AGENT_ID, f"Réaffecter {leftover:.1f} points aux fonds diversifiés",
                         "Les plafonds par titre empêchaient d'allouer toute la poche avec les titres admissibles.")
        st["output"] = {b: [s["ticker"] for s in items] for b, items in pockets.items()}
        trace.claim("Sélection par adéquation au profil (secteur, dividende, filtre ESG, volatilité), jamais par rendement passé; "
                    "pondération par volatilité inverse sur 3 ans" + (" (poids égaux dans la poche satellite d'un profil à risque élevé)." if p.risk_level == "high" else "."),
                    "assumption", agent_id=AGENT_ID)

    # Growth-sector cap (Amira: "not 100 % tech")
    g = growth_share(weights, stats)
    if g > p.max_sector:
        with trace.step(AGENT_ID, "cap_sector", {"sector": "technologie / croissance", "cap": p.max_sector}) as st:
            scale = p.max_sector / g
            freed = 0.0
            for t in list(weights):
                if stats[t]["sector"] in GROWTH_SECTORS:
                    nw = weights[t] * scale
                    freed += weights[t] - nw
                    weights[t] = nw
            core = [t for t in weights if pocket_of(stats[t]) == "core"] or [t for t in weights if pocket_of(stats[t]) == "defensive"]
            tot = sum(weights[t] for t in core)
            for t in core:
                weights[t] += freed * weights[t] / tot
            trace.decide(AGENT_ID, f"Plafonner techno/croissance à {p.max_sector:.0f} %",
                         f"Exposition de {g:.1f} % avant plafond; {freed:.1f} points réaffectés aux fonds indiciels diversifiés.")
            st["output"] = {"before": round(g, 1), "after": round(growth_share(weights, stats), 1)}

    # Risk-budget loop: shift 5 points to defensive until historical vol (3y) fits the budget
    defensive = [t for t in weights if pocket_of(stats[t]) == "defensive"]
    for it in range(10):
        ps = portfolio_stats(weights, store)
        if ps["vol3y"] is None or ps["vol3y"] <= p.vol_budget or not defensive:
            break
        with trace.step(AGENT_ID, "rebalance_to_risk_budget", {"iteration": it + 1, "vol3y": ps["vol3y"], "budget": p.vol_budget}):
            risky = [t for t in weights if pocket_of(stats[t]) in ("satellite", "crypto")] or \
                    [t for t in weights if pocket_of(stats[t]) == "core"]
            tot_r = sum(weights[t] for t in risky)
            move = min(5.0, tot_r)
            for t in risky:
                weights[t] -= move * weights[t] / tot_r
            tot_d = sum(weights[t] for t in defensive)
            for t in defensive:
                weights[t] += move * weights[t] / tot_d
            trace.decide(AGENT_ID, f"Itération {it + 1} : 5 points du satellite vers le défensif",
                         f"Volatilité historique 3 ans {ps['vol3y']:.1f} % > budget {p.vol_budget:.0f} %.")
    else:
        ps = portfolio_stats(weights, store)

    dust = {t: w for t, w in weights.items() if w < MIN_WEIGHT}
    if dust:
        for t, w in dust.items():  # redistribute inside the same pocket so pocket targets stay intact
            del weights[t]
            same = [x for x in weights if pocket_of(stats[x]) == pocket_of(stats[t])] or list(weights)
            tot = sum(weights[x] for x in same)
            for x in same:
                weights[x] += w * weights[x] / tot
        trace.decide(AGENT_ID, f"Retirer les lignes < {MIN_WEIGHT:.0f} % : {', '.join(dust)}", "Positions trop petites pour avoir un effet; poids redistribué au prorata.")
    weights = {t: round(w, 2) for t, w in sorted(weights.items(), key=lambda x: -x[1])}
    ps = portfolio_stats(weights, store)
    pk, sec, ccy = exposures(weights, stats)
    return {
        "weights": [{"ticker": t, "name": stats[t]["name"], "weight": w, "pocket": pocket_of(stats[t]), "assetClass": stats[t]["assetClass"],
                     "sector": stats[t]["sector"], "vol3y": stats[t]["vol3y"], "esgScreen": stats[t]["esgScreen"],
                     "why": _why(stats[t], p)} for t, w in weights.items()],
        "byPocket": pk, "bySector": sec, "byCurrency": ccy, "stats": ps,
        "growthShare": round(growth_share(weights, stats), 2),
        "_weights": weights,
    }


def _why(s: dict, p: Policy) -> str:
    pk = pocket_of(s)
    bits = {"defensive": "stabilisateur (obligations / or)", "core": "fonds indiciel diversifié", "satellite": "titre ou thème choisi pour le profil",
            "crypto": "exposition crypto plafonnée"}[pk]
    extra = []
    if "tech" in p.tilts and s["sector"] in GROWTH_SECTORS:
        extra.append("préférence techno/IA")
    if "dividend" in p.tilts and (s["dividendYield"] or 0) >= 2:
        extra.append(f"dividende {s['dividendYield']:.1f} %")
    if p.esg and s["esgScreen"] == "leader":
        extra.append("fonds à filtre ESG")
    if "low_vol" in p.tilts and (s["vol3y"] or 99) < 25 and pk == "satellite":
        extra.append(f"volatilité 3 ans {s['vol3y']:.0f} %")
    return bits + (" · " + ", ".join(extra) if extra else "")


def with_request(base: Dict[str, float], ticker: str, pct: float) -> Dict[str, float]:
    """Variant: the requested asset at `pct` %, the rest of the base allocation scaled to (100 - pct)."""
    rest = {t: w for t, w in base.items() if t != ticker}
    tot = sum(rest.values())
    out = {t: w * (100 - pct) / tot for t, w in rest.items()}
    out[ticker] = pct
    return out
