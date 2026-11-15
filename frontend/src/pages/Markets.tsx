import { useEffect, useMemo, useState } from "react";
import AppHeader from "../components/AppHeader";
import Chart from "../components/Chart";
import MultiChart, { type Line } from "../components/MultiChart";
import { bollinger, drawdown, macd, rollingVol, rsi, sma, withDerived } from "../lib/analysis";
import { parseCsv, toCsv, toSeries, type Series, type SeriesPoint } from "../lib/csv";
import { money, plainPct, shortDate, toSeconds } from "../lib/format";

const FILES = ["/data/macro-rates.csv", "/data/fx-usdcad-daily.csv", "/data/corporate-actions.csv", "/data/data-quality-warnings.txt"];
type Range = "1m" | "6m" | "1y" | "5y" | "all";
type Tab = "serie" | "technique" | "macro" | "actions";
const RANGES: { key: Range; label: string; months: number }[] = [
  { key: "1m", label: "1 M", months: 1 }, { key: "6m", label: "6 M", months: 6 },
  { key: "1y", label: "1 A", months: 12 }, { key: "5y", label: "5 A", months: 60 }, { key: "all", label: "Tout", months: 0 },
];
type Action = { date: string; ticker: string; action: string; value: number; unit: string };

const shift = (date: string, months: number) => {
  const d = new Date(`${date}T12:00:00Z`);
  d.setUTCMonth(d.getUTCMonth() + months);
  return d.toISOString().slice(0, 10);
};
const isPct = (s: Series) => s.unit === "percent";
const fmt = (v: number, s: Series) => (isPct(s) ? plainPct(v, 2) : money(v, 4));
const num = (v: number, d = 2) => (Number.isFinite(v) ? money(v, d) : "—");
/** Dernière valeur à une date <= d (points triés). */
function valueAt(pts: SeriesPoint[], d: string) {
  let r: SeriesPoint | undefined;
  for (const p of pts) { if (p.date <= d) r = p; else break; }
  return r?.value;
}

