import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, errorText } from "../api/errors";
import { getSummary, listPortfolios, putHoldings, searchAssets } from "../api/endpoints";
import type { Asset, Holding, Portfolio, PortfolioSummary, Slice, SummaryRange } from "../api/types";
import AppHeader from "../components/AppHeader";
import Chart from "../components/Chart";
import Explanation from "../components/Explanation";
import { amount, money, pct, plainPct, shortDate, signedAmount, toSeconds } from "../lib/format";

const RANGES: { key: SummaryRange; label: string }[] = [
  { key: "1m", label: "1 M" }, { key: "6m", label: "6 M" }, { key: "1y", label: "1 A" }, { key: "5y", label: "5 A" },
];
const PALETTE = ["var(--red)", "#f3a3a6", "#111318", "#6b7280", "#d6d9de", "#a1a6b0", "#c3141a"];

type Row = { key: number; ticker: string; quantity: string; avgCost: string };
let rowKey = 0;
const toRows = (h: Holding[]): Row[] => h.map((x) => ({ key: ++rowKey, ticker: x.ticker, quantity: String(x.quantity), avgCost: String(x.avgCost) }));
const num = (s: string) => (s.trim() === "" ? NaN : Number(s.replace(",", ".")));

/** Convertit les lignes saisies en positions du contrat (ou retourne un message d'erreur). */
function parseRows(rows: Row[]): { holdings: Holding[] } | { error: string } {
  const seen = new Set<string>();
  const holdings: Holding[] = [];
  for (const [i, r] of rows.entries()) {
    const ticker = r.ticker.trim().toUpperCase(), quantity = num(r.quantity), avgCost = num(r.avgCost);
    const n = `Ligne ${i + 1}`;
    if (!ticker) return { error: `${n} : ticker requis.` };
    if (seen.has(ticker)) return { error: `${n} : ${ticker} apparaît deux fois.` };
    if (!(quantity > 0)) return { error: `${n} : la quantité doit être supérieure à 0.` };
    if (!Number.isFinite(avgCost) || avgCost < 0) return { error: `${n} : prix de revient moyen invalide.` };
    seen.add(ticker);
    holdings.push({ ticker, quantity, avgCost });
  }
  return { holdings };
}

