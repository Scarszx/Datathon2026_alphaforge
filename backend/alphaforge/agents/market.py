"""MarketDataAgent: SELECT and CONNECT. Reads only the public dataset; computes descriptive statistics.

Why it exists: every other agent needs the same, point-in-time, CAD-comparable numbers. Centralising them
means one place to audit (sources, dates, transformation) and no agent can quietly use another dataset.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Dict, List, Optional

from .. import metrics as M
from ..data import DataStore
from ..trace import Trace

AGENT_ID = "market-data"
_cache: Dict[str, dict] = {}


def _shift(d: str, days: int) -> str:
    return (dt.date.fromisoformat(d) + dt.timedelta(days=days)).isoformat()


def _recovery(values: List[float], cal: List[str]) -> dict:
    """Max drawdown with peak / trough dates and recovery date (None if not recovered by as_of)."""
    peak_v, peak_d, best = -math.inf, None, (0.0, None, None)
    for v, d in zip(values, cal):
        if v != v:
            continue
        if v > peak_v:
            peak_v, peak_d = v, d
        dd = v / peak_v - 1
        if dd < best[0]:
            best = (dd, peak_d, d)
    dd, pk, tr = best
    rec = None
    if tr:
        ref = values[cal.index(pk)]
        for v, d in zip(values[cal.index(tr):], cal[cal.index(tr):]):
            if v == v and v >= ref:
                rec = d
                break
    days = (dt.date.fromisoformat(rec) - dt.date.fromisoformat(tr)).days if rec and tr else None
    return {"maxDrawdown": M.r2(dd * 100), "peakDate": pk, "troughDate": tr, "recoveryDate": rec, "recoveryDays": days}


def asset_stats(store: DataStore) -> Dict[str, dict]:
    key = f"{store.origin}:{store.as_of}"
    if key in _cache:
        return _cache[key]
    cal, as_of = store.calendar, store.as_of
    y1, y3 = _shift(as_of, -365), _shift(as_of, -3 * 365)
    out = {}
    for t, a in store.assets.items():
        if t not in store.prices:
            continue
        s = store.cad_series(t)
        r_all = M.returns(s)
        r1 = M.returns(M.window(s, cal, y1))
        r3 = M.returns(M.window(s, cal, y3))
        first = store.prices[t][0][0]
        years = (dt.date.fromisoformat(as_of) - dt.date.fromisoformat(max(first, cal[0]))).days / 365.25
        lp = store.last_price(t)
        div = store.trailing_dividends(t)
        out[t] = {
            "ticker": t, "name": a.name, "assetClass": a.asset_class, "sector": a.sector, "currency": a.currency,
            "esgScreen": a.esg_screen, "esgTags": a.esg_tags,
            "firstDate": first, "lastDate": lp["date"] if lp else None, "stale": bool(lp and lp["stale"]),
            "lastClose": lp["close"] if lp else None,
            "vol1y": M.r2(M.vol(r1)), "vol3y": M.r2(M.vol(r3)), "vol5y": M.r2(M.vol(r_all)),
            "return1y": M.r2(M.total_return(M.window(s, cal, y1))),
            "return5y": M.r2(M.total_return(s)), "cagr5y": M.r2(M.cagr(s, years)),
            "return2022": M.r2(M.total_return(M.window(s, cal, "2022-01-01", "2022-12-31"))),
            "var95_1d": M.r2(M.hist_var(r3)),
            "worstDay": M.r2(min((x for x in r_all if x == x), default=float("nan")) * 100),
            "dividendYield": M.r2(div / lp["close"] * 100) if lp and lp["close"] and div else 0.0,
            **_recovery(s, cal),
        }
    xiu = M.returns(store.cad_series("XIU.TO")) if "XIU.TO" in store.prices else None
    for t in out:
        out[t]["corrTSX"] = M.r2(M.corr(M.returns(store.cad_series(t)), xiu)) if xiu else None
    _cache[key] = out
    return out


MACRO_IDS = ["V39079", "BD.CDN.2YR.DQ.YLD", "BD.CDN.10YR.DQ.YLD", "STATIC_TOTALCPICHANGE", "DFF", "DGS10", "UNRATE"]


def macro_snapshot(store: DataStore, trace: Trace) -> dict:
    with trace.step(AGENT_ID, "read_macro_series", {"series": MACRO_IDS, "asOf": store.as_of}) as st:
        snap = {}
        for sid in MACRO_IDS:
            m = store.macro_as_of(sid)
            if m:
                snap[sid] = m
        c10, c2 = snap.get("BD.CDN.10YR.DQ.YLD"), snap.get("BD.CDN.2YR.DQ.YLD")
        if c10 and c2:
            snap["CA_10Y_2Y"] = {"id": "CA_10Y_2Y", "label": "Pente de la courbe Canada (10 ans − 2 ans)",
                                  "value": round(c10["value"] - c2["value"], 2), "unit": "percent", "date": c10["date"],
                                  "source": "dérivée"}
        st["output"] = {k: v["value"] for k, v in snap.items()}
    trace.source("macro", "macro_rates.csv", store.as_of,
                 "Banque du Canada (Valet) et FRED; séries mensuelles visibles 45 jours après le mois de référence")
    return snap


def load_universe(store: DataStore, trace: Trace) -> Dict[str, dict]:
    with trace.step(AGENT_ID, "compute_asset_statistics", {"assets": len(store.assets), "asOf": store.as_of,
                                                          "currency": "CAD", "windows": ["1y", "3y", "5y"]}) as st:
        stats = asset_stats(store)
        st["output"] = {"assets": len(stats), "stale": [t for t, s in stats.items() if s["stale"]]}
    trace.source("prices", "prices_daily.csv", store.as_of,
                 f"Cours ajustés (dividendes et splits), {store.calendar[0]} → {store.as_of}, convertis en CAD")
    trace.source("fx", "fx_usdcad_daily.csv", store.as_of, "Banque du Canada, FXUSDCAD, dernier taux connu reporté")
    trace.source("universe", "assets_universe.csv", store.as_of, "31 actifs; filtre ESG d'activités (sélection de l'équipe)")
    trace.assume("Les rendements sont calculés en CAD sur cours ajustés (dividendes réinvestis), calendrier des jours ouvrables de la Banque du Canada.")
    trace.limit("Univers restreint à 31 actifs connus et toujours cotés : biais du survivant, pas de petites capitalisations.")
    trace.limit("Les statistiques décrivent 2021-11 → 2026-11, une seule période de marché (dont 2022, où actions et obligations ont baissé ensemble). Elles ne prédisent pas l'avenir.")
    stale = [t for t, s in stats.items() if s["stale"]]
    if stale:
        trace.uncertain(f"Cours ancien (plus de 5 jours) pour : {', '.join(stale)}.")
    return stats


def fundamentals(store: DataStore, ticker: str, trace: Trace) -> Optional[dict]:
    with trace.step(AGENT_ID, "read_sec_fundamentals", {"ticker": ticker, "filedOnOrBefore": store.as_of}) as st:
        f = store.fundamentals_as_of(ticker)
        if not f:
            st["status"] = "empty"
            return None
        out = {k: {"value": float(v["value"]), "periodEnd": v["period_end"], "filed": v["filed"], "accession": v["accession"]}
               for k, v in f.items()}
        # previous year revenue for growth (also as-filed)
        prev = [r for r in store.fundamentals.get(ticker, []) if r["metric"] == "revenue" and r["filed"] <= store.as_of]
        prev.sort(key=lambda r: r["period_end"])
        if len(prev) >= 2:
            out["revenueGrowth"] = {"value": round((float(prev[-1]["value"]) / float(prev[-2]["value"]) - 1) * 100, 1),
                                    "periodEnd": prev[-1]["period_end"], "filed": prev[-1]["filed"]}
        if "revenue" in out and "net_income" in out:
            out["netMargin"] = {"value": round(out["net_income"]["value"] / out["revenue"]["value"] * 100, 1),
                                "periodEnd": out["revenue"]["periodEnd"], "filed": out["revenue"]["filed"]}
        st["output"] = {k: v["value"] for k, v in out.items()}
    trace.source(f"sec:{ticker}", "fundamentals_sec.csv", out["revenue"]["filed"] if "revenue" in out else store.as_of,
                 f"SEC EDGAR 10-K de {ticker}, valeurs telles que déposées (date de dépôt = date de disponibilité)")
    return out


def news_attention(store: DataStore, ticker: str, trace: Trace) -> Optional[dict]:
    with trace.step(AGENT_ID, "read_news_attention", {"ticker": ticker, "source": "GDELT"}) as st:
        n = store.news_attention(ticker)
        if not n:
            st["status"] = "empty"
            return None
        st["output"] = {k: v for k, v in n.items() if k != "series"}
    trace.source("news", "news_attention.csv", n["window"][1],
                 "GDELT Project, part des articles de presse anglophones mentionnant le nom (attention médiatique, pas un sentiment)")
    return n
