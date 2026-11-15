"""Orchestrator: COORDINATE. Runs the plan chosen by the planner, passes intermediate results between agents,
and returns {content, explanation, analysis}. The explanation is the execution trace itself.
"""
from __future__ import annotations

import copy
import logging
import uuid
from typing import Dict, List, Optional

from .agents import allocation as A
from .agents import explain as E
from .agents import governance as G
from .agents import market as MK
from .agents import planner as P
from .agents import profile as PR
from .agents import scenario as S
from .data import get_store
from .personas import PERSONAS
from .trace import Trace

log = logging.getLogger("alphaforge")


def _clean_alloc(a: dict) -> dict:
    return {k: v for k, v in a.items() if not k.startswith("_")}


def analyze(question: str, profile: Optional[dict] = None, persona_id: Optional[str] = None, holdings: Optional[List[dict]] = None,
            overrides: Optional[dict] = None, scale: float = 1.0, request_id: Optional[str] = None) -> dict:
    trace = Trace(request_id or uuid.uuid4().hex[:12])
    store = get_store()
    question = (question or "").strip()[:2000]
    name = "utilisateur"
    source = "user"
    if persona_id:
        per = PERSONAS.get(persona_id)
        if not per:
            raise ValueError(f"persona inconnue : {persona_id}")
        profile, name, source = copy.deepcopy(per["profile"]), per["displayName"].split(",")[0], f"persona:{persona_id}"
        question = question or per["demoQuestion"]
    if overrides and profile is not None:
        profile = {**profile, **{k: v for k, v in overrides.items() if k in ("riskLevel", "horizonMinYears", "horizonMaxYears", "preferences",
                                                                              "constraints", "excludedAssetClasses", "objective")}}
        trace.decide("orchestrator", "Profil modifié pour test de sensibilité", f"Paramètres changés : {', '.join(overrides)}")

    with trace.step("planner", "plan", {"question": question[:200]}) as st:
        pl = P.plan(question, store)
        if holdings and pl["intent"] in ("allocation",) and "portefeuille" in question.lower():
            pl["intent"] = "portfolio"
        st["output"] = pl
    out: Dict = {"intent": pl["intent"], "plan": pl, "persona": persona_id, "profileName": name, "asOf": store.as_of,
                 "dataOrigin": "s3" if store.origin.startswith("s3://") else "local"}

    if G.boundary(question, trace) == "trade":
        out["intent"] = "refusal"
        return {"content": E.refusal_text(), "explanation": trace.to_explanation(), "analysis": out}

    pol = PR.build_policy(profile, trace, source)
    out["policy"] = pol.to_api()
    stats = MK.load_universe(store, trace)
    out["macro"] = MK.macro_snapshot(store, trace)
    for k in ("V39079", "BD.CDN.10YR.DQ.YLD", "STATIC_TOTALCPICHANGE"):
        m = out["macro"].get(k)
        if m:
            trace.claim(f"{m['label']} : {m['value']} % (observation du {m['date']}).", "fact", ["macro"], MK.AGENT_ID)
    facts: Dict = {"profil": {"nom": name, "risque": PR.RISK_LABEL[pol.risk_level], "horizonMin": pol.horizon_min, "horizonMax": pol.horizon_max,
                              "budgetVolatilite": pol.vol_budget, "toleranceBaisse": pol.dd_tolerance, "esg": pol.esg},
                   "question": question, "dateDonnees": store.as_of,
                   "contexteMacro": {v["label"]: v["value"] for v in out["macro"].values()}}
    intent = pl["intent"]

    if intent == "compare":
        rows = []
        with trace.step(G.AGENT_ID, "profile_fit_per_asset", {"tickers": pl["tickers"]}):
            for t in pl["tickers"][:4]:
                s = stats[t]
                cap = G.max_compatible_weight(t, s, pol)
                fit = "hors profil" if cap == 0 else (f"compatible jusqu'à ~{cap:.0f} % (plafond)" if (s["vol3y"] or 0) <= 2 * pol.vol_budget
                                                       else f"très volatil pour ce profil, ≤ {cap:.0f} %")
                rows.append({"ticker": t, "stats": s, "fit": fit, "maxWeight": cap})
                trace.claim(f"{t} : volatilité 3 ans {s['vol3y']} %, pire baisse {s['maxDrawdown']} %, rendement 1 an {s['return1y']} %.", "fact",
                            ["prices", "fx"], MK.AGENT_ID)
        out["comparison"] = rows
        facts["comparaison"] = [{"ticker": r["ticker"], "volatilite3ans": r["stats"]["vol3y"], "pireBaisse": r["stats"]["maxDrawdown"],
                                 "rendement1an": r["stats"]["return1y"], "rendement2022": r["stats"]["return2022"], "esg": r["stats"]["esgScreen"],
                                 "adequation": r["fit"]} for r in rows]
        trace.limit("Comparer des rendements passés ne dit pas lequel fera mieux; la comparaison sert à situer le risque.")
        conf = E.confidence(trace)
        template = E.compare_text(name, pol, rows, conf)

    elif intent == "portfolio":
        if not holdings:
            trace.check(G.AGENT_ID, "portfolio_present", "not_verified", "Aucune position enregistrée : rien à analyser.")
            conf = E.confidence(trace)
            content = f"{E.profile_line(pol, name)}\n\nVotre portefeuille fictif est vide. Ajoutez des positions dans l'onglet Portefeuille."
            out["confidence"] = conf
            return {"content": content, "explanation": trace.to_explanation(), "analysis": out}
        with trace.step(MK.AGENT_ID, "value_holdings", {"holdings": len(holdings)}):
            vals = {}
            for h in holdings:
                lp = store.last_price(h["ticker"])
                if lp:
                    fx = store.fx_on(store.as_of) if store.assets[h["ticker"]].currency == "USD" else 1.0
                    vals[h["ticker"]] = h["quantity"] * lp["close"] * fx
            tot = sum(vals.values())
            w = {t: v / tot * 100 for t, v in vals.items()}
        ps = A.portfolio_stats(w, store)
        pk, sec, ccy = A.exposures(w, stats)
        alloc = {"weights": [{"ticker": t, "name": stats[t]["name"], "weight": round(v, 2), "pocket": A.pocket_of(stats[t]),
                              "assetClass": stats[t]["assetClass"], "sector": stats[t]["sector"], "vol3y": stats[t]["vol3y"],
                              "esgScreen": stats[t]["esgScreen"], "why": "position existante"} for t, v in sorted(w.items(), key=lambda x: -x[1])],
                 "byPocket": pk, "bySector": sec, "byCurrency": ccy, "stats": ps, "growthShare": round(A.growth_share(w, stats), 2), "_weights": w}
        G.check_allocation(alloc, pol, stats, trace)
        scen = S.run(w, stats, store, trace, value=tot, scale=scale)
        out.update({"allocation": _clean_alloc(alloc), "scenarios": scen, "lookback": S.lookback_sensitivity(ps, trace), "portfolioValue": round(tot, 2)})
        fails = [c["message"] for c in trace.checks if c["status"] in ("fail", "warn") and c["agentId"] == G.AGENT_ID]
        facts.update({"portefeuille": {"volatilite3ans": ps["vol3y"], "pireBaisse5ans": ps["maxDrawdown5y"], "nombreEffectif": ps["effectiveN"],
                                       "poches": pk}, "scenarios": [{"nom": s["label"], "type": s["kind"], "rendement": s["portfolioReturn"]} for s in scen],
                      "controlesEnEchec": fails})
        conf = E.confidence(trace)
        template = E.portfolio_text(name, pol, ps, scen, conf, fails)

    else:  # allocation, request, scenario
        alloc = A.propose(stats, pol, store, trace)
        G.check_allocation(alloc, pol, stats, trace)
        base_w = alloc["_weights"]
        out["allocation"] = _clean_alloc(alloc)
        out["lookback"] = S.lookback_sensitivity(alloc["stats"], trace)
        facts["allocation"] = {"poches": alloc["byPocket"], "lignes": {w["ticker"]: w["weight"] for w in alloc["weights"][:8]},
                               "volatilite3ans": alloc["stats"]["vol3y"], "pireBaisse5ans": alloc["stats"]["maxDrawdown5y"],
                               "nombreEffectif": alloc["stats"]["effectiveN"], "rendement2022": alloc["stats"]["return2022"]}
        if intent == "request":
            t = pl["tickers"][0]
            s = stats[t]
            pct = pl["percent"]
            variant = None
            if pct:
                vw = A.with_request(base_w, t, pct)
                with trace.step(G.AGENT_ID, "simulate_requested_weight", {"ticker": t, "weight": pct}):
                    vs = A.portfolio_stats(vw, store)
                variant = {"weights": vw, "stats": vs}
            verdict = G.check_request(t, pct, s, pol, alloc, variant, trace)
            fund = MK.fundamentals(store, t, trace) if store.fundamentals.get(t) else None
            if fund is None and s["assetClass"] == "equity" and s["currency"] == "CAD":
                trace.limit(f"Pas de données fondamentales structurées pour {t} (émetteur canadien : SEDAR+ n'offre pas d'API gratuite).")
            news = MK.news_attention(store, t, trace)
            if news and news["ratio"]:
                trace.claim(f"Attention médiatique sur {t} : {news['recentPpm']} articles par million sur les 3 derniers mois complets, "
                            f"{news['ratio']}× sa moyenne des mois précédents.", "fact", ["news"], MK.AGENT_ID)
                if pol.risk_level in ("low", "low_moderate", "moderate"):
                    verdict["issues"].append(f"La popularité médiatique de {t} (×{news['ratio']} vs sa moyenne) n'est pas une mesure de risque ni de qualité : "
                                             "elle peut amplifier les mouvements dans les deux sens.")
            elif s["assetClass"] in ("equity", "crypto"):
                trace.limit(f"Pas de mesure d'attention médiatique disponible pour {t}.")
            trace.uncertain(f"Les événements propres à {t} (résultats, réglementation, concurrence) ne sont pas modélisés : l'issue d'une position concentrée est très incertaine.")
            alt = G.max_compatible_weight(t, s, pol)
            scen_base = S.run(base_w, stats, store, trace, scale=scale)
            scen_var = S.run(variant["weights"], stats, store, Trace(trace.request_id), scale=scale) if variant else None
            out["request"] = {"ticker": t, "name": s["name"], "requestedWeight": pct, "assetStats": s, "verdict": verdict,
                              "maxCompatibleWeight": alt, "fundamentals": fund, "news": news,
                              "variantStats": {k: v for k, v in variant["stats"].items() if k != "index"} if variant else None,
                              "variantIndex": variant["stats"]["index"] if variant else None}
            out["scenarios"] = scen_base
            out["scenariosVariant"] = scen_var
            facts["demande"] = {"actif": t, "nom": s["name"], "poidsDemande": pct, "verdict": verdict["status"], "problemes": verdict["issues"],
                                "volatilite3ans": s["vol3y"], "pireBaisse": s["maxDrawdown"], "debutBaisse": s["peakDate"], "creux": s["troughDate"],
                                "joursRecuperation": s["recoveryDays"], "rendement5ans": s["return5y"], "plafondCompatible": alt,
                                "portefeuilleAvecDemande": ({"volatilite3ans": variant["stats"]["vol3y"], "pireBaisse5ans": variant["stats"]["maxDrawdown5y"]}
                                                            if variant else None),
                                "fondamentaux": ({k: v["value"] for k, v in fund.items()} if fund else None),
                                "attentionMediatique": ({"articlesParMillion3DerniersMois": news["recentPpm"], "multipleDeLaMoyenne": news["ratio"]} if news else None)}
            if scen_var:
                facts["scenariosAvecDemande"] = [{"nom": x["label"], "rendement": x["portfolioReturn"]} for x in scen_var]
            facts["scenariosBase"] = [{"nom": x["label"], "rendement": x["portfolioReturn"]} for x in scen_base]
            trace.claim(f"{t} : pire baisse historique {s['maxDrawdown']} % entre {s['peakDate']} et {s['troughDate']}.", "fact", ["prices", "fx"], MK.AGENT_ID)
            conf = E.confidence(trace)
            template = E.request_text(name, pol, t, s, verdict, pct, alt, fund, conf)
        else:
            scen = S.run(base_w, stats, store, trace, scale=scale)
            out["scenarios"] = scen
            facts["scenarios"] = [{"nom": x["label"], "type": x["kind"], "rendement": x["portfolioReturn"], "perte": x["pnl"],
                                   "sensibilite": x.get("sensitivity")} for x in scen]
            conf = E.confidence(trace)
            template = (E.scenario_text(name, pol, alloc, scen, conf) if intent == "scenario" else E.allocation_text(name, pol, alloc, scen, conf))

    facts["incertitudes"] = trace.uncertainties
    facts["hypotheses"] = trace.assumptions[:4]
    facts["confiance"] = conf
    facts["sourcesDisponibles"] = list(trace.sources)
    content, writer = E.write(facts, template, trace)
    out["confidence"] = E.confidence(trace)
    out["writer"] = writer
    out["templateText"] = template
    log.info('{"requestId": "%s", "type": "analysis_done", "intent": "%s", "persona": "%s", "writer": "%s"}',
             trace.request_id, out["intent"], persona_id, writer.get("writer"))
    return {"content": content, "explanation": trace.to_explanation(), "analysis": out}
