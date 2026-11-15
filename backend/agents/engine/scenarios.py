"""Scénarios 0/1/2 d'un mandat confirmé et leurs mesures (module-engine).

0 : portefeuille actuel ; 1 : idée appliquée telle quelle ; 2 : alternative par
catégorie, compatible avec le profil retenu (SOLUTION.md 7.2). L'alternative
garde le montant de l'idée et remplace chaque actif ajouté dont le profil
implicite dépasse le profil retenu (ou toute crypto refusée) par une catégorie
compatible. Le FNB qui la représente n'est qu'une approximation de calcul
(proxyNote) : le texte parle de la catégorie, jamais du titre (R5).

Chaque mesure devient un élément du registre (EV-nn) ; scenario.metrics ne
contient que des identifiants EV.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from backend.agents.data.store import DataStore
from backend.agents.engine import analytics as an
from backend.agents.engine.concentration import by_asset_class, concentration, top_sector
from backend.agents.engine.registry import EvidenceRegistry
from backend.agents.engine.stress import LABELS as STRESS_LABELS
from backend.agents.engine.stress import PERIOD_IDS, StressPeriod, derive_period
from backend.agents.rules.settings import risk_band, settings

PORTFOLIO_METHOD = (
    "Constant-weight portfolio (daily rebalanced) on adjusted close (adj_close) converted to CAD "
    "with the last known USD/CAD rate; common North American trading days of the holdings."
)
VOL_METHOD = "Standard deviation of daily returns x sqrt(252) (equities, ETFs) or sqrt(365) (crypto)."
DD_METHOD = "Largest peak-to-trough decline of the value index over the window."
PAST_CAVEATS = ["Past performance describes the past; it does not predict future returns."]
SURVIVOR_CAVEAT = "Survivorship bias: the asset universe was selected in 2026."

STRESS_METRIC_KEYS = {
    "y2022": "stress2022",
    "covid_2020": "stressCovid2020",
    "rate_hikes": "stressRates",
    "crypto_crash": "stressCrypto",
}


@dataclass
class ScenarioAnalysis:
    """Résultats chiffrés d'un scénario, lus par module-rules (jamais envoyés bruts au modèle)."""

    index: int
    label: str
    positions_cad: dict[str, float]
    weights: dict[str, float]
    metrics: dict[str, float] = field(default_factory=dict)
    stress: dict[str, float] = field(default_factory=dict)
    concentration: dict[str, Any] = field(default_factory=dict)
    idea_assets: list[dict[str, Any]] = field(default_factory=list)
    portfolio_band: int | None = None
    evidence: dict[str, str] = field(default_factory=dict)  # clé de mesure -> EV-nn
    description: str | None = None
    proxy_note: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class EngineResult:
    as_of: pd.Timestamp
    window: tuple[pd.Timestamp, pd.Timestamp]
    scenarios: list[ScenarioAnalysis]
    stress_periods: dict[str, StressPeriod]
    registry: EvidenceRegistry
    sources: list[dict[str, Any]]
    macro_usage: list[dict[str, Any]]
    warnings: list[str]


# --- valorisation ---------------------------------------------------------


def holding_values_cad(store: DataStore, holdings: list[dict[str, Any]], as_of: pd.Timestamp) -> tuple[dict[str, float], list[str]]:
    """Valeur CAD de chaque position au dernier cours (close) connu à as_of."""
    values: dict[str, float] = {}
    warnings: list[str] = []
    rate = an.fx_rate_on(store, as_of)
    for holding in holdings:
        ticker = holding["ticker"]
        if not store.has_ticker(ticker):
            warnings.append(f"{ticker} is not in the dataset universe: position ignored.")
            continue
        prices = store.prices(ticker)
        known = prices[prices.index <= as_of]
        if known.empty:
            warnings.append(f"No price for {ticker} on or before {as_of.date()}: position ignored.")
            continue
        last_day = known.index[-1]
        if (as_of - last_day).days > 5:
            warnings.append(f"Last price for {ticker} dated {last_day.date()} (stale).")
        price = float(known["close"].iloc[-1])
        value = price * float(holding["quantity"])
        if an.listing_currency(store, ticker) == "USD":
            value *= rate
        values[ticker] = values.get(ticker, 0.0) + value
    return values, warnings


