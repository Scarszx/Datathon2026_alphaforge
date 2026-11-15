"""ExplainabilityAgent: EXPLAIN. Turns the trace into a short answer whose every statement is traceable.

Two writers, one rule ("only what the trace contains"):
  * a deterministic French template (always available, used as reference and fallback);
  * Amazon Bedrock (Claude Haiku) rephrasing the same fact sheet, accepted only if the governance agent's
    faithfulness check passes (all numbers traceable, no advice wording).
It also assigns a confidence level from observable signals (data coverage, check results, estimate dispersion).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .. import llm
from ..trace import Trace
from . import governance
from .profile import RISK_LABEL, Policy

AGENT_ID = "explainability"


def _f(x, nd=1):
    if x is None:
        return "n.d."
    return f"{x:.{nd}f}".replace(".", ",")


def confidence(trace: Trace, extra_unc: int = 0) -> Dict:
    fails = sum(1 for c in trace.checks if c["status"] == "fail")
    warns = sum(1 for c in trace.checks if c["status"] in ("warn", "not_verified"))
    unc = len(trace.uncertainties) + extra_unc
    if unc >= 3 or any(c["status"] == "not_verified" for c in trace.checks):
        level, why = "faible", "plusieurs incertitudes importantes sur les données ou les estimations"
    elif unc >= 1 or warns >= 3:
        level, why = "moyenne", "les estimations dépendent de la période observée ou de quelques hypothèses"
    else:
        level, why = "élevée", "données complètes sur la période et contrôles concordants"
    return {"level": level, "reason": why, "fails": fails, "warnings": warns, "uncertainties": unc}


def numbers_in(obj) -> List[float]:
    out: List[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            out += numbers_in(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out += numbers_in(v)
    elif isinstance(obj, str):
        import re
        for m in re.finditer(r"\d+(?:[.,]\d+)?", obj):
            try:
                out.append(float(m.group(0).replace(",", ".")))
            except ValueError:
                pass
    return out


def write(facts: dict, template: str, trace: Trace) -> Tuple[str, dict]:
    with trace.step(AGENT_ID, "narrate_with_bedrock" if llm.enabled() else "narrate_template",
                    {"model": llm.model_id() if llm.enabled() else None, "maxTokens": 450}) as st:
        text, meta = llm.narrate(facts)
        st["output"] = meta
        if text is None:
            st["status"] = "empty" if not llm.enabled() else "error"
            trace.check(AGENT_ID, "narrative_source", "pass" if not llm.enabled() else "warn",
                        "Texte déterministe (gabarit) : génération par modèle désactivée." if not llm.enabled()
                        else "Bedrock indisponible : texte déterministe utilisé.")
            return template, {"writer": "template", **meta}
    if governance.check_narrative(text, numbers_in(facts), trace):
        trace.source("bedrock", f"Amazon Bedrock · {meta['model']}", "", "Reformulation de la fiche de faits; aucun calcul par le modèle")
        return text, {"writer": "bedrock", **meta}
    return template, {"writer": "template_after_rejection", "rejected": text, **meta}


# --------------------------------------------------------------------------- templates (French)
def profile_line(p: Policy, name: str) -> str:
    h = f"{p.horizon_min}–{p.horizon_max} ans" if p.horizon_max else f"{p.horizon_min} ans et plus"
    return f"Profil {name} : risque {RISK_LABEL[p.risk_level]}, horizon {h}."


def allocation_text(name: str, p: Policy, alloc: dict, scen: List[dict], conf: dict) -> str:
    ps = alloc["stats"]
    top = ", ".join(f"{w['ticker']} {_f(w['weight'])} %" for w in alloc["weights"][:4])
    pk = alloc["byPocket"]
    worst = min(scen, key=lambda s: s["portfolioReturn"]) if scen else None
    lines = [
        profile_line(p, name),
        f"Allocation FICTIVE proposée : défensif {_f(pk.get('defensive', 0))} %, cœur indiciel {_f(pk.get('core', 0))} %, "
        f"satellite {_f(pk.get('satellite', 0))} %, crypto {_f(pk.get('crypto', 0))} %. Principales lignes : {top}.",
        f"FAIT [prices] : sur 3 ans, ce mélange aurait eu une volatilité de {_f(ps['vol3y'])} % (budget {_f(p.vol_budget, 0)} %) et une pire baisse de "
        f"{_f(ps['maxDrawdown5y'])} % sur 5 ans; nombre effectif de positions {_f(ps['effectiveN'])}.",
    ]
    if worst:
        lines.append(f"{'FAIT' if worst['kind'] == 'historical' else 'HYPOTHÈSE'} : pire scénario testé « {worst['label']} » : {_f(worst['portfolioReturn'])} % "
                     f"(soit {_f(worst['pnl'], 0)} $ sur 100 000 $ fictifs).")
    if p.esg:
        lines.append("Les préférences ESG ont exclu les activités d'extraction fossile" + (" et les titres sous surveillance pour controverse." if p.avoid_controversy else "."))
    lines.append(f"Confiance {conf['level']} : {conf['reason']}. Rendement passé ≠ rendement futur; simulation seulement, pas un conseil.")
    return "\n\n".join(lines)


def scenario_text(name: str, p: Policy, alloc: dict, scen: List[dict], conf: dict) -> str:
    lines = [profile_line(p, name), f"Tests de résistance sur l'allocation fictive du profil (volatilité 3 ans {_f(alloc['stats']['vol3y'])} %) :"]
    for s in scen:
        tag = "FAIT historique" if s["kind"] == "historical" else "HYPOTHÈSE"
        extra = ""
        if s.get("sensitivity"):
            se = s["sensitivity"]
            extra = f" Sensibilité : choc ×0,5 → {_f(se['0.5'])} %, ×1,5 → {_f(se['1.5'])} %."
        lines.append(f"• {tag} — {s['label']} : {_f(s['portfolioReturn'])} % ({_f(s['pnl'], 0)} $ sur 100 000 $ fictifs).{extra}")
    lines.append("Les scénarios hypothétiques ne sont pas des prévisions : leurs paramètres sont affichés et modifiables.")
    lines.append(f"Confiance {conf['level']} : {conf['reason']}. Simulation seulement.")
    return "\n\n".join(lines)


def request_text(name: str, p: Policy, ticker: str, s: dict, verdict: dict, pct: Optional[float], alt: float,
                 fund: Optional[dict], conf: dict) -> str:
    head = {"fail": f"Attention : la demande sur {ticker} n'est pas cohérente avec le profil {name}.",
            "warn": f"La demande sur {ticker} est possible mais tendue pour le profil {name}.",
            "pass": f"{ticker} est compatible avec le profil {name}, dans une proportion limitée.",
            "not_verified": f"Impossible de vérifier {ticker} : données insuffisantes."}[verdict["status"]]
    lines = [head, profile_line(p, name)]
    lines.append(f"FAIT [prices] : {ticker} a eu une volatilité de {_f(s['vol3y'])} % sur 3 ans et une pire baisse de {_f(s['maxDrawdown'])} % "
                 f"({s['peakDate']} → {s['troughDate']}). Rendement sur 5 ans : {_f(s['return5y'])} %, ce qui explique l'attention médiatique, "
                 "mais ne dit rien des 3 à 5 prochaines années.")
    if fund and "revenueGrowth" in fund:
        lines.append(f"FAIT [sec:{ticker}] : croissance du chiffre d'affaires {_f(fund['revenueGrowth']['value'])} % au dernier 10-K "
                     f"(déposé le {fund['revenueGrowth']['filed']})" + (f", marge nette {_f(fund['netMargin']['value'])} %." if "netMargin" in fund else "."))
    for i in verdict["issues"][:6]:
        lines.append("• " + i)
    if verdict["status"] in ("fail", "warn"):
        lines.append(f"Mise en contexte : dans une simulation respectant ce profil, l'exposition à {ticker} resterait au plus vers {_f(alt, 0)} % "
                     "(plafond retenu pour un titre de ce profil et de cette volatilité), à l'intérieur d'un portefeuille diversifié. C'est une illustration, pas une recommandation.")
    lines.append(f"Confiance {conf['level']} : {conf['reason']}. Simulation seulement.")
    return "\n\n".join(lines)


def compare_text(name: str, p: Policy, rows: List[dict], conf: dict) -> str:
    lines = [profile_line(p, name), "Comparaison descriptive (FAITS [prices], en CAD) :"]
    for r in rows:
        s = r["stats"]
        lines.append(f"• {r['ticker']} : rendement 1 an {_f(s['return1y'])} %, volatilité 3 ans {_f(s['vol3y'])} %, pire baisse {_f(s['maxDrawdown'])} %, "
                     f"2022 : {_f(s['return2022'])} %, filtre ESG « {s['esgScreen']} » → {r['fit']}.")
    lines.append(f"Confiance {conf['level']} : {conf['reason']}. Les chiffres passés ne prédisent pas l'avenir.")
    return "\n\n".join(lines)


def portfolio_text(name: str, p: Policy, ps: dict, scen: List[dict], conf: dict, fails: List[str]) -> str:
    worst = min(scen, key=lambda s: s["portfolioReturn"]) if scen else None
    lines = [profile_line(p, name),
             f"FAIT [prices] : votre portefeuille fictif aurait eu une volatilité de {_f(ps['vol3y'])} % sur 3 ans (budget {_f(p.vol_budget, 0)} %) "
             f"et une pire baisse de {_f(ps['maxDrawdown5y'])} % sur 5 ans; nombre effectif de positions {_f(ps['effectiveN'])}."]
    if worst:
        lines.append(f"Pire scénario testé « {worst['label']} » : {_f(worst['portfolioReturn'])} %.")
    lines.append("Points à revoir : " + "; ".join(fails) + "." if fails else "Aucun contrôle en échec.")
    lines.append(f"Confiance {conf['level']} : {conf['reason']}. Simulation seulement.")
    return "\n\n".join(lines)


def refusal_text() -> str:
    return ("Je ne peux ni exécuter de transaction ni accéder à un compte réel : AlphaForge est un outil de simulation sur données publiques. "
            "Je peux par contre analyser la demande : demandez par exemple « Que penses-tu de mettre 10 % dans NVDA pour mon profil ? » "
            "ou « Propose une allocation fictive ».")