function Alloc({ title, items }: { title: string; items: Slice[] }) {
  return (
    <section>
      <h2 className="section-title">{title}</h2>
      {items.length === 0 ? <div className="empty"><strong>Aucune donnée</strong></div> : (
        <>
          <div className="alloc-bar">{items.filter((a) => a.weight > 0).map((a, i) => <span key={a.label} style={{ width: `${a.weight}%`, background: PALETTE[i % PALETTE.length] }} title={`${a.label} ${plainPct(a.weight)}`} />)}</div>
          <ul className="legend">{items.map((a, i) => <li key={a.label}><span className="dot" style={{ background: PALETTE[i % PALETTE.length] }} />{a.label}<span className="pct filled">{plainPct(a.weight)}</span></li>)}</ul>
        </>
      )}
    </section>
  );
}

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [range, setRange] = useState<SummaryRange>("1y");
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [sumLoading, setSumLoading] = useState(false);
  const [error, setError] = useState("");
  const [sumError, setSumError] = useState("");
  const [saveErr, setSaveErr] = useState("");
  const [saving, setSaving] = useState(false);
  const [suggestions, setSuggestions] = useState<Asset[]>([]);
  const [info, setInfo] = useState<Record<string, Asset>>({});
  const searchSeq = useRef<AbortController | null>(null);
  const timer = useRef<number>();
  const sumSeq = useRef(0);

  useEffect(() => {
    listPortfolios()
      .then(({ items }) => {
        const p = items.find((x) => x.portfolioId === "main") ?? items[0];
        if (!p) return setError("Aucun portefeuille.");
        setPortfolio(p); setRows(toRows(p.holdings));
      })
      .catch((e) => setError(errorText(e)))
      .finally(() => setLoading(false));
  }, []);

  const loadSummary = useCallback(async (p: Portfolio, r: SummaryRange) => {
    const seq = ++sumSeq.current;
    if (p.holdings.length === 0) { setSummary(null); setSumError(""); return; }
    setSumLoading(true); setSumError("");
    try {
      const s = await getSummary(p.portfolioId, r);
      if (seq === sumSeq.current) setSummary(s);
    } catch (e) {
      if (seq === sumSeq.current) { setSummary(null); setSumError(errorText(e)); }
    } finally {
      if (seq === sumSeq.current) setSumLoading(false);
    }
  }, []);

  useEffect(() => { if (portfolio) void loadSummary(portfolio, range); }, [portfolio, range, loadSummary]);

  const currencyOf = useMemo(() => {
    const m: Record<string, string> = {};
    for (const [t, a] of Object.entries(info)) if (a.currency) m[t] = a.currency;
    for (const h of summary?.holdings ?? []) m[h.ticker] = h.currency;
    return m;
  }, [info, summary]);

  function onTicker(key: number, value: string) {
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ticker: value } : r)));
    window.clearTimeout(timer.current);
    searchSeq.current?.abort();
    const q = value.trim();
    if (q.length < 1) return setSuggestions([]);
    timer.current = window.setTimeout(() => {
      const ctl = new AbortController();
      searchSeq.current = ctl;
      searchAssets(q, undefined, ctl.signal)
        .then(({ items }) => {
          setSuggestions(items);
          setInfo((m) => ({ ...m, ...Object.fromEntries(items.map((a) => [a.ticker, a])) }));
        })
        .catch(() => {}); // l'autocomplétion est une aide : une erreur ne bloque pas la saisie
    }, 250);
  }

  const parsed = parseRows(rows);
  const norm = (h: Holding[]) => JSON.stringify(h.map((x) => [x.ticker, x.quantity, x.avgCost]));
  const dirty = portfolio ? !("holdings" in parsed) || norm(parsed.holdings) !== norm(portfolio.holdings) : false;

  async function save() {
    if (!portfolio) return;
    const r = parseRows(rows);
    if ("error" in r) return setSaveErr(r.error);
    setSaving(true); setSaveErr("");
    try {
      const p = await putHoldings(portfolio.portfolioId, r.holdings); // état complet de la table
      setPortfolio(p); setRows(toRows(p.holdings));
    } catch (e) {
      setSaveErr(e instanceof ApiError && e.code === "ASSET_NOT_FOUND" && e.message ? e.message : errorText(e));
    } finally {
      setSaving(false);
    }
  }

  const chart = useMemo(() => {
    const pts = summary?.performance.points ?? [];
    return pts.length > 1 ? { values: pts.map((p) => p.value), timestamps: pts.map((p) => toSeconds(p.date)) } : null;
  }, [summary]);

  if (loading) return <><AppHeader /><main className="wrap"><p className="muted" style={{ padding: "48px 0" }}>Chargement…</p></main></>;
  if (!portfolio) return <><AppHeader /><main className="wrap"><p className="error" role="alert" style={{ padding: "48px 0" }}>{error}</p></main></>;

  const cur = summary?.baseCurrency ?? portfolio.baseCurrency;
  const t = summary?.totals;

  return (
    <>
      <AppHeader />
      <main className="wrap">
        <section className="hero">
          <div>
            <div className="eyebrow">{portfolio.name}<span className="tag">Simulation seulement</span></div>
            <div className="big filled">{t ? money(t.value) : "—"}<small>{cur}</small></div>
            {t && <div className={`sub ${t.dayChange >= 0 ? "up" : "down"}`}>{signedAmount(t.dayChange, cur)} ({pct(t.dayChangePct)}) <span>jour · au {summary!.asOf}</span></div>}
          </div>
          <div className="controls">
            <div className="segmented" role="group" aria-label="Période">
              {RANGES.map((r) => <button key={r.key} type="button" className={r.key === range ? "on" : undefined} aria-pressed={r.key === range} onClick={() => setRange(r.key)}>{r.label}</button>)}
            </div>
          </div>
        </section>

        {sumError && <p className="error" role="alert" style={{ marginBottom: 16 }}>{sumError}</p>}
        {sumLoading && <p className="muted small">Calcul en cours…</p>}
        {!!summary?.warnings?.length && <div className="banner warn" role="status">{summary.warnings.map((w, i) => <p key={i}>{w}</p>)}</div>}

        {summary && (
          <>
            <section className="chart" aria-label="Évolution de la valeur">
              {chart
                ? <Chart key={range} values={chart.values} timestamps={chart.timestamps} axisLabel={(ts) => shortDate(ts, range === "1y" || range === "5y")} format={(v) => amount(v, cur)} />
                : <div className="chart-empty"><p>Pas assez de points pour tracer la performance.</p></div>}
            </section>
            <section className="stats">
              <div className="stat"><div className="stat-label">Valeur investie (coût)</div><div className="stat-value filled">{amount(summary.totals.cost, cur, 0)}</div></div>
              <div className="stat"><div className="stat-label">Gain / perte</div><div className={`stat-value filled ${summary.totals.pnl >= 0 ? "up" : "down"}`}>{signedAmount(summary.totals.pnl, cur)}</div><div className="stat-sub">{pct(summary.totals.pnlPct)}</div></div>
              <div className="stat"><div className="stat-label">Volatilité annualisée</div><div className="stat-value filled">{plainPct(summary.risk.volatility, 2)}</div></div>
              <div className="stat"><div className="stat-label">Baisse maximale ({summary.performance.range})</div><div className="stat-value filled">{plainPct(summary.risk.maxDrawdown, 2)}</div></div>
            </section>

            <div className="grid2">
              <Alloc title="Classes d'actifs" items={summary.allocation.byAssetClass} />
              <Alloc title="Secteurs" items={summary.allocation.bySector} />
            </div>
            <div className="grid2" style={{ paddingTop: 0 }}>
              <Alloc title="Devises" items={summary.allocation.byCurrency} />
              <div />
            </div>

            <section style={{ padding: "8px 0 32px" }}>
              <h2 className="section-title">Positions enrichies</h2>
              <div className="table-wrap">
                <table className="tbl">
                  <thead><tr><th>Titre</th><th>Quantité</th><th>Prix</th><th>Valeur ({cur})</th><th>Poids</th><th>Gain / perte</th><th>Jour</th></tr></thead>
                  <tbody>
                    {summary.holdings.map((h) => (
                      <tr key={h.ticker}>
                        <td><strong>{h.ticker}</strong> {h.stale && <span className="badge warn" title="Dernier cours connu utilisé">cours ancien</span>}<br /><span className="muted small">{h.name} · {h.assetClass}{h.sector ? ` · ${h.sector}` : ""}</span></td>
                        <td>{money(h.quantity, 4).replace(/,?0+$/, "")}</td>
                        <td>{amount(h.price, h.currency)}</td>
                        <td>{money(h.value)}</td>
                        <td>{plainPct(h.weight)}</td>
                        <td className={h.pnl >= 0 ? "up" : "down"}>{signedAmount(h.pnl, cur)}<br /><span className="small">{pct(h.pnlPct)}</span></td>
                        <td className={h.dayChangePct >= 0 ? "up" : "down"}>{pct(h.dayChangePct)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {summary.explanation && <div style={{ paddingBottom: 32 }}><Explanation data={summary.explanation} defaultOpen /></div>}
          </>
        )}

        <section style={{ padding: "8px 0 48px" }}>
          <div className="section-row"><h2 className="section-title">Modifier mes positions</h2><span className="muted small">Mis à jour : {new Date(portfolio.updatedAt).toLocaleString("fr-CA")}</span></div>
          <p className="muted small" style={{ marginBottom: 12 }}>Le prix de revient moyen est exprimé dans la devise de cotation de l'actif (.TO = CAD, les autres = USD). Enregistrer remplace toute la liste. Aucun ordre n'est exécuté.</p>
          <datalist id="tickers">{suggestions.map((a) => <option key={a.ticker} value={a.ticker}>{a.name}</option>)}</datalist>
          <div className="table-wrap">
            <table className="tbl edit">
              <thead><tr><th>Ticker</th><th>Quantité</th><th>Prix de revient moyen</th><th /></tr></thead>
              <tbody>
                {rows.map((r) => {
                  const k = r.ticker.trim().toUpperCase();
                  return (
                    <tr key={r.key}>
                      <td><input className="cell" list="tickers" aria-label="Ticker" value={r.ticker} onChange={(e) => onTicker(r.key, e.target.value)} placeholder="ex. RY.TO" autoComplete="off" /><span className="muted small">{info[k]?.name ?? summary?.holdings.find((h) => h.ticker === k)?.name ?? ""}</span></td>
                      <td><input className="cell" inputMode="decimal" aria-label="Quantité" value={r.quantity} onChange={(e) => setRows((rs) => rs.map((x) => (x.key === r.key ? { ...x, quantity: e.target.value } : x)))} /></td>
                      <td><input className="cell" inputMode="decimal" aria-label="Prix de revient moyen" value={r.avgCost} onChange={(e) => setRows((rs) => rs.map((x) => (x.key === r.key ? { ...x, avgCost: e.target.value } : x)))} /> <span className="muted small">{currencyOf[k] ?? ""}</span></td>
                      <td><button type="button" className="link" onClick={() => setRows((rs) => rs.filter((x) => x.key !== r.key))}>Retirer</button></td>
                    </tr>
                  );
                })}
                {rows.length === 0 && <tr><td colSpan={4} className="muted">Aucune position.</td></tr>}
              </tbody>
            </table>
          </div>
          {saveErr && <p className="error" role="alert" style={{ marginTop: 12 }}>{saveErr}</p>}
          <div className="actions-row" style={{ marginTop: 16 }}>
            <button type="button" className="btn-ghost" onClick={() => setRows((rs) => [...rs, { key: ++rowKey, ticker: "", quantity: "", avgCost: "" }])}>+ Ajouter une position</button>
            <button type="button" className="btn" disabled={!dirty || saving} onClick={() => void save()}>{saving ? "Enregistrement…" : "Enregistrer"}</button>
            {dirty && <button type="button" className="link" onClick={() => { setRows(toRows(portfolio.holdings)); setSaveErr(""); }}>Annuler les changements</button>}
          </div>
        </section>
      </main>
      <footer className="footer"><div className="wrap footer-row"><span>Simulation seulement : aucune transaction n'est exécutée et rien ici ne constitue un conseil financier personnalisé. Le rendement passé ne prédit pas le futur. Tous les chiffres sont calculés par le serveur.</span></div></footer>
    </>
  );
}