def _amount_cad(store: DataStore, amount: float, currency: str | None, as_of: pd.Timestamp) -> float:
    return amount * an.fx_rate_on(store, as_of) if currency == "USD" else amount


def apply_operations(
    store: DataStore, positions: dict[str, float], operations: list[dict[str, Any]], as_of: pd.Timestamp, default_currency: str
) -> dict[str, float]:
    result = dict(positions)
    for op in operations:
        ticker = op["ticker"]
        action = op["action"]
        if action == "add":
            result[ticker] = result.get(ticker, 0.0) + _amount_cad(store, float(op.get("amount", 0.0)), op.get("currency") or default_currency, as_of)
        elif action == "remove":
            amount = op.get("amount")
            current = result.get(ticker, 0.0)
            removed = current if amount is None else min(current, _amount_cad(store, float(amount), op.get("currency") or default_currency, as_of))
            result[ticker] = current - removed
        elif action == "set_weight":
            target = float(op.get("weight", 0.0)) / 100.0
            total = sum(result.values())
            others = {t: v for t, v in result.items() if t != ticker}
            other_total = sum(others.values())
            if total <= 0:
                continue
            result = {t: v / other_total * total * (1 - target) for t, v in others.items()} if other_total else {}
            result[ticker] = total * target
    return {t: v for t, v in result.items() if v > 1e-9}


def _weights(positions: dict[str, float]) -> dict[str, float]:
    total = sum(positions.values())
    return {t: v / total * 100.0 for t, v in positions.items()} if total else {}


# --- alternative par catégorie --------------------------------------------


def _asset_band(store: DataStore, ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple[int | None, float | None]:
    metrics = an.asset_metrics(store, ticker, start, end)
    vol = metrics.get("volatility")
    if vol is None or vol != vol:
        return None, None
    return risk_band(vol), vol


def choose_category(store: DataStore, risk_profile: int, start: pd.Timestamp, end: pd.Timestamp) -> tuple[str, str] | None:
    """Première catégorie (et son FNB d'approximation) compatible avec le profil retenu."""
    categories = settings()["alternativeCategories"].get(str(risk_profile), [])
    fallback = None
    for category in categories:
        for proxy in category["proxies"]:
            if not store.has_ticker(proxy):
                continue
            band, _ = _asset_band(store, proxy, start, end)
            if band is not None and band <= risk_profile:
                return category["category"], proxy
            fallback = fallback or (category["category"], proxy)
    return fallback


def _crypto_refused(mandate: dict[str, Any]) -> bool:
    preferences = mandate.get("preferences") or {}
    excluded = [c.lower() for c in preferences.get("excludedAssetClasses") or []]
    constraints = " ".join(mandate.get("constraints") or []).lower()
    return "crypto" in excluded or "no crypto" in constraints


def alternative_operations(
    store: DataStore, mandate: dict[str, Any], risk_profile: int, start: pd.Timestamp, end: pd.Timestamp
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]] | None:
    """Opérations du scénario 2, ou None si l'idée est déjà compatible."""
    replaced: list[tuple[str, str, str]] = []  # (ticker remplacé, catégorie, proxy)
    operations: list[dict[str, Any]] = []
    category = choose_category(store, risk_profile, start, end)
    for op in mandate.get("operations") or []:
        if op["action"] not in ("add", "set_weight"):
            operations.append(op)
            continue
        ticker = op["ticker"]
        asset_class = store.asset(ticker).get("asset_class") if store.has_ticker(ticker) else None
        band, _ = _asset_band(store, ticker, start, end)
        incompatible = band is None or band > risk_profile
        if an.is_crypto(ticker, asset_class) and _crypto_refused(mandate):
            incompatible = True
        if not incompatible or category is None or category[1] == ticker:
            operations.append(op)
            continue
        replaced.append((ticker, category[0], category[1]))
        operations.append({**op, "ticker": category[1]})
    if not replaced:
        return None
    return operations, replaced


