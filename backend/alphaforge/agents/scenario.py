"""ScenarioAgent: EXPERIENCE. Stress-tests a set of weights with two kinds of scenarios, clearly separated:

  historical (fact)   - replays what each asset really did in a past window of the dataset;
  hypothetical        - applies shocks WE chose (every parameter shown), with a sensitivity multiplier.

Why it exists: volatility alone does not tell a 59-year-old with a 3-year horizon what a bad year looks like.
Scenarios translate risk into a loss in dollars and show how much the conclusion depends on the hypothesis.
"""
from __future__ import annotations

from typing import Dict, List

from .. import metrics as M
from ..data import DataStore
from ..trace import Trace
from .allocation import GROWTH_SECTORS

AGENT_ID = "scenario"

# Modified duration assumptions (years), rounded from issuer fact sheets (iShares XBB ~7, XSB ~2.6).
DURATION = {"XBB.TO": 7.0, "XSB.TO": 2.6}

HYPOTHETICAL = {
    "rates_up_200": {
        "label": "Hausse des taux de 2 points (hypothèse)",
        "description": "Taux obligataires +2 points d'un coup; actions de croissance plus touchées (valorisation sensible aux taux).",
        "shocks": {"bond": "−durée × 2 %", "equity": -10.0, "growth": -18.0, "utilities": -12.0, "gold": -5.0, "crypto": -25.0},
    },
    "tech_crash": {
        "label": "Krach techno / IA de 35 % (hypothèse)",
        "description": "Repli marqué des titres technologiques et de croissance, contagion partielle au reste du marché, fuite vers la qualité.",
        "shocks": {"bond": 2.0, "equity": -12.0, "growth": -35.0, "utilities": -5.0, "gold": 5.0, "crypto": -50.0},
    },
}


def _shock_for(t: str, s: dict, shocks: dict) -> float:
    c = s["assetClass"]
    if c == "etf_bond":
        return -DURATION.get(t, 5.0) * 2.0 if isinstance(shocks["bond"], str) else shocks["bond"]
    if c == "etf_gold":
        return shocks["gold"]
    if c == "crypto":
        return shocks["crypto"]
    if s["sector"] in GROWTH_SECTORS:
        return shocks["growth"]
    if s["sector"] == "Utilities":
        return shocks["utilities"]
    return shocks["equity"]


def _crypto_winter(store: DataStore) -> tuple:
    s = store.cad_series("BTC-USD") if "BTC-USD" in store.prices else None
    if not s:
        return None
    cal = store.calendar
    idx = [i for i, d in enumerate(cal) if "2022-01-01" <= d <= "2022-12-31"]
    i_min = min(idx, key=lambda i: s[i])
    return cal[0], cal[i_min]


def historical_windows(store: DataStore) -> List[dict]:
    w = [{"id": "hist_2022", "label": "Année 2022 : actions et obligations en baisse ensemble (historique)",
          "start": "2022-01-01", "end": "2022-12-31"}]
    cw = _crypto_winter(store)
    if cw:
        w.append({"id": "hist_crypto_winter", "label": f"Hiver crypto {cw[0][:7]} → {cw[1][:7]} (historique)", "start": cw[0], "end": cw[1]})
    return w


def run(weights: Dict[str, float], stats: Dict[str, dict], store: DataStore, trace: Trace, value: float = 100_000.0,
        scale: float = 1.0) -> List[dict]:
    out = []
    cal = store.calendar
    with trace.step(AGENT_ID, "replay_historical_windows", {"windows": [w["id"] for w in historical_windows(store)]}) as st:
        for w in historical_windows(store):
            contrib, missing = {}, []
            for t, wt in weights.items():
                r = M.total_return(M.window(store.cad_series(t), cal, w["start"], w["end"]))
                if r != r:
                    missing.append(t)
                    r = 0.0
                contrib[t] = wt / 100 * r
            pr = sum(contrib.values())
            out.append({"id": w["id"], "kind": "historical", "label": w["label"], "window": [w["start"], w["end"]],
                        "portfolioReturn": round(pr, 2), "pnl": round(value * pr / 100, 0),
                        "contributions": {t: round(v, 2) for t, v in sorted(contrib.items(), key=lambda x: x[1])[:5]},
                        "missing": missing})
            if missing:
                trace.uncertain(f"{w['label']} : pas d'historique pour {', '.join(missing)} (rendement 0 supposé).")
        st["output"] = {o["id"]: o["portfolioReturn"] for o in out}
    trace.assume("Scénarios historiques : poids constants pendant la fenêtre, sans frais ni impôts; rendements en CAD sur cours ajustés.")

    with trace.step(AGENT_ID, "apply_hypothetical_shocks", {"scenarios": list(HYPOTHETICAL), "scale": scale}) as st:
        for sid, sc in HYPOTHETICAL.items():
            contrib = {t: wt / 100 * _shock_for(t, stats[t], sc["shocks"]) * scale for t, wt in weights.items()}
            pr = sum(contrib.values())
            sens = {str(k): round(sum(wt / 100 * _shock_for(t, stats[t], sc["shocks"]) * k for t, wt in weights.items()), 2)
                    for k in (0.5, 1.0, 1.5)}
            out.append({"id": sid, "kind": "hypothetical", "label": sc["label"], "description": sc["description"],
                        "parameters": sc["shocks"], "scale": scale, "portfolioReturn": round(pr, 2), "pnl": round(value * pr / 100, 0),
                        "sensitivity": sens,
                        "contributions": {t: round(v, 2) for t, v in sorted(contrib.items(), key=lambda x: x[1])[:5]}})
        st["output"] = {o["id"]: o["portfolioReturn"] for o in out if o["kind"] == "hypothetical"}
    trace.assume("Scénarios hypothétiques : chocs instantanés choisis par l'équipe (paramètres affichés); obligations : variation ≈ −durée × variation de taux, "
                 "durées XBB ≈ 7 ans et XSB ≈ 2,6 ans arrondies des fiches iShares.")
    trace.limit("Les scénarios ne sont pas des probabilités : ils illustrent une ampleur de perte possible, pas sa fréquence.")
    return out


def lookback_sensitivity(pstats: dict, trace: Trace) -> dict:
    v = [pstats.get(k) for k in ("vol1y", "vol3y", "vol5y")]
    vv = [x for x in v if x]
    ratio = max(vv) / min(vv) if len(vv) == 3 and min(vv) > 0 else None
    res = {"vol1y": v[0], "vol3y": v[1], "vol5y": v[2], "ratio": round(ratio, 2) if ratio else None}
    if ratio and ratio > 1.4:
        trace.uncertain(f"La volatilité estimée dépend fortement de la fenêtre (1 an {v[0]} %, 3 ans {v[1]} %, 5 ans {v[2]} %) : "
                        "l'estimation du risque est incertaine.")
    return res
