"""Descriptive risk/return statistics. Every number here describes the PAST; none is a forecast."""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

TRADING_DAYS = 252


def _finite(x: float) -> bool:
    return x is not None and not math.isnan(x)


def returns(values: Sequence[float]) -> List[float]:
    """Simple daily returns; NaN when either side is unknown."""
    out = []
    for a, b in zip(values[:-1], values[1:]):
        out.append(b / a - 1 if _finite(a) and _finite(b) and a > 0 else float("nan"))
    return out


def vol(rets: Sequence[float]) -> float:
    r = [x for x in rets if _finite(x)]
    if len(r) < 20:
        return float("nan")
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(TRADING_DAYS) * 100


def max_drawdown(values: Sequence[float]) -> float:
    peak, mdd = -math.inf, 0.0
    for v in values:
        if not _finite(v):
            continue
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return mdd * 100


def total_return(values: Sequence[float]) -> float:
    v = [x for x in values if _finite(x)]
    return (v[-1] / v[0] - 1) * 100 if len(v) > 1 and v[0] > 0 else float("nan")


def cagr(values: Sequence[float], years: float) -> float:
    tr = total_return(values)
    return ((1 + tr / 100) ** (1 / years) - 1) * 100 if _finite(tr) and years > 0 else float("nan")


def hist_var(rets: Sequence[float], level: float = 0.95) -> float:
    """Historical 1-day Value-at-Risk (loss, %) at `level`."""
    r = sorted(x for x in rets if _finite(x))
    if len(r) < 50:
        return float("nan")
    return -r[int((1 - level) * len(r))] * 100


def corr(a: Sequence[float], b: Sequence[float]) -> float:
    pairs = [(x, y) for x, y in zip(a, b) if _finite(x) and _finite(y)]
    if len(pairs) < 30:
        return float("nan")
    ma = sum(p[0] for p in pairs) / len(pairs)
    mb = sum(p[1] for p in pairs) / len(pairs)
    cov = sum((x - ma) * (y - mb) for x, y in pairs)
    va = sum((x - ma) ** 2 for x, _ in pairs)
    vb = sum((y - mb) ** 2 for _, y in pairs)
    return cov / math.sqrt(va * vb) if va > 0 and vb > 0 else float("nan")


def portfolio_values(weights: Dict[str, float], series: Dict[str, List[float]]) -> List[float]:
    """Daily-rebalanced portfolio index (start = 100). Assets missing on a day contribute 0 return that day."""
    rets = {t: returns(series[t]) for t in weights}
    n = len(next(iter(series.values()))) if series else 0
    out = [100.0]
    for i in range(n - 1):
        r = sum(w * (rets[t][i] if _finite(rets[t][i]) else 0.0) for t, w in weights.items())
        out.append(out[-1] * (1 + r))
    return out


def risk_contributions(weights: Dict[str, float], series: Dict[str, List[float]]) -> Dict[str, float]:
    """Share (%) of portfolio variance coming from each asset: w_i * (Σw)_i / w'Σw."""
    tick = [t for t, w in weights.items() if w > 0]
    rets = {t: returns(series[t]) for t in tick}
    n = len(next(iter(rets.values()))) if rets else 0
    clean = {t: [x if _finite(x) else 0.0 for x in rets[t]] for t in tick}
    means = {t: sum(clean[t]) / max(n, 1) for t in tick}
    cov = {}
    for a in tick:
        for b in tick:
            if (b, a) in cov:
                cov[(a, b)] = cov[(b, a)]
                continue
            cov[(a, b)] = sum((clean[a][i] - means[a]) * (clean[b][i] - means[b]) for i in range(n)) / max(n - 1, 1)
    sw = {a: sum(cov[(a, b)] * weights[b] for b in tick) for a in tick}
    total = sum(weights[a] * sw[a] for a in tick)
    return {a: (weights[a] * sw[a] / total * 100 if total > 0 else 0.0) for a in tick}


def effective_n(weights: Dict[str, float]) -> float:
    s = sum(w * w for w in weights.values() if w > 0)
    return 1 / s if s > 0 else 0.0


def window(values: List[float], calendar: List[str], start: Optional[str], end: Optional[str] = None) -> List[float]:
    return [v for v, d in zip(values, calendar) if (start is None or d >= start) and (end is None or d <= end)]


def r2(x: float, nd: int = 2) -> Optional[float]:
    return round(x, nd) if _finite(x) else None