# --- moteur ---------------------------------------------------------------


def _analysis_window(store: DataStore) -> tuple[pd.Timestamp, pd.Timestamp]:
    end = store.last_date()
    start = end - pd.DateOffset(years=int(settings()["windowYears"]))
    return pd.Timestamp(start), pd.Timestamp(end)


def _record_scenario_metrics(
    store: DataStore, registry: EvidenceRegistry, scenario: ScenarioAnalysis, start: pd.Timestamp, end: pd.Timestamp,
    periods: dict[str, StressPeriod], dataset_source: str,
) -> None:
    tickers = list(scenario.weights)
    aligned = an.aligned_cad_prices(store, tickers, start, end)
    if aligned.missing:
        scenario.notes.append("No price data on the window for " + ", ".join(aligned.missing) + ".")
    caveats = list(PAST_CAVEATS) + [SURVIVOR_CAVEAT]
    if aligned.shortened_by:
        caveats.append(
            "Window shortened to the common history of the holdings because of " + ", ".join(aligned.shortened_by) + "."
        )
    metrics = an.portfolio_metrics(aligned.frame, scenario.weights)
    window = an.window_label(aligned.start, aligned.end)
    if metrics:
        scenario.metrics = {k: metrics[k] for k in ("volatility", "maxDrawdown", "totalReturn")}
        scenario.portfolio_band = risk_band(metrics["volatility"])
        scenario.evidence["volatility"] = registry.add(
            kind="metric", label=f"Annualized volatility, scenario {scenario.index}", value=metrics["volatility"],
            scenario=scenario.index, method=f"{VOL_METHOD} {PORTFOLIO_METHOD}", window=window, currency="CAD",
            source=dataset_source, as_of=end.date().isoformat(), caveats=caveats, key="volatility",
        )
        scenario.evidence["maxDrawdown"] = registry.add(
            kind="metric", label=f"Maximum drawdown, scenario {scenario.index}", value=metrics["maxDrawdown"],
            scenario=scenario.index, method=f"{DD_METHOD} {PORTFOLIO_METHOD}", window=window, currency="CAD",
            source=dataset_source, as_of=end.date().isoformat(), caveats=caveats, key="maxDrawdown",
        )
        scenario.evidence["totalReturn"] = registry.add(
            kind="metric", label=f"Total return over the window, scenario {scenario.index}", value=metrics["totalReturn"],
            scenario=scenario.index, method=f"Change of the value index over the window. {PORTFOLIO_METHOD}",
            window=window, currency="CAD", source=dataset_source, as_of=end.date().isoformat(), caveats=caveats,
            key="totalReturn",
        )

    ranges = an.bootstrap_ranges(an.portfolio_index(aligned.frame, scenario.weights)) if metrics else {}
    if ranges:
        range_method = (
            f"Moving-block bootstrap ({ranges['resamples']} resamples, {ranges['blockDays']}-day blocks, fixed seed) of the "
            f"portfolio's daily returns over the window; 5th to 95th percentile. It shows how much the figure depends on the "
            f"period observed, not what the future holds. {PORTFOLIO_METHOD}"
        )
        fmt = "{:.1f}".format
        vol_low, vol_high = fmt(ranges["volatilityLow"]), fmt(ranges["volatilityHigh"])
        dd_low, dd_high = fmt(ranges["maxDrawdownLow"]), fmt(ranges["maxDrawdownHigh"])
        if registry.language == "fr":
            vol_text = f"{vol_low} % à {vol_high} %".replace(".", ",")
            dd_text = f"{dd_low} % à {dd_high} %".replace(".", ",")
        else:
            vol_text, dd_text = f"{vol_low}% to {vol_high}%", f"{dd_low}% to {dd_high}%"
        scenario.evidence["volatilityRange"] = registry.add(
            kind="metric", label=f"Annualized volatility, 90% resampling range, scenario {scenario.index}",
            value=(ranges["volatilityLow"] + ranges["volatilityHigh"]) / 2, formatted=vol_text,
            scenario=scenario.index, method=range_method, window=window, currency="CAD", source=dataset_source,
            as_of=end.date().isoformat(), caveats=caveats, key="volatilityRange",
        )
        scenario.evidence["maxDrawdownRange"] = registry.add(
            kind="metric", label=f"Maximum drawdown, 90% resampling range, scenario {scenario.index}",
            value=(ranges["maxDrawdownLow"] + ranges["maxDrawdownHigh"]) / 2, formatted=dd_text,
            scenario=scenario.index, method=range_method, window=window, currency="CAD", source=dataset_source,
            as_of=end.date().isoformat(), caveats=caveats, key="maxDrawdownRange",
        )

    for period_id, period in periods.items():
        if not period.available:
            continue
        stressed = an.aligned_cad_prices(store, tickers, period.start, period.end, require_full_window=True)
        if stressed.missing or stressed.frame.empty:
            scenario.notes.append(
                f"{STRESS_LABELS[period_id]} not computed: insufficient history for "
                + ", ".join(stressed.missing or tickers) + "."
            )
            continue
        index = an.portfolio_index(stressed.frame, scenario.weights)
        if index.empty:
            continue
        drawdown, _, _ = an.max_drawdown(index)
        key = STRESS_METRIC_KEYS[period_id]
        scenario.stress[period_id] = drawdown
        scenario.evidence[key] = registry.add(
            kind="metric", label=f"Maximum drawdown during {STRESS_LABELS[period_id].split(': ', 1)[1]}, scenario {scenario.index}",
            value=drawdown, scenario=scenario.index, method=f"{DD_METHOD} {PORTFOLIO_METHOD} Period: {period.method}",
            window=an.window_label(period.start, period.end), currency="CAD", source=dataset_source,
            caveats=PAST_CAVEATS, key=key,
        )

    conc = concentration(store, scenario.weights)
    scenario.concentration = conc
    conc_caveats = conc["caveats"] or None
    conc_source = dataset_source + (
        "; " + "; ".join(conc["sources"]) if conc["sources"] else ""
    )
    if conc["topSingle"]["ticker"]:
        scenario.evidence["topSingleWeight"] = registry.add(
            kind="metric", label=f"Largest single-security weight (direct positions plus the fund holdings available in the dataset), scenario {scenario.index}",
            value=conc["topSingle"]["weight"], scenario=scenario.index,
            method="Direct positions plus each fund's published top holdings, as a share of the portfolio.",
            source=conc_source, caveats=conc_caveats, key="topSingleWeight",
        )
    sector_label, sector_weight = top_sector(conc)
    if sector_label:
        scenario.evidence["topSectorWeight"] = registry.add(
            kind="metric", label=f"Largest sector weight ({sector_label}; direct positions plus the fund exposure available in the dataset), scenario {scenario.index}",
            value=sector_weight, scenario=scenario.index,
            method="Direct equities by sector plus each fund's published sector weights, as a share of the portfolio. Funds without a published composition are not counted in a sector.",
            source=conc_source, caveats=conc_caveats, key="topSectorWeight",
        )
    scenario.evidence["techWeightLookThrough"] = registry.add(
        kind="metric", label=f"Information Technology weight (direct positions plus the fund exposure available in the dataset), scenario {scenario.index}",
        value=conc["techLookThrough"], scenario=scenario.index,
        method="Direct IT equities plus each fund's published IT sector weight, as a share of the portfolio.",
        source=conc_source, caveats=conc_caveats, key="techWeightLookThrough",
    )
    scenario.evidence["cryptoWeight"] = registry.add(
        kind="metric", label=f"Crypto-asset weight, scenario {scenario.index}", value=conc["cryptoWeight"],
        scenario=scenario.index, method="Crypto-asset positions as a share of the portfolio.", source=dataset_source,
        key="cryptoWeight",
    )