export default function Markets() {
  const [series, setSeries] = useState<Series[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [warnings, setWarnings] = useState("");
  const [id, setId] = useState("");
  const [ticker, setTicker] = useState("");
  const [range, setRange] = useState<Range>("1y");
  const [tab, setTab] = useState<Tab>("serie");
  const [ind, setInd] = useState({ sma20: true, sma50: true, sma200: false, boll: false });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function ingest(texts: string[]) {
    const merged = new Map<string, Series>();
    const acts: Action[] = [];
    let warn = "";
    for (const t of texts) {
      const head = t.split(/\r?\n/, 1)[0];
      if (head.includes("ex_date")) {
        for (const r of parseCsv(t)) acts.push({ date: r.ex_date, ticker: r.ticker, action: r.action, value: Number(r.value), unit: r.unit });
      } else if (head.startsWith("date,")) {
        for (const s of toSeries(parseCsv(t))) merged.set(s.id, s);
      } else warn = t.trim();
    }
    if (merged.size) {
      const list = withDerived([...merged.values()]).sort((a, b) => a.label.localeCompare(b.label, "fr"));
      setSeries(list);
      setId((cur) => (list.some((s) => s.id === cur) ? cur : list[0].id));
    }
    if (acts.length) { setActions(acts); setTicker((c) => c || acts[0].ticker); }
    if (warn) setWarnings(warn);
  }

  useEffect(() => {
    Promise.all(FILES.map((f) => fetch(f).then((r) => (r.ok ? r.text() : "")).catch(() => "")))
      .then((texts) => {
        const ok = texts.filter((t) => t && !t.trimStart().startsWith("<"));
        if (ok.length) ingest(ok); else setError("Aucun fichier trouvé dans public/data. Importez vos CSV avec le bouton ci-dessous.");
      })
      .finally(() => setLoading(false));
  }, []);

  async function onUpload(files: FileList | null) {
    if (!files?.length) return;
    ingest(await Promise.all([...files].map((f) => f.text())));
    setError("");
  }

  const s = series.find((x) => x.id === id);
  const startIdx = useMemo(() => {
    if (!s?.points.length) return 0;
    const m = RANGES.find((r) => r.key === range)!.months;
    if (!m) return 0;
    const from = shift(s.points[s.points.length - 1].date, -m);
    const i = s.points.findIndex((p) => p.date >= from);
    return i < 0 ? 0 : i;
  }, [s, range]);
  const pts = useMemo(() => s?.points.slice(startIdx) ?? [], [s, startIdx]);

  const stats = useMemo(() => {
    if (!pts.length) return null;
    const v = pts.map((p) => p.value), first = v[0], last = v[v.length - 1];
    return { last, min: Math.min(...v), max: Math.max(...v), avg: v.reduce((a, b) => a + b, 0) / v.length, change: last - first, changePct: first ? ((last - first) / Math.abs(first)) * 100 : NaN };
  }, [pts]);

  /* Indicateurs calculés sur toute la série (amorçage), puis tronqués à la période. */
  const tech = useMemo(() => {
    if (!s || s.points.length < 30) return null;
    const v = s.points.map((p) => p.value);
    const cut = (a: number[]) => a.slice(startIdx);
    return {
      price: cut(v), s20: cut(sma(v, 20)), s50: cut(sma(v, 50)), s200: cut(sma(v, 200)), bb: (() => { const b = bollinger(v); return { u: cut(b.upper), l: cut(b.lower), m: cut(b.mid) }; })(),
      rsi: cut(rsi(v)), macd: (() => { const m = macd(v); return { l: cut(m.line), s: cut(m.signal), h: cut(m.hist) }; })(),
      vol: cut(rollingVol(v)), dd: cut(drawdown(v.slice(startIdx))),
    };
  }, [s, startIdx]);

  const ts = pts.map((p) => toSeconds(p.date));
  const long = range === "1y" || range === "5y" || range === "all";
  const axis = (t: number) => shortDate(t, long);

  const signals = useMemo(() => {
    if (!tech) return [];
    const L = <T,>(a: T[]) => a[a.length - 1];
    const out: [string, string][] = [];
    const r = L(tech.rsi), p = L(tech.price), a50 = L(tech.s50), a200 = L(tech.s200);
    if (Number.isFinite(r)) out.push([`RSI (14) : ${num(r, 1)}`, r > 70 ? "zone de surachat" : r < 30 ? "zone de survente" : "zone neutre"]);
    if (Number.isFinite(a50)) out.push([`Prix vs MM50 : ${num(p, 4)} / ${num(a50, 4)}`, p >= a50 ? "au-dessus (tendance haussière à court terme)" : "en dessous (tendance baissière à court terme)"]);
    if (Number.isFinite(a200) && Number.isFinite(a50)) out.push([`MM50 vs MM200`, a50 >= a200 ? "MM50 au-dessus de la MM200 (« golden cross » en vigueur)" : "MM50 sous la MM200 (« death cross » en vigueur)"]);
    const ml = L(tech.macd.l), ms = L(tech.macd.s);
    if (Number.isFinite(ml) && Number.isFinite(ms)) out.push([`MACD : ${num(ml, 4)} / signal ${num(ms, 4)}`, ml >= ms ? "momentum haussier" : "momentum baissier"]);
    const bu = L(tech.bb.u), bl = L(tech.bb.l);
    if (Number.isFinite(bu)) out.push(["Bandes de Bollinger (20, 2)", p > bu ? "prix au-dessus de la bande haute" : p < bl ? "prix sous la bande basse" : "prix dans les bandes"]);
    return out;
  }, [tech]);

  const macroRows = useMemo(() => series.map((x) => {
    const last = x.points[x.points.length - 1];
    if (!last) return null;
    const m1 = valueAt(x.points, shift(last.date, -1)), y1 = valueAt(x.points, shift(last.date, -12));
    return { x, last, d1m: m1 === undefined ? NaN : last.value - m1, d1y: y1 === undefined ? NaN : last.value - y1 };
  }).filter((r): r is NonNullable<typeof r> => !!r), [series]);

  function download() {
    if (!s) return;
    const url = URL.createObjectURL(new Blob([toCsv(s, pts)], { type: "text/csv" }));
    Object.assign(document.createElement("a"), { href: url, download: `${s.id}_${range}.csv` }).click();
    URL.revokeObjectURL(url);
  }

  /* ----- Dividendes / splits ----- */
  const tickers = useMemo(() => [...new Set(actions.map((a) => a.ticker))].sort(), [actions]);
  const mine = useMemo(() => actions.filter((a) => a.ticker === ticker).sort((a, b) => (a.date < b.date ? -1 : 1)), [actions, ticker]);
  const divs = mine.filter((a) => a.action === "dividend");
  const splits = mine.filter((a) => a.action === "split");
  const byYear = useMemo(() => {
    const m = new Map<string, number>();
    for (const d of divs) m.set(d.date.slice(0, 4), (m.get(d.date.slice(0, 4)) ?? 0) + d.value);
    return [...m.entries()];
  }, [divs]);
  const cagr = useMemo(() => {
    // Années complètes seulement : on exclut la première et la dernière année (potentiellement partielles).
    const full = byYear.slice(1, -1);
    if (full.length < 2) return NaN;
    const [y0, v0] = full[0], [y1, v1] = full[full.length - 1];
    return v0 > 0 ? ((v1 / v0) ** (1 / (Number(y1) - Number(y0))) - 1) * 100 : NaN;
  }, [byYear]);

  const tabs: { key: Tab; label: string }[] = [
    { key: "serie", label: "Série" }, { key: "technique", label: "Technique" },
    { key: "macro", label: "Tableau macro" }, { key: "actions", label: "Dividendes et splits" },
  ];
  const showSelector = tab === "serie" || tab === "technique";
  const lineOf = (label: string, values: number[], color: string, extra: Partial<Line> = {}): Line => ({ label, values, color, ...extra });

  return (
    <>
      <AppHeader />
      <main className="wrap">
        <section className="hero">
          <div>
            <div className="eyebrow">Marchés et analyse<span className="tag">Données publiques</span></div>
            <div className="big filled" style={{ fontSize: 28 }}>{tab === "actions" ? ticker || "—" : tab === "macro" ? "Tableau de bord macro" : s?.label ?? "—"}</div>
            {s && showSelector && <div className="sub">{s.frequency}{s.source ? ` · ${s.source}` : ""}</div>}
          </div>
          {showSelector && (
            <div className="controls">
              <div className="segmented" role="group" aria-label="Période">
                {RANGES.map((r) => <button key={r.key} type="button" className={r.key === range ? "on" : undefined} aria-pressed={r.key === range} onClick={() => setRange(r.key)}>{r.label}</button>)}
              </div>
            </div>
          )}
        </section>

        {loading && <p className="muted small">Chargement…</p>}
        {error && <div className="banner warn" role="status"><p>{error}</p></div>}
        {warnings && <div className={`banner${/no warnings/i.test(warnings) ? "" : " warn"}`} role="status"><p><strong>Qualité des données :</strong> {warnings.replace(/\n+/g, " ")}</p></div>}

        <section style={{ padding: "8px 0 16px" }}>
          <div className="segmented" role="tablist" aria-label="Analyses" style={{ marginBottom: 12 }}>
            {tabs.map((t) => <button key={t.key} type="button" role="tab" className={t.key === tab ? "on" : undefined} aria-selected={t.key === tab} onClick={() => setTab(t.key)}>{t.label}</button>)}
          </div>
          <div className="actions-row">
            {showSelector && (
              <label className="muted small">Série{" "}
                <select value={id} onChange={(e) => setId(e.target.value)} disabled={!series.length}>
                  {series.map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
                </select>
              </label>
            )}
            {tab === "actions" && (
              <label className="muted small">Titre{" "}
                <select value={ticker} onChange={(e) => setTicker(e.target.value)} disabled={!tickers.length}>
                  {tickers.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
            )}
            <label className="btn-ghost" style={{ cursor: "pointer" }}>Importer des fichiers
              <input type="file" accept=".csv,.txt,text/csv,text/plain" multiple hidden onChange={(e) => void onUpload(e.target.files)} />
            </label>
            {showSelector && <button type="button" className="btn-ghost" disabled={!pts.length} onClick={download}>Exporter (CSV)</button>}
          </div>
        </section>

        {tab === "serie" && s && stats && (
          <>
            <section className="chart" aria-label={s.label}>
              {pts.length > 1
                ? <Chart key={`${id}-${range}`} values={pts.map((p) => p.value)} timestamps={ts} axisLabel={axis} format={(v) => fmt(v, s)} />
                : <div className="chart-empty"><p>Pas assez de points pour tracer la série.</p></div>}
            </section>
            <section className="stats">
              <div className="stat"><div className="stat-label">Dernière valeur</div><div className="stat-value filled">{fmt(stats.last, s)}</div><div className="stat-sub">{pts[pts.length - 1].date}</div></div>
              <div className="stat"><div className="stat-label">Variation sur la période</div><div className={`stat-value filled ${stats.change >= 0 ? "up" : "down"}`}>{(stats.change >= 0 ? "+" : "−") + money(Math.abs(stats.change), isPct(s) ? 2 : 4)}</div><div className="stat-sub">{Number.isFinite(stats.changePct) ? (stats.changePct >= 0 ? "+" : "−") + money(Math.abs(stats.changePct), 2) + " %" : ""}</div></div>
              <div className="stat"><div className="stat-label">Min / Max</div><div className="stat-value filled" style={{ fontSize: 20 }}>{fmt(stats.min, s)} / {fmt(stats.max, s)}</div></div>
              <div className="stat"><div className="stat-label">Moyenne</div><div className="stat-value filled">{fmt(stats.avg, s)}</div><div className="stat-sub">{pts.length} observations</div></div>
            </section>
          </>
        )}

        {tab === "technique" && s && (
          !tech ? <p className="muted">Pas assez d'observations (30 minimum) pour les indicateurs.</p> : (
            <>
              <div className="actions-row" style={{ marginBottom: 12 }}>
                {([["sma20", "MM 20"], ["sma50", "MM 50"], ["sma200", "MM 200"], ["boll", "Bollinger (20, 2)"]] as const).map(([k, l]) => (
                  <label key={k} className="small"><input type="checkbox" checked={ind[k]} onChange={(e) => setInd({ ...ind, [k]: e.target.checked })} /> {l}</label>
                ))}
              </div>
              <section className="chart" aria-label="Prix et moyennes mobiles">
                <MultiChart timestamps={ts} axisLabel={axis} format={(v) => fmt(v, s)} lines={[
                  lineOf("Valeur", tech.price, "#111318", { width: 2.25 }),
                  ...(ind.sma20 ? [lineOf("MM 20", tech.s20, "#e41c23")] : []),
                  ...(ind.sma50 ? [lineOf("MM 50", tech.s50, "#f3a3a6")] : []),
                  ...(ind.sma200 ? [lineOf("MM 200", tech.s200, "#6b7280")] : []),
                  ...(ind.boll ? [lineOf("Bollinger haute", tech.bb.u, "#a1a6b0", { dash: "4 4" }), lineOf("Bollinger basse", tech.bb.l, "#a1a6b0", { dash: "4 4" })] : []),
                ]} />
              </section>
              <h2 className="section-title">RSI (14)</h2>
              <section className="chart"><MultiChart height={140} timestamps={ts} axisLabel={axis} format={(v) => num(v, 1)} guides={[30, 70]} lines={[lineOf("RSI", tech.rsi, "#e41c23")]} /></section>
              <h2 className="section-title">MACD (12, 26, 9)</h2>
              <section className="chart"><MultiChart height={160} timestamps={ts} axisLabel={axis} format={(v) => num(v, 4)} guides={[0]} lines={[lineOf("MACD", tech.macd.l, "#111318"), lineOf("Signal", tech.macd.s, "#e41c23"), lineOf("Histogramme", tech.macd.h, "#a1a6b0", { dash: "2 3" })]} /></section>
              <div className="grid2">
                <section>
                  <h2 className="section-title">Volatilité annualisée (20 j, %)</h2>
                  <MultiChart height={140} timestamps={ts} axisLabel={axis} format={(v) => plainPct(v, 1)} lines={[lineOf("Volatilité", tech.vol, "#6b7280")]} />
                </section>
                <section>
                  <h2 className="section-title">Baisse depuis le sommet (%)</h2>
                  <MultiChart height={140} timestamps={ts} axisLabel={axis} format={(v) => plainPct(v, 1)} lines={[lineOf("Drawdown", tech.dd, "#e41c23")]} />
                </section>
              </div>
              <section style={{ padding: "8px 0 32px" }}>
                <h2 className="section-title">Signaux (dernière observation)</h2>
                <div className="table-wrap"><table className="tbl"><tbody>{signals.map(([a, b]) => <tr key={a}><td>{a}</td><td>{b}</td></tr>)}</tbody></table></div>
                <p className="muted small" style={{ marginTop: 8 }}>Indicateurs descriptifs calculés sur l'historique : ils ne prédisent rien. Pour les taux, une « tendance » n'a pas la même signification que pour un prix.</p>
              </section>
            </>
          )
        )}

        {tab === "macro" && (
          <section style={{ padding: "8px 0 32px" }}>
            <div className="table-wrap">
              <table className="tbl">
                <thead><tr><th>Série</th><th>Date</th><th>Dernière valeur</th><th>Δ 1 mois</th><th>Δ 12 mois</th><th>Lecture</th></tr></thead>
                <tbody>
                  {macroRows.map(({ x, last, d1m, d1y }) => (
                    <tr key={x.id} style={{ cursor: "pointer" }} onClick={() => { setId(x.id); setTab("serie"); }}>
                      <td><strong>{x.label}</strong><br /><span className="muted small">{x.frequency}</span></td>
                      <td>{last.date}</td>
                      <td>{fmt(last.value, x)}</td>
                      <td className={d1m >= 0 ? "up" : "down"}>{Number.isFinite(d1m) ? (d1m >= 0 ? "+" : "−") + money(Math.abs(d1m), isPct(x) ? 2 : 4) : "—"}</td>
                      <td className={d1y >= 0 ? "up" : "down"}>{Number.isFinite(d1y) ? (d1y >= 0 ? "+" : "−") + money(Math.abs(d1y), isPct(x) ? 2 : 4) : "—"}</td>
                      <td className="small">{x.id.endsWith("_10Y_2Y") ? (last.value < 0 ? "courbe inversée" : "courbe normale") : x.id.endsWith("_REAL_POLICY") ? (last.value < 0 ? "taux réel négatif" : "taux réel positif") : ""}</td>
                    </tr>
                  ))}
                  {macroRows.length === 0 && <tr><td colSpan={6} className="muted">Aucune donnée. Importez macro-rates.csv.</td></tr>}
                </tbody>
              </table>
            </div>
            <p className="muted small" style={{ marginTop: 8 }}>Δ en points de pourcentage pour les taux, en unités pour les indices et le change. Cliquez une ligne pour la tracer. Les séries « dérivée » sont calculées ici à partir des séries sources (report de la dernière valeur mensuelle connue).</p>
          </section>
        )}

        {tab === "actions" && (
          <section style={{ padding: "8px 0 32px" }}>
            {actions.length === 0 ? <p className="muted">Aucune donnée. Importez corporate-actions.csv.</p> : (
              <>
                <section className="stats">
                  <div className="stat"><div className="stat-label">Dividendes versés (nombre)</div><div className="stat-value filled">{divs.length}</div><div className="stat-sub">{divs[0]?.unit ?? ""}</div></div>
                  <div className="stat"><div className="stat-label">Dernier dividende</div><div className="stat-value filled">{divs.length ? num(divs[divs.length - 1].value, 3) : "—"}</div><div className="stat-sub">{divs[divs.length - 1]?.date ?? ""}</div></div>
                  <div className="stat"><div className="stat-label">Croissance annuelle du dividende</div><div className="stat-value filled">{Number.isFinite(cagr) ? plainPct(cagr, 1) : "—"}</div><div className="stat-sub">années complètes seulement</div></div>
                  <div className="stat"><div className="stat-label">Fractionnements</div><div className="stat-value filled">{splits.length}</div></div>
                </section>
                {divs.length > 1 && (
                  <section className="chart" aria-label="Dividendes par versement">
                    <Chart key={ticker} values={divs.map((d) => d.value)} timestamps={divs.map((d) => toSeconds(d.date))} axisLabel={(t) => shortDate(t, true)} format={(v) => num(v, 3)} />
                  </section>
                )}
                <div className="grid2">
                  <section>
                    <h2 className="section-title">Total par année</h2>
                    <div className="table-wrap"><table className="tbl"><thead><tr><th>Année</th><th>Total</th></tr></thead><tbody>{byYear.map(([y, v]) => <tr key={y}><td>{y}</td><td>{num(v, 3)}</td></tr>)}</tbody></table></div>
                    <p className="muted small" style={{ marginTop: 8 }}>La première et la dernière année peuvent être partielles. Le rendement (dividende / prix) exige l'historique de prix, absent des fichiers fournis.</p>
                  </section>
                  <section>
                    <h2 className="section-title">Événements</h2>
                    <div className="table-wrap"><table className="tbl"><thead><tr><th>Date ex.</th><th>Type</th><th>Valeur</th></tr></thead><tbody>
                      {[...mine].reverse().map((a, i) => <tr key={i}><td>{a.date}</td><td>{a.action === "split" ? "fractionnement" : "dividende"}</td><td>{a.action === "split" ? `${num(a.value, 3)} pour 1` : `${num(a.value, 3)} ${a.unit.split(" ")[0]}`}</td></tr>)}
                    </tbody></table></div>
                  </section>
                </div>
              </>
            )}
          </section>
        )}
      </main>
      <footer className="footer"><div className="wrap footer-row"><span>Données publiques à titre informatif : aucun conseil financier. Sources : Banque du Canada, FRED. Le rendement passé ne prédit pas le futur.</span></div></footer>
    </>
  );
}
