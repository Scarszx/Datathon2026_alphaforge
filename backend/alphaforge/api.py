"""HTTP routes of the AlphaForge API contract v0.3.0 (+ v1.0 additions: /analysis, /personas, /data/sources).

The router is transport-agnostic: `handle()` is called by the Lambda handler (API Gateway HTTP API, JWT authorizer
on Amazon Cognito) and by the local dev server. `user` always comes from the verified token, never from the body.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import logging
import re
import uuid
from typing import Any, Dict, Optional, Tuple

from . import metrics as M
from .agents import REGISTRY
from .agents import allocation as A
from .agents import governance as G
from .agents import market as MK
from .agents import profile as PR
from .data import get_store
from .orchestrator import analyze
from .personas import PERSONAS
from .storage import get_db
from .trace import Trace

log = logging.getLogger("alphaforge.api")

CLASS_LABEL = {"equity": "Actions", "etf_equity": "FNB d'actions", "etf_bond": "FNB d'obligations", "etf_gold": "Or", "crypto": "Crypto-actifs"}
RISK_LEVELS = {"low", "low_moderate", "moderate", "high"}
DEMO_PORTFOLIOS = {
    "amira": [("QQQ", 20, 450.0), ("NVDA", 30, 120.0), ("SHOP.TO", 25, 110.0), ("BTC-USD", 0.15, 60000.0), ("VFV.TO", 40, 120.0), ("MSFT", 8, 380.0)],
    "mateo": [("XESG.TO", 300, 24.0), ("XBB.TO", 200, 27.0), ("VFV.TO", 60, 115.0), ("MSFT", 10, 350.0), ("FTS.TO", 80, 56.0), ("TSLA", 15, 240.0)],
    "robert": [("XBB.TO", 600, 27.5), ("XSB.TO", 400, 26.5), ("RY.TO", 60, 130.0), ("FTS.TO", 120, 55.0), ("ENB.TO", 150, 50.0), ("XIU.TO", 200, 31.0), ("NVDA", 40, 140.0)],
}


class HttpError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _num(v: Any, name: str, lo: float = 0, hi: float = 1e12, allow_zero: bool = True) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise HttpError(400, "VALIDATION_ERROR", f"{name} doit être un nombre.")
    if v < lo or v > hi or (not allow_zero and v == 0):
        raise HttpError(400, "VALIDATION_ERROR", f"{name} hors bornes.")
    return float(v)


def _str_list(v: Any, name: str, max_items: int = 20, max_len: int = 200) -> list:
    if v is None:
        return []
    if not isinstance(v, list) or len(v) > max_items or not all(isinstance(x, str) and len(x) <= max_len for x in v):
        raise HttpError(400, "VALIDATION_ERROR", f"{name} : liste de textes attendue (≤ {max_items}).")
    return [x.strip() for x in v if x.strip()]


def validate_profile(b: Any) -> dict:
    if not isinstance(b, dict):
        raise HttpError(400, "VALIDATION_ERROR", "Profil invalide.")
    if b.get("riskLevel") not in RISK_LEVELS:
        raise HttpError(400, "VALIDATION_ERROR", "riskLevel invalide.")
    hmin = int(_num(b.get("horizonMinYears"), "horizonMinYears", 0, 60))
    hmax = b.get("horizonMaxYears")
    if hmax is not None:
        hmax = int(_num(hmax, "horizonMaxYears", hmin, 60))
    obj = b.get("objective")
    if not isinstance(obj, str) or not obj.strip() or len(obj) > 300:
        raise HttpError(400, "VALIDATION_ERROR", "objective requis (≤ 300 caractères).")
    return {"riskLevel": b["riskLevel"], "horizonMinYears": hmin, "horizonMaxYears": hmax, "objective": obj.strip(),
            "constraints": _str_list(b.get("constraints"), "constraints"), "preferences": _str_list(b.get("preferences"), "preferences"),
            "excludedAssetClasses": _str_list(b.get("excludedAssetClasses"), "excludedAssetClasses")}


# ------------------------------------------------------------------------------------ users / bootstrap
def get_user(user: dict) -> dict:
    db = get_db()
    pk = f"USER#{user['sub']}"
    u = db.get(pk, "PROFILE")
    if u:
        return u
    uname = user.get("username") or user["sub"]
    persona = PERSONAS.get(uname.lower())
    u = {"userId": user["sub"], "username": uname, "displayName": persona["displayName"] if persona else uname, "baseCurrency": "CAD",
         "investorProfile": copy.deepcopy(persona["profile"]) if persona else None, "personaId": persona["id"] if persona else None}
    db.put(pk, "PROFILE", u)
    holdings = [{"ticker": t, "quantity": q, "avgCost": c} for t, q, c in DEMO_PORTFOLIOS.get(uname.lower(), [])]
    db.put(pk, "PORTFOLIO#main", {"portfolioId": "main", "name": "Portefeuille fictif", "baseCurrency": "CAD", "holdings": holdings, "updatedAt": now()})
    return u


def _portfolio(user: dict, pid: str) -> dict:
    get_user(user)
    p = get_db().get(f"USER#{user['sub']}", f"PORTFOLIO#{pid}")
    if not p:
        raise HttpError(404, "PORTFOLIO_NOT_FOUND", "Portefeuille introuvable.")
    return p


def _conv(user: dict, sid: str) -> dict:
    c = get_db().get(f"USER#{user['sub']}", f"CONV#{sid}")
    if not c:
        raise HttpError(404, "CONVERSATION_NOT_FOUND", "Conversation introuvable.")
    return c


# ------------------------------------------------------------------------------------ portfolio summary
def summary(user: dict, pid: str, rng: str, request_id: str) -> dict:
    if rng not in ("1m", "6m", "1y", "5y"):
        raise HttpError(400, "VALIDATION_ERROR", "range invalide (1m, 6m, 1y, 5y).")
    p = _portfolio(user, pid)
    u = get_user(user)
    store = get_store()
    trace = Trace(request_id)
    stats = MK.load_universe(store, trace)
    fx_now = store.fx_on(store.as_of)
    rows, warnings = [], []
    with trace.step("market-data", "value_holdings", {"holdings": len(p["holdings"]), "asOf": store.as_of, "usdcad": fx_now}):
        for h in p["holdings"]:
            a, lp = store.assets.get(h["ticker"]), store.last_price(h["ticker"])
            if not a or not lp:
                warnings.append(f"{h['ticker']} : aucun cours disponible.")
                continue
            fx = fx_now if a.currency == "USD" else 1.0
            value, cost = h["quantity"] * lp["close"] * fx, h["quantity"] * h["avgCost"] * fx
            rows.append({"ticker": a.ticker, "name": a.name, "assetClass": CLASS_LABEL.get(a.asset_class, a.asset_class), "quantity": h["quantity"],
                         "avgCost": h["avgCost"], "currency": a.currency, "price": lp["close"], "value": round(value, 2), "pnl": round(value - cost, 2),
                         "pnlPct": round((value / cost - 1) * 100, 2) if cost else 0.0,
                         "dayChangePct": round((lp["close"] / lp["prev_close"] - 1) * 100, 2) if lp["prev_close"] else 0.0,
                         "sector": a.sector, "stale": lp["stale"], "_cls": a.asset_class, "_prev": h["quantity"] * lp["prev_close"] * fx})
                         
            if lp["stale"]:
                warnings.append(f"{a.ticker} : dernier cours du {lp['date']} (plus de 5 jours).")
    tot = sum(r["value"] for r in rows)
    cost = sum(r["quantity"] * r["avgCost"] * (fx_now if r["currency"] == "USD" else 1) for r in rows)
    prev = sum(r["_prev"] for r in rows)
    for r in rows:
        r["weight"] = round(r["value"] / tot * 100, 2) if tot else 0.0

    def slices(key):
        d: Dict[str, float] = {}
        for r in rows:
            d[r[key]] = d.get(r[key], 0) + r["weight"]
        return [{"label": k, "weight": round(v, 2)} for k, v in sorted(d.items(), key=lambda x: -x[1])]

    # Back-cast of CURRENT holdings over the range (not the real history of the account)
    days = {"1m": 31, "6m": 183, "1y": 365, "5y": 5 * 365}[rng]
    start = (dt.date.fromisoformat(store.as_of) - dt.timedelta(days=days)).isoformat()
    cal = [d for d in store.calendar if d >= start]
    step = 5 if rng == "5y" else 1
    pts = []
    with trace.step("market-data", "backcast_current_holdings", {"range": rng, "from": start}):
        for d in cal[::step] + ([cal[-1]] if (len(cal) - 1) % step else []):
            v = 0.0
            for r in rows:
                dates, _, close = store.prices[r["ticker"]]
                import bisect
                i = bisect.bisect_right(dates, d) - 1
                if i >= 0:
                    v += r["quantity"] * close[i] * (store.fx_on(d) if r["currency"] == "USD" else 1)
            pts.append({"date": d, "value": round(v, 2)})
    vals = [x["value"] for x in pts]
    w = {r["ticker"]: r["weight"] for r in rows if r["weight"] > 0}
    risk = {"volatility": 0.0, "maxDrawdown": 0.0}
    explanation = None
    if w:
        series = {t: M.window(store.cad_series(t), store.calendar, start) for t in w}
        idx = M.portfolio_values({t: v / 100 for t, v in w.items()}, series)
        risk = {"volatility": M.r2(M.vol(M.returns(idx))) or 0.0, "maxDrawdown": M.r2(-M.max_drawdown(idx)) or 0.0}
        pol = PR.build_policy(u.get("investorProfile"), trace, "user")
        ps = A.portfolio_stats(w, store)
        pk, sec, ccy = A.exposures(w, stats)
        G.check_allocation({"_weights": w, "stats": ps, "byPocket": pk, "growthShare": A.growth_share(w, stats)}, pol, stats, trace)
        trace.assume("Valeur en CAD au taux USD/CAD du jour d'analyse (Banque du Canada); le coût d'achat est converti au même taux.")
        trace.assume("Courbe de performance : valeur rétroactive des positions ACTUELLES (sans tenir compte des achats/ventes passés).")
        trace.limit("Volatilité et baisse maximale calculées sur la période choisie : une période calme sous-estime le risque.")
        explanation = trace.to_explanation()
        warnings.append("La courbe montre la valeur qu'auraient eue les positions actuelles; ce n'est pas l'historique réel du compte.")
    for r in rows:
        r.pop("_cls"), r.pop("_prev")
    return {"portfolioId": pid, "baseCurrency": "CAD", "asOf": store.as_of,
            "totals": {"value": round(tot, 2), "cost": round(cost, 2), "pnl": round(tot - cost, 2), "pnlPct": round((tot / cost - 1) * 100, 2) if cost else 0.0,
                       "dayChange": round(tot - prev, 2), "dayChangePct": round((tot / prev - 1) * 100, 2) if prev else 0.0},
            "holdings": rows, "allocation": {"byAssetClass": slices("assetClass"), "bySector": slices("sector"), "byCurrency": slices("currency")},
            "performance": {"range": rng, "points": pts}, "risk": risk, "warnings": warnings, "explanation": explanation}


# ------------------------------------------------------------------------------------ messages
def _slim(analysis: dict) -> dict:
    """Drop large series before storing a message (DynamoDB item ≤ 400 KB)."""
    a = copy.deepcopy(analysis)
    if a.get("allocation"):
        a["allocation"].get("stats", {}).pop("index", None)
    if a.get("request"):
        a["request"].pop("variantIndex", None)
        if a["request"].get("news"):
            a["request"]["news"].pop("series", None)
    a.pop("templateText", None)
    if a.get("writer"):
        a["writer"].pop("rejected", None)
    return a


def post_message(user: dict, sid: str, body: dict, request_id: str) -> dict:
    c = _conv(user, sid)
    content = body.get("content") if isinstance(body, dict) else None
    if not isinstance(content, str) or not content.strip() or len(content) > 2000:
        raise HttpError(400, "VALIDATION_ERROR", "content requis (1 à 2000 caractères).")
    u = get_user(user)
    db = get_db()
    ts = now()
    um = {"messageId": uuid.uuid4().hex, "sessionId": sid, "role": "user", "content": content.strip(), "status": "done", "createdAt": ts}
    db.put(f"CONV#{sid}", f"MSG#{ts}#{um['messageId']}", um)
    port = db.get(f"USER#{user['sub']}", "PORTFOLIO#main")
    try:
        r = analyze(content, profile=u.get("investorProfile"), holdings=(port or {}).get("holdings"), request_id=request_id)
        ts2 = now()
        am = {"messageId": uuid.uuid4().hex, "sessionId": sid, "role": "assistant", "content": r["content"], "status": "done", "createdAt": ts2,
              "explanation": r["explanation"], "analysis": _slim(r["analysis"])}
    except Exception as e:  # noqa: BLE001
        log.exception("analysis failed")
        ts2 = now()
        am = {"messageId": uuid.uuid4().hex, "sessionId": sid, "role": "assistant", "status": "error", "createdAt": ts2,
              "content": f"L'analyse a échoué ({type(e).__name__}). Réessayez ou reformulez. Réf. {request_id}"}
    db.put(f"CONV#{sid}", f"MSG#{ts2}#{am['messageId']}", am)
    c["updatedAt"] = ts2
    db.put(f"USER#{user['sub']}", f"CONV#{sid}", c)
    return {"userMessage": um, "assistantMessage": am}


# ------------------------------------------------------------------------------------ router
ROUTES = []


def route(method: str, pattern: str):
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn
    return deco


@route("GET", "/v1/me")
def r_me(user, q, b, rid):
    return get_user(user)


@route("PUT", "/v1/me/profile")
def r_profile(user, q, b, rid):
    u = get_user(user)
    u["investorProfile"] = validate_profile(b)
    get_db().put(f"USER#{user['sub']}", "PROFILE", u)
    return u


@route("GET", "/v1/conversations")
def r_convs(user, q, b, rid):
    get_user(user)
    items, cur = [], None
    while True:
        page, cur = get_db().query(f"USER#{user['sub']}", "CONV#", 100, cur)
        items += page
        if not cur or len(items) > 1000:
            break
    items.sort(key=lambda c: c["updatedAt"], reverse=True)
    limit = max(1, min(int(q.get("limit") or 20), 100))
    start = int(q.get("cursor") or 0)
    nxt = str(start + limit) if start + limit < len(items) else None
    return {"items": items[start:start + limit], "nextCursor": nxt}


@route("POST", "/v1/conversations")
def r_conv_new(user, q, b, rid):
    get_user(user)
    title = (b or {}).get("title") if isinstance(b, dict) else None
    if title is not None and (not isinstance(title, str) or len(title) > 120):
        raise HttpError(400, "VALIDATION_ERROR", "title ≤ 120 caractères.")
    ts = now()
    c = {"sessionId": uuid.uuid4().hex[:16], "title": (title or "Nouvelle conversation").strip(), "createdAt": ts, "updatedAt": ts}
    get_db().put(f"USER#{user['sub']}", f"CONV#{c['sessionId']}", c)
    return c


@route("PATCH", r"/v1/conversations/(?P<sid>[\w-]{1,64})")
def r_conv_patch(user, q, b, rid, sid):
    c = _conv(user, sid)
    title = (b or {}).get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise HttpError(400, "VALIDATION_ERROR", "title requis (≤ 120 caractères).")
    c["title"], c["updatedAt"] = title.strip(), now()
    get_db().put(f"USER#{user['sub']}", f"CONV#{sid}", c)
    return c


@route("DELETE", r"/v1/conversations/(?P<sid>[\w-]{1,64})")
def r_conv_del(user, q, b, rid, sid):
    _conv(user, sid)
    db = get_db()
    cur = None
    while True:
        page, cur = db.query(f"CONV#{sid}", "MSG#", 100, cur)
        for m in page:
            db.delete(f"CONV#{sid}", f"MSG#{m['createdAt']}#{m['messageId']}")
        if not cur:
            break
    db.delete(f"USER#{user['sub']}", f"CONV#{sid}")
    return None


@route("GET", r"/v1/conversations/(?P<sid>[\w-]{1,64})/messages")
def r_msgs(user, q, b, rid, sid):
    _conv(user, sid)
    limit = max(1, min(int(q.get("limit") or 50), 100))
    items, nxt = get_db().query(f"CONV#{sid}", "MSG#", limit, q.get("cursor"))
    return {"items": items, "nextCursor": nxt}


@route("POST", r"/v1/conversations/(?P<sid>[\w-]{1,64})/messages")
def r_msg_new(user, q, b, rid, sid):
    return post_message(user, sid, b, rid)


@route("GET", "/v1/portfolios")
def r_ports(user, q, b, rid):
    get_user(user)
    items, _ = get_db().query(f"USER#{user['sub']}", "PORTFOLIO#", 20)
    return {"items": items}


@route("PUT", r"/v1/portfolios/(?P<pid>[\w-]{1,40})/holdings")
def r_holdings(user, q, b, rid, pid):
    p = _portfolio(user, pid)
    hs = (b or {}).get("holdings")
    if not isinstance(hs, list) or len(hs) > 50:
        raise HttpError(400, "VALIDATION_ERROR", "holdings : liste (≤ 50) attendue.")
    store, seen, out = get_store(), set(), []
    for h in hs:
        if not isinstance(h, dict) or not isinstance(h.get("ticker"), str):
            raise HttpError(400, "VALIDATION_ERROR", "Position invalide.")
        t = h["ticker"].strip().upper()
        if t not in store.assets:
            raise HttpError(400, "ASSET_NOT_FOUND", f"{t} n'est pas dans l'univers des 31 actifs.")
        if t in seen:
            raise HttpError(400, "VALIDATION_ERROR", f"{t} apparaît deux fois.")
        seen.add(t)
        out.append({"ticker": t, "quantity": _num(h.get("quantity"), "quantity", 0, 1e9, allow_zero=False), "avgCost": _num(h.get("avgCost"), "avgCost", 0, 1e9)})
    p["holdings"], p["updatedAt"] = out, now()
    get_db().put(f"USER#{user['sub']}", f"PORTFOLIO#{pid}", p)
    return p


@route("GET", r"/v1/portfolios/(?P<pid>[\w-]{1,40})/summary")
def r_summary(user, q, b, rid, pid):
    return summary(user, pid, q.get("range") or "1y", rid)


@route("GET", "/v1/market/search")
def r_search(user, q, b, rid):
    s = get_store()
    return {"items": [a.to_api() for a in s.search(q.get("q") or "", q.get("assetClass") or None)]}


@route("GET", "/v1/market/assets")
def r_assets(user, q, b, rid):
    s = get_store()
    stats = MK.asset_stats(s)
    return {"asOf": s.as_of, "items": [{**s.assets[t].to_api(), "esgRationale": s.assets[t].esg_rationale, "esgSource": s.assets[t].esg_source,
                                        "stats": {k: v for k, v in st.items() if k not in ("name", "ticker", "sector", "currency", "assetClass", "esgScreen", "esgTags")}}
                                       for t, st in stats.items()]}


@route("GET", "/v1/agents")
def r_agents(user, q, b, rid):
    return REGISTRY


@route("GET", "/v1/personas")
def r_personas(user, q, b, rid):
    return {"items": list(PERSONAS.values())}


@route("GET", "/v1/data/sources")
def r_sources(user, q, b, rid):
    s = get_store()
    return {"asOf": s.as_of, "origin": "s3" if s.origin.startswith("s3://") else "local", "calendar": [s.calendar[0], s.calendar[-1]],
            "items": s.sources_meta,
            "rules": ["Aucune information postérieure à la date d'analyse n'est utilisée (as-of).",
                      "Séries macro mensuelles visibles 45 jours après le mois de référence (délai de publication).",
                      "Fondamentaux SEC visibles à leur date de dépôt, première version déposée (pas de retraitement ultérieur).",
                      "Prix convertis en CAD au taux Banque du Canada du jour; cours ajustés pour les rendements."]}


@route("POST", "/v1/analysis")
def r_analysis(user, q, b, rid):
    b = b if isinstance(b, dict) else {}
    question = b.get("question") or ""
    if not isinstance(question, str) or len(question) > 2000:
        raise HttpError(400, "VALIDATION_ERROR", "question ≤ 2000 caractères.")
    pid = b.get("personaId")
    if pid is not None and pid not in PERSONAS:
        raise HttpError(400, "VALIDATION_ERROR", "personaId inconnu (amira, mateo, robert).")
    overrides = b.get("overrides") or None
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise HttpError(400, "VALIDATION_ERROR", "overrides invalide.")
        if "riskLevel" in overrides and overrides["riskLevel"] not in RISK_LEVELS:
            raise HttpError(400, "VALIDATION_ERROR", "overrides.riskLevel invalide.")
        if "horizonMinYears" in overrides:
            overrides["horizonMinYears"] = int(_num(overrides["horizonMinYears"], "horizonMinYears", 0, 60))
    scale = _num(b.get("scenarioScale", 1.0), "scenarioScale", 0.1, 3.0)
    profile, holdings = None, None
    if not pid:
        u = get_user(user)
        profile = u.get("investorProfile")
        port = get_db().get(f"USER#{user['sub']}", "PORTFOLIO#main")
        holdings = (port or {}).get("holdings")
    if overrides and pid:
        profile = copy.deepcopy(PERSONAS[pid]["profile"])
    return analyze(question, profile=profile, persona_id=pid, holdings=holdings, overrides=overrides, scale=scale, request_id=rid)


def handle(method: str, path: str, query: Dict[str, str], body: Any, user: Optional[dict], request_id: str) -> Tuple[int, Optional[dict]]:
    if not user or not user.get("sub"):
        return 401, {"error": {"code": "UNAUTHORIZED", "message": "Jeton manquant ou invalide.", "requestId": request_id}}
    path = path.rstrip("/") or "/"
    for m, rx, fn in ROUTES:
        mt = rx.match(path)
        if mt and m == method:
            try:
                res = fn(user, query or {}, body, request_id, **mt.groupdict())
                return (204, None) if res is None else (200, res)
            except HttpError as e:
                return e.status, {"error": {"code": e.code, "message": e.message, "requestId": request_id}}
            except ValueError as e:
                return 400, {"error": {"code": "VALIDATION_ERROR", "message": str(e), "requestId": request_id}}
            except Exception:  # noqa: BLE001
                log.exception("unhandled error")
                return 500, {"error": {"code": "INTERNAL", "message": "Erreur interne.", "requestId": request_id}}
    return 404, {"error": {"code": "INTERNAL", "message": f"Route inconnue : {method} {path}", "requestId": request_id}}


def parse_body(raw: Optional[str]) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise HttpError(400, "VALIDATION_ERROR", "Corps JSON invalide.")