def run_engine(
    store: DataStore,
    mandate_item: dict[str, Any],
    portfolio: dict[str, Any] | None,
    registry: EvidenceRegistry,
) -> EngineResult:
    """Construit les scénarios et inscrit toutes les mesures au registre."""
    mandate = mandate_item["mandate"]
    risk_profile = int(mandate_item["riskProfile"])
    start, end = _analysis_window(store)
    dataset_source = store.source_label("prices") + " (Yahoo Finance via yfinance); fx/usdcad.parquet (Bank of Canada Valet)"
    holdings = (portfolio or {}).get("holdings") or []
    base_currency = (portfolio or {}).get("baseCurrency") or "CAD"
    warnings: list[str] = []

    positions0, value_warnings = holding_values_cad(store, holdings, end)
    warnings.extend(value_warnings)
    periods = {pid: derive_period(store, pid) for pid in PERIOD_IDS}
    macro_usage: list[dict[str, Any]] = []
    if periods["rate_hikes"].available:
        series_id = "V39079" if "V39079" in periods["rate_hikes"].method else "DFF"
        used_up_to = periods["rate_hikes"].end
        macro = store.macro()
        rows = macro[(macro["series_id"] == series_id) & (macro["date"] <= used_up_to)]
        publication = None
        if "publication_date" in rows.columns and not rows.empty:
            publication = rows["publication_date"].max()
        # R10 : la dernière valeur utilisée doit être publiée avant la date d'analyse (asOf).
        macro_usage.append({"seriesId": series_id, "usedUpTo": used_up_to, "publication": publication, "asOf": end})

    for period_id, period in periods.items():
        if period.available:
            registry.add(
                kind="assumption", label=STRESS_LABELS[period_id], formatted=an.window_label(period.start, period.end),
                method=period.method, window=an.window_label(period.start, period.end), source=period.source,
                key=f"period:{period_id}",
            )
    registry.add(
        kind="assumption", label="Analysis window (team assumption)", value=float(settings()["windowYears"]),
        unit="years" if registry.language != "fr" else "ans", window=an.window_label(start, end),
        method="Trailing window ending at the last price date of the dataset.", source=dataset_source,
        as_of=end.date().isoformat(), key="window",
    )

    scenarios: list[ScenarioAnalysis] = []
    operations = mandate.get("operations") or []
    s0 = ScenarioAnalysis(0, "Current portfolio", positions0, _weights(positions0))
    scenarios.append(s0)
    if operations:
        positions1 = apply_operations(store, positions0, operations, end, base_currency)
        s1 = ScenarioAnalysis(1, "Idea as stated", positions1, _weights(positions1))
        s1.idea_assets = _idea_assets(store, operations, start, end)
        scenarios.append(s1)
        alternative = alternative_operations(store, mandate, risk_profile, start, end)
        if alternative is not None:
            ops2, replaced = alternative
            positions2 = apply_operations(store, positions0, ops2, end, base_currency)
            s2 = ScenarioAnalysis(2, "Alternative by asset category", positions2, _weights(positions2))
            categories = sorted({category for _, category, _ in replaced})
            s2.description = (
                "Same amount as the idea, allocated to " + ", ".join(c.lower() for c in categories)
                + ", a category compatible with the retained risk profile."
            )
            s2.proxy_note = "; ".join(
                f"{category} approximated by {proxy} for the calculation only" for _, category, proxy in replaced
            ) + "."
            s2.idea_assets = _idea_assets(store, ops2, start, end)
            scenarios.append(s2)

    for scenario in scenarios:
        if not scenario.weights:
            scenario.notes.append("Empty portfolio: no metric computed.")
            continue
        _record_scenario_metrics(store, registry, scenario, start, end, periods, dataset_source)

    subject = mandate.get("subjectTicker")
    idea_tickers = {a["ticker"] for s in scenarios for a in s.idea_assets}
    asset_evidence: dict[str, dict[str, str]] = {}
    for ticker in sorted(idea_tickers | ({subject} if subject else set())):
        asset_evidence[ticker] = _record_asset_metrics(store, registry, ticker, start, end)
    for scenario in scenarios:
        for asset in scenario.idea_assets:
            asset["evidence"] = asset_evidence.get(asset["ticker"], {}).get("volatility")

    sources = [
        {"id": "prices_daily", "dataset": store.source_label("prices"), "asOf": end.date().isoformat(),
         "note": "adj_close for returns, close for valuation; listing currency converted to CAD"},
        {"id": "fx_usdcad", "dataset": store.source_label("fx/usdcad.parquet"), "note": "last known rate carried forward"},
    ]
    if macro_usage:
        sources.append({"id": "macro", "dataset": store.source_label("macro/macro.parquet"),
                        "note": "policy rate used to derive the hiking-cycle stress period"})
    if store.etf_enriched():
        sources.append({"id": "etf_enriched", "dataset": store.source_label("etf_enriched.json"),
                        "note": "issuer fund sheets (dated) for look-through"})
    return EngineResult(end, (start, end), scenarios, periods, registry, sources, macro_usage, warnings)


