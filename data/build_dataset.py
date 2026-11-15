#!/usr/bin/env python3
"""Rebuild the AlphaForge dataset from public sources (stdlib only, Python >= 3.9).

Outputs (data/dataset/):
  assets_universe.csv     31 assets + ESG activity screen (joined from data/esg_screen.csv)
  prices_daily.csv        date,ticker,open,high,low,close,adj_close,volume,currency
  corporate_actions.csv   ex_date,ticker,action,value,unit
  fx_usdcad_daily.csv     date,usdcad,cadusd                      (Bank of Canada)
  macro_rates.csv         date,series_id,value,unit,label,frequency,source  (BoC + FRED)
  fundamentals_sec.csv    ticker,fiscal_year,period_end,filed,metric,value,unit,form,accession (SEC EDGAR)
  news_attention.csv      month,ticker,articles,share_ppm      (GDELT, media attention signal)
  sources_metadata.csv    one row per source: provider, url, retrieved_at, licence, processing, limits
  data_quality_report.txt gaps, stale prices, missing values

It also copies macro/FX/corporate actions to public/data/ for the Markets page.

Usage:  python3 data/build_dataset.py [--out data/dataset] [--skip-sec]
If you have the official alphaforge_starter/ folder, you can use it instead: the backend
reads the same file names and column names (see backend/alphaforge/data.py).
"""
import argparse
import csv
import datetime as dt
import json
import os
import shutil
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from universe import ASSETS, BOC_SERIES, END, FRED_SERIES, SEC_CONCEPTS, START  # noqa: E402

