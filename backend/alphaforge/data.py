"""Data layer: loads the public dataset (local folder or Amazon S3) and exposes point-in-time views.

Time-consistency rules (no look-ahead bias):
  * every query takes an ``as_of`` date; nothing after it is visible;
  * monthly macro series are dated by reference month, so they only become visible
    MONTHLY_PUBLICATION_LAG_DAYS after that date (CPI/unemployment are published ~2-6 weeks later);
  * SEC fundamentals become visible on their ``filed`` date, never on the fiscal period end.
Comparability: every price is converted to CAD with the Bank of Canada USD/CAD rate of the same day
(last known rate carried forward on non-business days), and adjusted close (dividends + splits) is used
for returns. Raw close is kept for valuation of holdings.
"""
from __future__ import annotations

import bisect
import csv
import io
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

MONTHLY_PUBLICATION_LAG_DAYS = 45
STALE_PRICE_DAYS = 5

FILES = ["assets_universe.csv", "prices_daily.csv", "corporate_actions.csv", "fx_usdcad_daily.csv",
         "macro_rates.csv", "fundamentals_sec.csv", "sources_metadata.csv", "news_attention.csv"]


@dataclass
class Asset:
    ticker: str
    name: str
    asset_class: str
    market: str
    currency: str
    sector: str
    esg_screen: str = "unknown"
    esg_tags: List[str] = field(default_factory=list)
    esg_rationale: str = ""
    esg_source: str = ""

    def to_api(self) -> dict:
        return {"ticker": self.ticker, "name": self.name, "assetClass": self.asset_class, "market": self.market,
                "currency": self.currency, "sector": self.sector, "esgScreen": self.esg_screen, "esgTags": self.esg_tags}