def _idea_assets(store: DataStore, operations: list[dict[str, Any]], start: pd.Timestamp, end: pd.Timestamp) -> list[dict[str, Any]]:
    assets = []
    for op in operations:
        if op["action"] not in ("add", "set_weight") or not store.has_ticker(op["ticker"]):
            continue
        band, vol = _asset_band(store, op["ticker"], start, end)
        asset_class = store.asset(op["ticker"]).get("asset_class")
        assets.append({"ticker": op["ticker"], "band": band, "volatility": vol,
                       "crypto": an.is_crypto(op["ticker"], asset_class)})
    return assets


def _record_asset_metrics(store: DataStore, registry: EvidenceRegistry, ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, str]:
    """Inscrit la volatilité et la pire baisse d'un titre ; renvoie leurs identifiants EV-nn."""
    metrics = an.asset_metrics(store, ticker, start, end)
    if not metrics:
        return {}
    currency = an.listing_currency(store, ticker)
    window = an.window_label(metrics["start"], metrics["end"])
    source = store.source_label(f"prices/{ticker}.parquet")
    root = "sqrt(365)" if metrics["periods"] == 365 else "sqrt(252)"
    volatility_id = registry.add(
        kind="metric", label=f"Annualized volatility of {ticker} (listing currency)", value=metrics["volatility"],
        method=f"Standard deviation of daily returns x {root}, native calendar, adj_close.", window=window,
        currency=currency, source=source, caveats=PAST_CAVEATS, key=f"asset:{ticker}:volatility",
    )
    drawdown_id = registry.add(
        kind="metric", label=f"Maximum drawdown of {ticker} (listing currency)", value=metrics["maxDrawdown"],
        method="Largest peak-to-trough decline of adj_close over the window, native calendar.", window=window,
        currency=currency, source=source, caveats=PAST_CAVEATS, key=f"asset:{ticker}:maxDrawdown",
    )
    return {"volatility": volatility_id, "maxDrawdown": drawdown_id}


def public_scenarios(result: EngineResult, verdicts_by_scenario: dict[int, str]) -> list[dict[str, Any]]:
    """Scénarios au format schema-scenario (scenario.metrics = identifiants EV-nn)."""
    store_free = []
    for scenario in result.scenarios:
        item: dict[str, Any] = {
            "index": scenario.index,
            "label": scenario.label,
            "metrics": dict(scenario.evidence),
            "verdict": verdicts_by_scenario.get(scenario.index, "pass"),
        }
        if scenario.description:
            item["description"] = scenario.description
        if scenario.proxy_note:
            item["proxyNote"] = scenario.proxy_note
        # scenario.notes (données manquantes) vont dans run.explanation.limitations :
        # schema-scenario n'a pas de champ pour elles.
        store_free.append(item)
    return store_free


def attach_allocations(store: DataStore, result: EngineResult, scenarios: list[dict[str, Any]]) -> None:
    by_index = {s.index: s for s in result.scenarios}
    for item in scenarios:
        item["allocation"] = by_asset_class(store, by_index[item["index"]].weights)