UA_BROWSER = "Mozilla/5.0 (X11; Linux x86_64) AlphaForge-Datathon/1.0"
# SEC asks automated clients to identify themselves: https://www.sec.gov/os/accessing-edgar-data
UA_SEC = os.environ.get("SEC_USER_AGENT", "AlphaForge Datathon research alphaforge@example.org")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get(url, ua=UA_BROWSER, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            if i == retries - 1:
                raise RuntimeError(f"GET {url} failed: {e}") from e
            time.sleep(1.5 * (i + 1))


def epoch(d):
    return int(dt.datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp())


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------- prices
def fetch_prices(out, report):
    end_excl = (dt.date.fromisoformat(END) + dt.timedelta(days=1)).isoformat()
    prices, actions = [], []
    for ticker, _name, _cls, _mkt, cur, _sec, _cik in ASSETS:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={epoch(START)}"
               f"&period2={epoch(end_excl)}&interval=1d&events=div%2Csplit")
        try:
            d = json.loads(get(url))["chart"]["result"][0]
        except Exception as e:  # noqa: BLE001
            report.append(f"[ERROR] prices {ticker}: {e}")
            continue
        tz = d["meta"].get("gmtoffset", 0)
        q = d["indicators"]["quote"][0]
        adj = d["indicators"].get("adjclose", [{}])[0].get("adjclose", q["close"])
        n_missing = 0
        for i, ts in enumerate(d.get("timestamp", [])):
            day = dt.datetime.utcfromtimestamp(ts + tz).date().isoformat()
            if day < START or day > END:
                continue
            c = q["close"][i]
            if c is None:
                n_missing += 1
                continue
            r = lambda x: "" if x is None else round(x, 6)  # noqa: E731
            prices.append([day, ticker, r(q["open"][i]), r(q["high"][i]), r(q["low"][i]), r(c), r(adj[i]),
                           q["volume"][i] or 0, cur])
        if n_missing:
            report.append(f"[WARN] prices {ticker}: {n_missing} rows with null close dropped")
        ev = d.get("events", {})
        for v in ev.get("dividends", {}).values():
            day = dt.datetime.utcfromtimestamp(v["date"] + tz).date().isoformat()
            actions.append([day, ticker, "dividend", round(v["amount"], 6), f"{cur} per share"])
        for v in ev.get("splits", {}).values():
            day = dt.datetime.utcfromtimestamp(v["date"] + tz).date().isoformat()
            actions.append([day, ticker, "split", round(v["numerator"] / v["denominator"], 6), "ratio"])
        last = max((p[0] for p in prices if p[1] == ticker), default="—")
        if last < END and ticker[-4:] != "-USD":
            gap = (dt.date.fromisoformat(END) - dt.date.fromisoformat(last)).days if last != "—" else 999
            if gap > 4:
                report.append(f"[WARN] prices {ticker}: last observation {last} ({gap} days before {END})")
        time.sleep(0.3)  # be polite with the free endpoint
    prices.sort(key=lambda r: (r[1], r[0]))
    actions.sort(key=lambda r: (r[1], r[0]))
    write_csv(os.path.join(out, "prices_daily.csv"),
              ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume", "currency"], prices)
    write_csv(os.path.join(out, "corporate_actions.csv"), ["ex_date", "ticker", "action", "value", "unit"], actions)
    return len(prices), len(actions)


# ---------------------------------------------------------------- FX + macro
def fetch_boc(ids):
    url = f"https://www.bankofcanada.ca/valet/observations/{','.join(ids)}/json?start_date={START}&end_date={END}"
    return json.loads(get(url))["observations"]


def fetch_fx_macro(out, report):
    obs = fetch_boc(["FXUSDCAD"])
    fx = [[o["d"], o["FXUSDCAD"]["v"], round(1 / float(o["FXUSDCAD"]["v"]), 6)] for o in obs if o.get("FXUSDCAD", {}).get("v")]
    write_csv(os.path.join(out, "fx_usdcad_daily.csv"), ["date", "usdcad", "cadusd"], fx)

    rows = []
    for o in fetch_boc(list(BOC_SERIES)):
        for sid, (label, unit, freq) in BOC_SERIES.items():
            v = o.get(sid, {}).get("v")
            if v not in (None, ""):
                rows.append([o["d"], sid, v, unit, label, freq, "Bank of Canada Valet API"])
    for sid, (label, unit, freq) in FRED_SERIES.items():
        txt = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={START}&coed={END}")
        n_dot = 0
        for r in list(csv.reader(txt.splitlines()))[1:]:
            if len(r) < 2 or r[1] in ("", "."):
                n_dot += 1
                continue
            rows.append([r[0], sid, r[1], unit, label, freq, "FRED, Federal Reserve Bank of St. Louis"])
        if n_dot:
            report.append(f"[INFO] FRED {sid}: {n_dot} missing observations (holidays) skipped")
    rows.sort(key=lambda r: (r[1], r[0]))
    write_csv(os.path.join(out, "macro_rates.csv"), ["date", "series_id", "value", "unit", "label", "frequency", "source"], rows)
    report.append("[INFO] Monthly macro series (CPI, unemployment) are dated by REFERENCE month, not publication date. "
                  "The backend applies a publication lag (see backend/alphaforge/data.py: MONTHLY_PUBLICATION_LAG_DAYS) to avoid look-ahead bias.")
    return len(fx), len(rows)


# ---------------------------------------------------------------- SEC fundamentals
def fetch_sec(out, report):
    rows = []
    for ticker, *_rest, cik in ASSETS:
        if not cik:
            continue
        try:
            facts = json.loads(get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", ua=UA_SEC))
        except Exception as e:  # noqa: BLE001
            report.append(f"[ERROR] SEC {ticker}: {e}")
            continue
        gaap = facts.get("facts", {}).get("us-gaap", {})
        for metric, tags in SEC_CONCEPTS.items():
            picked = None
            for tag in tags:
                units = gaap.get(tag, {}).get("units", {}).get("USD", [])
                annual = [u for u in units if u.get("form") == "10-K" and u.get("fp") == "FY" and u.get("fy")
                          and u.get("end", "") >= "2019-01-01"]
                if annual:
                    picked = (tag, annual)
                    break
            if not picked:
                report.append(f"[WARN] SEC {ticker}: no 10-K value for {metric}")
                continue
            tag, annual = picked
            # Keep one value per period end: the FIRST filing (original, as known at that date -> no restatement look-ahead)
            best = {}
            for u in sorted(annual, key=lambda u: u["filed"]):
                # flows: keep full-year durations only
                if "start" in u:
                    days = (dt.date.fromisoformat(u["end"]) - dt.date.fromisoformat(u["start"])).days
                    if days < 350:
                        continue
                best.setdefault(u["end"], u)
            for end, u in sorted(best.items()):
                rows.append([ticker, end[:4], end, u["filed"], metric, u["val"], "USD", u["form"], u.get("accn", ""), tag])
        time.sleep(0.25)  # SEC fair-access: < 10 requests/second
    write_csv(os.path.join(out, "fundamentals_sec.csv"),
              ["ticker", "fiscal_year", "period_end", "filed", "metric", "value", "unit", "form", "accession", "xbrl_tag"], rows)
    return len(rows)


# ---------------------------------------------------------------- news attention (GDELT)
NEWS_QUERY = {
    "NVDA": "nvidia", "TSLA": "tesla", "AAPL": '"apple inc" OR iphone', "MSFT": "microsoft", "AMZN": "amazon.com OR \"amazon web services\"",
    "GOOGL": "alphabet OR google", "JNJ": '"johnson & johnson"', "PG": '"procter & gamble"', "JPM": "jpmorgan", "XOM": "exxonmobil OR \"exxon mobil\"",
    "RY.TO": '"royal bank of canada"', "TD.TO": '"td bank"', "ENB.TO": "enbridge", "SU.TO": "suncor", "CNR.TO": '"canadian national railway"',
    "SHOP.TO": "shopify", "CSU.TO": '"constellation software"', "BCE.TO": '"bce inc" OR "bell canada"', "ATD.TO": "couche-tard",
    "FTS.TO": '"fortis inc"', "BTC-USD": "bitcoin", "ETH-USD": "ethereum",
}


def fetch_news(out, report):
    """Monthly media attention from the GDELT DOC 2.0 API (article counts, English-language global news).
    share_ppm = articles mentioning the query / all articles monitored by GDELT that month, in parts per million."""
    import urllib.parse
    rows = []
    for t, q in NEWS_QUERY.items():
        url = ("https://api.gdeltproject.org/api/v2/doc/doc?query=" + urllib.parse.quote(f"({q}) sourcelang:english" if " OR " in q else f"{q} sourcelang:english")
               + "&mode=timelinevolraw&format=json&timespan=24m")
        try:
            data = json.loads(get(url))["timeline"][0]["data"]
        except Exception as e:  # noqa: BLE001
            report.append(f"[WARN] GDELT {t}: {e}")
            time.sleep(6)
            continue
        month = {}
        for p in data:
            m = p["date"][:4] + "-" + p["date"][4:6]
            a, n = month.get(m, (0, 0))
            month[m] = (a + p["value"], n + p["norm"])
        for m, (a, n) in sorted(month.items()):
            rows.append([m + "-01", t, a, round(a / n * 1e6, 1) if n else ""])
        time.sleep(6)  # GDELT asks for at most one request every 5 seconds
    write_csv(os.path.join(out, "news_attention.csv"), ["month", "ticker", "articles", "share_ppm"], rows)
    return len(rows)


# ---------------------------------------------------------------- universe + metadata
def write_universe(out):
    esg = {}
    with open(os.path.join(ROOT, "data", "esg_screen.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            esg[r["ticker"]] = r
    rows = []
    for t, name, cls, mkt, cur, sector, _cik in ASSETS:
        e = esg.get(t, {})
        rows.append([t, name, cls, mkt, cur, sector, e.get("esg_screen", "unknown"), e.get("activity_tags", ""),
                     e.get("rationale", ""), e.get("evidence_source", "")])
    write_csv(os.path.join(out, "assets_universe.csv"),
              ["ticker", "name", "asset_class", "market", "currency", "sector", "esg_screen", "esg_activity_tags",
               "esg_rationale", "esg_evidence_source"], rows)


def write_sources(out, stats):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [
        ["prices_daily.csv", "Yahoo Finance chart endpoint (query1.finance.yahoo.com/v8/finance/chart)", now,
         f"{START}..{END}", "daily", "Personal/research use under Yahoo terms; raw data is not redistributed beyond the team repo",
         "Close and split/dividend-adjusted close kept; null closes dropped; dates converted to exchange local time",
         "Free provider, no SLA; adjusted close is provider-computed; crypto trades 24/7 so has weekend rows", stats.get("prices", "")],
        ["corporate_actions.csv", "Yahoo Finance chart endpoint (events=div,split)", now, f"{START}..{END}", "event",
         "Same as prices", "Dividends per share in quote currency; split ratio numerator/denominator", "Ex-dates only, no record/pay dates", stats.get("actions", "")],
        ["fx_usdcad_daily.csv", "Bank of Canada Valet API, series FXUSDCAD", now, f"{START}..{END}", "business daily",
         "Bank of Canada terms of use (https://www.bankofcanada.ca/terms/) - free reuse with attribution",
         "cadusd = 1/usdcad", "Published once per business day; no weekend values (forward-filled in backend for crypto)", stats.get("fx", "")],
        ["macro_rates.csv", "Bank of Canada Valet API + FRED (St. Louis Fed)", now, f"{START}..{END}", "daily / monthly",
         "BoC terms (attribution); FRED: public-domain US government series, cite FRED",
         "Long format; FRED '.' placeholders dropped",
         "Monthly series dated by reference month; publication lag applied in backend to avoid look-ahead", stats.get("macro", "")],
        ["fundamentals_sec.csv", "SEC EDGAR XBRL companyfacts API (data.sec.gov)", now, "FY2019+", "annual (10-K)",
         "US government public data; SEC fair-access policy (declared User-Agent, <10 req/s)",
         "10-K, fiscal-year values only; FIRST filing kept per period (as-filed, no restatements); 'filed' = publication date",
         "US filers only (no Canadian issuers: SEDAR+ has no free structured API); tag choice may differ by company", stats.get("sec", "")],
        ["news_attention.csv", "GDELT Project DOC 2.0 API (api.gdeltproject.org), mode timelinevolraw", now, "last 24 months", "monthly (from daily)",
         "GDELT: free and open for any use with citation of the GDELT Project",
         "Daily article counts summed per month; share_ppm = matching articles / all monitored articles x 1e6",
         "English-language sources only; keyword queries can catch homonyms (e.g. Amazon river, Apple fruit); attention is not sentiment", stats.get("news", "")],
        ["assets_universe.csv / esg_screen.csv", "Team-curated from issuer annual reports and ETF fact sheets (see esg_evidence_source column)",
         now, "as of 2026-11", "static", "Our own work (MIT)",
         "Activity-based screen: leader / neutral / watch / exclude_candidate + activity tags",
         "NOT a third-party ESG rating; binary activity tags ignore degree of involvement; subject to curator judgement", "31"],
    ]
    write_csv(os.path.join(out, "sources_metadata.csv"),
              ["file", "provider", "retrieved_at", "coverage", "frequency", "licence_terms", "processing", "limitations", "rows"], rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "dataset"))
    ap.add_argument("--skip-sec", action="store_true")
    ap.add_argument("--skip-news", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    report, stats = [], {}
    print("universe…"); write_universe(a.out)
    print("prices…"); stats["prices"], stats["actions"] = fetch_prices(a.out, report)
    print("fx + macro…"); stats["fx"], stats["macro"] = fetch_fx_macro(a.out, report)
    if not a.skip_sec:
        print("SEC fundamentals…"); stats["sec"] = fetch_sec(a.out, report)
    if not a.skip_news:
        print("GDELT news attention… (~3 min, rate-limited)"); stats["news"] = fetch_news(a.out, report)
    write_sources(a.out, stats)
    with open(os.path.join(a.out, "data_quality_report.txt"), "w", encoding="utf-8") as f:
        f.write(f"AlphaForge data quality report - built {dt.datetime.now(dt.timezone.utc).isoformat()}\n")
        f.write(f"Window {START}..{END}. Rows: {json.dumps(stats)}\n")
        f.write("\n".join(report) if report else "No warnings.")
        f.write("\n")
    pub = os.path.join(ROOT, "public", "data")
    os.makedirs(pub, exist_ok=True)
    for src, dst in [("macro_rates.csv", "macro-rates.csv"), ("fx_usdcad_daily.csv", "fx-usdcad-daily.csv"),
                     ("corporate_actions.csv", "corporate-actions.csv"), ("data_quality_report.txt", "data-quality-warnings.txt"),
                     ("sources_metadata.csv", "sources-metadata.csv")]:
        shutil.copyfile(os.path.join(a.out, src), os.path.join(pub, dst))
    print(json.dumps(stats), f"{len(report)} report lines")


if __name__ == "__main__":
    main()