def _add_days(d: str, n: int) -> str:
    import datetime as dt
    return (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()


class DataStore:
    def __init__(self, texts: Dict[str, str], origin: str):
        self.origin = origin
        self.assets: Dict[str, Asset] = {}
        for r in csv.DictReader(io.StringIO(texts["assets_universe.csv"])):
            self.assets[r["ticker"]] = Asset(
                r["ticker"], r["name"], r["asset_class"], r.get("market", ""), r["currency"], r.get("sector", ""),
                r.get("esg_screen", "unknown") or "unknown",
                [t for t in (r.get("esg_activity_tags") or "").split(";") if t],
                r.get("esg_rationale", ""), r.get("esg_evidence_source", ""))
        # prices: ticker -> (dates, adj, close)
        raw: Dict[str, List[Tuple[str, float, float]]] = {}
        for r in csv.DictReader(io.StringIO(texts["prices_daily.csv"])):
            try:
                c = float(r["close"])
                a = float(r.get("adj_close") or c)
            except (TypeError, ValueError):
                continue
            raw.setdefault(r["ticker"], []).append((r["date"], a, c))
        self.prices: Dict[str, Tuple[List[str], List[float], List[float]]] = {}
        for t, rows in raw.items():
            rows.sort()
            self.prices[t] = ([x[0] for x in rows], [x[1] for x in rows], [x[2] for x in rows])
        fx = sorted((r["date"], float(r["usdcad"])) for r in csv.DictReader(io.StringIO(texts["fx_usdcad_daily.csv"])))
        self.fx_dates = [d for d, _ in fx]
        self.fx_vals = [v for _, v in fx]
        self.macro: Dict[str, dict] = {}
        for r in csv.DictReader(io.StringIO(texts["macro_rates.csv"])):
            s = self.macro.setdefault(r["series_id"], {"label": r["label"], "unit": r["unit"], "frequency": r["frequency"],
                                                       "source": r["source"], "dates": [], "values": []})
            s["dates"].append(r["date"]); s["values"].append(float(r["value"]))
        self.fundamentals: Dict[str, List[dict]] = {}
        for r in csv.DictReader(io.StringIO(texts.get("fundamentals_sec.csv", "ticker\n"))):
            if r.get("ticker"):
                self.fundamentals.setdefault(r["ticker"], []).append(r)
        self.dividends: Dict[str, List[Tuple[str, float]]] = {}
        for r in csv.DictReader(io.StringIO(texts.get("corporate_actions.csv", "ticker\n"))):
            if r.get("action") == "dividend":
                self.dividends.setdefault(r["ticker"], []).append((r["ex_date"], float(r["value"])))
        self.news: Dict[str, List[Tuple[str, int, float]]] = {}
        for r in csv.DictReader(io.StringIO(texts.get("news_attention.csv", "ticker\n"))):
            if r.get("ticker") and r.get("share_ppm"):
                self.news.setdefault(r["ticker"], []).append((r["month"], int(r["articles"]), float(r["share_ppm"])))
        self.sources_meta = list(csv.DictReader(io.StringIO(texts.get("sources_metadata.csv", "file\n"))))
        self.as_of = max(d[0][-1] for t, d in self.prices.items() if self.assets.get(t) and self.assets[t].asset_class != "crypto")
        # Common calendar: Bank of Canada business days (also the FX calendar) within price coverage
        first = max(min(d[0][0] for d in self.prices.values()), self.fx_dates[0])
        self.calendar = [d for d in self.fx_dates if first <= d <= self.as_of]
        self._cad_cache: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------ point-in-time accessors
    def fx_on(self, d: str) -> float:
        i = bisect.bisect_right(self.fx_dates, d) - 1
        return self.fx_vals[max(i, 0)]

    def last_price(self, ticker: str, as_of: Optional[str] = None) -> Optional[dict]:
        p = self.prices.get(ticker)
        if not p:
            return None
        as_of = as_of or self.as_of
        i = bisect.bisect_right(p[0], as_of) - 1
        if i < 0:
            return None
        prev = p[2][i - 1] if i > 0 else p[2][i]
        import datetime as dt
        age = (dt.date.fromisoformat(as_of) - dt.date.fromisoformat(p[0][i])).days
        return {"date": p[0][i], "close": p[2][i], "prev_close": prev, "stale": age > STALE_PRICE_DAYS, "age_days": age}

    def cad_series(self, ticker: str) -> List[float]:
        """Adjusted close in CAD on the common calendar (last price carried forward). NaN before first price."""
        if ticker in self._cad_cache:
            return self._cad_cache[ticker]
        dates, adj, _ = self.prices[ticker]
        usd = self.assets[ticker].currency == "USD"
        out, j = [], -1
        for d in self.calendar:
            while j + 1 < len(dates) and dates[j + 1] <= d:
                j += 1
            if j < 0:
                out.append(float("nan"))
            else:
                out.append(adj[j] * (self.fx_on(d) if usd else 1.0))
        self._cad_cache[ticker] = out
        return out

    def macro_as_of(self, series_id: str, as_of: Optional[str] = None) -> Optional[dict]:
        s = self.macro.get(series_id)
        if not s:
            return None
        as_of = as_of or self.as_of
        lag = MONTHLY_PUBLICATION_LAG_DAYS if s["frequency"] == "monthly" else 0
        cutoff = _add_days(as_of, -lag)
        i = bisect.bisect_right(s["dates"], cutoff) - 1
        if i < 0:
            return None
        return {"id": series_id, "label": s["label"], "date": s["dates"][i], "value": s["values"][i], "unit": s["unit"],
                "source": s["source"], "publicationLagDays": lag}

    def fundamentals_as_of(self, ticker: str, as_of: Optional[str] = None) -> Dict[str, dict]:
        """Latest annual value per metric whose 10-K was FILED on or before as_of."""
        as_of = as_of or self.as_of
        best: Dict[str, dict] = {}
        for r in self.fundamentals.get(ticker, []):
            if r["filed"] <= as_of and (r["metric"] not in best or r["period_end"] > best[r["metric"]]["period_end"]):
                best[r["metric"]] = r
        return best

    def news_attention(self, ticker: str, as_of: Optional[str] = None) -> Optional[dict]:
        """Media attention: average share of GDELT articles over the last 3 complete months vs the months before."""
        as_of = as_of or self.as_of
        cur_month = as_of[:7] + "-01"
        rows = sorted(r for r in self.news.get(ticker, []) if r[0] < cur_month)  # complete months only
        if len(rows) < 9:
            return None
        recent, before = rows[-3:], rows[:-3]
        r_avg = sum(x[2] for x in recent) / 3
        b_avg = sum(x[2] for x in before) / len(before)
        return {"recentPpm": round(r_avg, 1), "baselinePpm": round(b_avg, 1), "ratio": round(r_avg / b_avg, 2) if b_avg else None,
                "recentArticles": sum(x[1] for x in recent), "window": [rows[0][0], rows[-1][0]],
                "series": [{"month": m, "articles": a, "sharePpm": v} for m, a, v in rows]}

    def trailing_dividends(self, ticker: str, as_of: Optional[str] = None) -> float:
        as_of = as_of or self.as_of
        start = _add_days(as_of, -365)
        return sum(v for d, v in self.dividends.get(ticker, []) if start < d <= as_of)

    def search(self, q: str, asset_class: Optional[str] = None, limit: int = 10) -> List[Asset]:
        q = q.strip().lower()
        out = []
        for a in self.assets.values():
            if asset_class and a.asset_class != asset_class:
                continue
            if not q or q in a.ticker.lower() or q in a.name.lower():
                out.append(a)
        out.sort(key=lambda a: (not a.ticker.lower().startswith(q), a.ticker))
        return out[:limit]


# ---------------------------------------------------------------------- loading (local or S3)
_lock = threading.Lock()
_store: Optional[DataStore] = None


def _read_local(folder: str) -> Dict[str, str]:
    texts = {}
    for f in FILES:
        p = os.path.join(folder, f)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                texts[f] = fh.read()
    return texts


def _read_s3(bucket: str, prefix: str) -> Dict[str, str]:
    import boto3  # available in the Lambda runtime
    s3 = boto3.client("s3")
    texts = {}
    for f in FILES:
        key = f"{prefix.rstrip('/')}/{f}" if prefix else f
        try:
            texts[f] = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
        except s3.exceptions.NoSuchKey:
            continue
    return texts


def get_store() -> DataStore:
    """Singleton, loaded once per Lambda execution environment (warm invocations reuse it)."""
    global _store
    with _lock:
        if _store is None:
            bucket = os.environ.get("DATA_BUCKET")
            if bucket:
                prefix = os.environ.get("DATA_PREFIX", "dataset")
                texts, origin = _read_s3(bucket, prefix), f"s3://{bucket}/{prefix}"
            else:
                folder = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(__file__), "..", "..", "data", "dataset")
                folder = os.path.abspath(folder)
                texts, origin = _read_local(folder), folder
            missing = [f for f in FILES[:5] if f not in texts]
            if missing:
                raise RuntimeError(f"Dataset incomplete at {origin}: missing {missing}. Run data/build_dataset.py")
            _store = DataStore(texts, origin)
        return _store
