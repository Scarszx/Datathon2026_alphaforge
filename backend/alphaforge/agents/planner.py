"""Planner (coordinator front door): reads the question and decides which agents run, in which order.

Deterministic on purpose: routing must be reproducible and testable in front of a jury. The plan is part of the trace.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from ..data import DataStore
from .profile import norm

AGENT_ID = "planner"

ALIASES = {
    "nvidia": "NVDA", "tesla": "TSLA", "apple": "AAPL", "microsoft": "MSFT", "amazon": "AMZN", "google": "GOOGL", "alphabet": "GOOGL",
    "bitcoin": "BTC-USD", "btc": "BTC-USD", "ether": "ETH-USD", "ethereum": "ETH-USD", "eth": "ETH-USD", "shopify": "SHOP.TO",
    "rbc": "RY.TO", "banque royale": "RY.TO", "royal bank": "RY.TO", "banque td": "TD.TO", "enbridge": "ENB.TO", "suncor": "SU.TO",
    "canadien national": "CNR.TO", "cn rail": "CNR.TO", "constellation": "CSU.TO", "bce": "BCE.TO", "bell": "BCE.TO",
    "couche-tard": "ATD.TO", "couche tard": "ATD.TO", "fortis": "FTS.TO", "johnson": "JNJ", "procter": "PG", "p&g": "PG",
    "jpmorgan": "JPM", "jp morgan": "JPM", "exxon": "XOM", "nasdaq": "QQQ", "l'or": "GLD", "gold": "GLD",
    "s&p 500": "VFV.TO", "s&p500": "VFV.TO", "tsx": "XIU.TO",
}

INTENT_WORDS = {
    "compare": ["compar", " vs ", "versus", " ou bien ", "difference entre"],
    "scenario": ["scenario", "et si ", "what if", "krach", "crash", "hausse des taux", "taux montent", "recession", "stress", "choc"],
    "portfolio": ["mon portefeuille", "my portfolio", "mes positions", "mes placements"],
    "request": ["je veux", "acheter", "investir dans", "mettre", "should i", "tente", "tempt", "miser", "placer", "que penses-tu de", "bonne idee"],
    "allocation": ["allocation", "repartition", "propose", "construis", "portefeuille fictif", "diversif", "investir", "repartir"],
}


def find_tickers(question: str, store: DataStore) -> List[str]:
    found: List[str] = []
    for m in re.finditer(r"\b([A-Z]{1,5}(?:[.-](?:TO|USD))?)\b", question):
        tok = m.group(1)
        for cand in (tok, f"{tok}.TO", f"{tok}-USD"):
            if cand in store.assets and cand not in found and tok not in ("ETF", "IA", "AI", "ESG", "USD", "CAD", "OK", "TD", "CN"):
                found.append(cand)
                break
    q = " " + norm(question) + " "
    for alias, t in ALIASES.items():
        if re.search(r"(?<![a-z])" + re.escape(norm(alias)) + r"(?![a-z])", q) and t not in found:
            found.append(t)
    return found


def find_percent(question: str) -> Optional[float]:
    m = re.search(r"(\d{1,3}(?:[.,]\d+)?)\s*(?:%|pour ?cent|percent)", question)
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    return v if 0 < v <= 100 else None


def plan(question: str, store: DataStore) -> Dict:
    q = " " + norm(question) + " "
    tickers = find_tickers(question, store)
    pct = find_percent(question)
    hit = {k: any(w in q for w in ws) for k, ws in INTENT_WORDS.items()}
    if hit["portfolio"] and not tickers:
        intent = "portfolio"
    elif len(tickers) >= 2 and (hit["compare"] or not hit["request"]):
        intent = "compare"
    elif tickers:
        intent = "request"
    elif hit["scenario"]:
        intent = "scenario"
    else:
        intent = "allocation"
    agents = {
        "allocation": ["investor-profile", "market-data", "allocation", "scenario", "governance", "explainability"],
        "request": ["investor-profile", "market-data", "allocation", "governance", "scenario", "explainability"],
        "compare": ["investor-profile", "market-data", "governance", "explainability"],
        "scenario": ["investor-profile", "market-data", "allocation", "scenario", "governance", "explainability"],
        "portfolio": ["investor-profile", "market-data", "scenario", "governance", "explainability"],
    }[intent]
    return {"intent": intent, "tickers": tickers, "percent": pct, "agents": agents}
