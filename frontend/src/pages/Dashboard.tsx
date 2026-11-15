/* Page /accueil (logo Grow) : vue générale du portefeuille du client.
 * Valeur totale, courbe de performance, camembert d'allocation et vue graphique des titres.
 * Aucun calcul financier ici : tout vient de GET /portfolios/{id}/summary (le front ne fait que présenter). */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { errorText } from "../api/errors";
import { getSummary, listPortfolios } from "../api/endpoints";
import type { Portfolio, PortfolioSummary, Slice, SummaryRange } from "../api/types";
import AppHeader from "../components/AppHeader";
import Chart from "../components/Chart";
import { TickerLabel } from "../components/TickerLogo";
import { amount, money, pct, plainPct, shortDate, signedAmount, toSeconds } from "../lib/format";
import { useApp } from "../lib/store";

const RANGES: { key: SummaryRange; label: string }[] = [
  { key: "1m", label: "1 M" }, { key: "6m", label: "6 M" }, { key: "1y", label: "1 A" }, { key: "5y", label: "5 A" },
];
const PALETTE = ["#143D30", "#1B5E45", "#3E8F68", "#C4A15A", "#D08A62", "#6E8FA8", "#8E9892", "#D5DDD8"];
const BREAKDOWNS = [
  { key: "byAssetClass", label: "Classes d'actifs" },
  { key: "bySector", label: "Secteurs" },
  { key: "byCurrency", label: "Devises" },
] as const;
type BreakdownKey = (typeof BREAKDOWNS)[number]["key"];

/** Camembert (donut) en SVG : un arc par tranche, centre interactif. */
function Donut({ slices, centerTitle, centerValue }: { slices: Slice[]; centerTitle: string; centerValue: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const R = 70, C = 2 * Math.PI * R, GAP = 2;
  const data = slices.filter((s) => s.weight > 0);
  const total = data.reduce((s, x) => s + x.weight, 0) || 1;
  let acc = 0;
  const active = hover !== null ? data[hover] : null;
  return (
    <div className="donut">
      <svg viewBox="0 0 200 200" role="img" aria-label="Répartition du portefeuille">
        <circle cx="100" cy="100" r={R} fill="none" stroke="#EEF2EF" strokeWidth="26" />
        {data.map((s, i) => {
          const len = (s.weight / total) * C;
          const el = (
            <circle
              key={s.label}
              cx="100" cy="100" r={R} fill="none"
              stroke={PALETTE[i % PALETTE.length]}
              strokeWidth={hover === i ? 32 : 26}
              strokeDasharray={`${Math.max(len - GAP, 0.5)} ${C}`}
              strokeDashoffset={-acc}
              transform="rotate(-90 100 100)"
              className="donut-arc"
              opacity={hover === null || hover === i ? 1 : 0.35}
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
            >
              <title>{`${s.label} ${plainPct(s.weight)}`}</title>
            </circle>
          );
          acc += len;
          return el;
        })}
      </svg>
      <div className="donut-center">
        <span className="donut-label">{active ? active.label : centerTitle}</span>
        <strong className="donut-value">{active ? plainPct(active.weight) : centerValue}</strong>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user, status } = useApp();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [range, setRange] = useState<SummaryRange>("1y");
  const [by, setBy] = useState<BreakdownKey>("byAssetClass");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user?.investorProfile) return;
    setLoading(true);
    listPortfolios()
      .then(({ items }) => setPortfolio(items.find((p) => p.portfolioId === "main") ?? items[0] ?? null))
      .catch((e) => setError(errorText(e)))
      .finally(() => setLoading(false));
  }, [user?.investorProfile]);

  useEffect(() => {
    if (!portfolio || portfolio.holdings.length === 0) { setSummary(null); return; }
    let live = true;
    getSummary(portfolio.portfolioId, range)
      .then((s) => { if (live) { setSummary(s); setError(""); } })
      .catch((e) => { if (live) setError(errorText(e)); });
    return () => { live = false; };
  }, [portfolio, range]);

  const chart = useMemo(() => {
    const pts = summary?.performance.points ?? [];
    return pts.length > 1 ? { values: pts.map((p) => p.value), timestamps: pts.map((p) => toSeconds(p.date)) } : null;
  }, [summary]);

  const holdings = useMemo(() => [...(summary?.holdings ?? [])].sort((a, b) => b.value - a.value), [summary]);

  if (status === "loading") return <><AppHeader /><main className="wrap"><p className="muted" style={{ padding: "48px 0" }}>Chargement…</p></main></>;
  const anon = status === "anon" || !user;
  const needsProfile = !anon && !user?.investorProfile;

  const cur = summary?.baseCurrency ?? portfolio?.baseCurrency ?? "CAD";
  const t = summary?.totals;
  const name = user ? (user.displayName ?? user.username) : "";
  const best = holdings.length ? holdings.reduce((a, b) => (b.dayChangePct > a.dayChangePct ? b : a)) : null;
  const worst = holdings.length ? holdings.reduce((a, b) => (b.dayChangePct < a.dayChangePct ? b : a)) : null;

  return (
    <>
      <AppHeader />
      <main className="wrap dash2">
        <section className="dash2-hero">
          <div>
            <p className="dash2-hello">{anon ? "Mode exploration" : `Bonjour ${name}`}</p>
            <h1 className="dash2-title">Vue générale de votre portefeuille</h1>
          </div>
          <div className="dash2-actions">
            <Link to="/chat" className="btn">Nouvelle session</Link>
            <Link to="/portefeuille" className="btn-ghost">Gérer mes positions</Link>
          </div>
        </section>

        {anon && (
          <section className="dash2-card dash2-empty dash2-empty-tree">
            <h2>Aucune donnée à afficher</h2>
            <p className="muted">Explorez Grow sans compte, ou connectez-vous pour voir la vue d'ensemble de votre portefeuille.</p>
            <Link to="/inscription" className="btn dash2-create">Créez votre portefeuille !</Link>
          </section>
        )}
        {needsProfile && (
          <section className="dash2-card dash2-empty">
            <h2>Créez votre portefeuille</h2>
            <p className="muted">Répondez au questionnaire investisseur pour afficher ici votre vue d'ensemble.</p>
            <Link to="/portefeuille" className="btn">Commencer</Link>
          </section>
        )}
        {loading && <p className="muted">Chargement…</p>}
        {error && <p className="error" role="alert">{error}</p>}

        {!loading && portfolio && portfolio.holdings.length === 0 && (
          <section className="dash2-card dash2-empty">
            <h2>Votre portefeuille est vide</h2>
            <p className="muted">Ajoutez vos premiers titres ou demandez à l'assistant de vous proposer un mandat.</p>
            <div className="dash2-actions">
              <Link to="/portefeuille" className="btn">Ajouter des positions</Link>
              <Link to="/chat" className="btn-ghost">Démarrer une session</Link>
            </div>
          </section>
        )}

        {summary && t && (
          <>
            <section className="dash2-kpis" aria-label="Indicateurs clés">
              <div className="dash2-card dash2-kpi main">
                <span className="dash2-kpi-label">Valeur totale</span>
                <strong className="dash2-kpi-value">{money(t.value)} <small>{cur}</small></strong>
                <span className={`dash2-chip ${t.dayChange >= 0 ? "up" : "down"}`}>
                  {t.dayChange >= 0 ? "▲" : "▼"} {signedAmount(t.dayChange, cur)} ({pct(t.dayChangePct)}) <em>aujourd'hui</em>
                </span>
              </div>
              <div className="dash2-card dash2-kpi">
                <span className="dash2-kpi-label">Gain / perte total</span>
                <strong className={`dash2-kpi-value sm ${t.pnl >= 0 ? "up" : "down"}`}>{signedAmount(t.pnl, cur)}</strong>
                <span className="dash2-kpi-sub">{pct(t.pnlPct)} depuis l'achat</span>
              </div>
              <div className="dash2-card dash2-kpi">
                <span className="dash2-kpi-label">Volatilité annualisée</span>
                <strong className="dash2-kpi-value sm">{plainPct(summary.risk.volatility, 2)}</strong>
                <span className="dash2-kpi-sub">Baisse maximale {plainPct(summary.risk.maxDrawdown, 2)}</span>
              </div>
              <div className="dash2-card dash2-kpi">
                <span className="dash2-kpi-label">Titres détenus</span>
                <strong className="dash2-kpi-value sm">{holdings.length}</strong>
                <span className="dash2-kpi-sub">Capital investi {amount(t.cost, cur, 0)}</span>
              </div>
            </section>

            <section className="dash2-row">
              <div className="dash2-card dash2-perf">
                <div className="dash2-card-head">
                  <h2>Performance</h2>
                  <div className="segmented" role="group" aria-label="Période">
                    {RANGES.map((r) => (
                      <button key={r.key} type="button" className={r.key === range ? "on" : undefined} aria-pressed={r.key === range} onClick={() => setRange(r.key)}>{r.label}</button>
                    ))}
                  </div>
                </div>
                {chart
                  ? <div className="chart"><Chart key={range} values={chart.values} timestamps={chart.timestamps} axisLabel={(ts) => shortDate(ts, range === "1y" || range === "5y")} format={(v) => amount(v, cur)} /></div>
                  : <p className="muted">Pas assez de points pour tracer la performance.</p>}
              </div>

              <div className="dash2-card dash2-alloc">
                <div className="dash2-card-head"><h2>Répartition</h2></div>
                <div className="dash2-tabs" role="tablist" aria-label="Type de répartition">
                  {BREAKDOWNS.map((b) => (
                    <button key={b.key} type="button" role="tab" aria-selected={by === b.key} className={by === b.key ? "on" : undefined} onClick={() => setBy(b.key)}>{b.label}</button>
                  ))}
                </div>
                <Donut key={by} slices={summary.allocation[by]} centerTitle="Total" centerValue={`${money(t.value, 0)} ${cur}`} />
                <ul className="dash2-legend">
                  {summary.allocation[by].map((s, i) => (
                    <li key={s.label}>
                      <span className="dot" style={{ background: PALETTE[i % PALETTE.length] }} />
                      <span className="dash2-legend-name">{s.label}</span>
                      <strong>{plainPct(s.weight)}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            <section aria-labelledby="titres-h">
              <div className="dash2-section-head">
                <h2 id="titres-h">Mes titres</h2>
                {best && worst && holdings.length > 1 && (
                  <span className="muted small">
                    Meilleur du jour : <strong className="up">{best.ticker} {pct(best.dayChangePct)}</strong> · Plus faible : <strong className="down">{worst.ticker} {pct(worst.dayChangePct)}</strong>
                  </span>
                )}
              </div>

              <div className="dash2-stack" role="img" aria-label="Poids de chaque titre dans le portefeuille">
                {holdings.map((h, i) => (
                  <span key={h.ticker} style={{ width: `${h.weight}%`, background: PALETTE[i % PALETTE.length] }} title={`${h.ticker} ${plainPct(h.weight)}`} />
                ))}
              </div>

              <div className="dash2-holdings">
                {holdings.map((h, i) => (
                  <article key={h.ticker} className="dash2-card dash2-holding">
                    <header>
                      <TickerLabel ticker={h.ticker} name={h.name} size={36} />
                      <span className={`dash2-chip ${h.dayChangePct >= 0 ? "up" : "down"}`}>{pct(h.dayChangePct)}</span>
                    </header>
                    <div className="dash2-holding-value">{money(h.value)} <small>{cur}</small></div>
                    <div className="dash2-bar"><span style={{ width: `${Math.min(h.weight, 100)}%`, background: PALETTE[i % PALETTE.length] }} /></div>
                    <footer>
                      <span>{plainPct(h.weight)} du portefeuille</span>
                      <span className={h.pnl >= 0 ? "up" : "down"}>{signedAmount(h.pnl, cur)}</span>
                    </footer>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </main>
      <footer className="footer"><div className="wrap footer-row"><span>Simulation seulement : aucune transaction n'est exécutée et rien ici ne constitue un conseil financier personnalisé. Tous les chiffres sont calculés par le serveur.</span></div></footer>
    </>
  );
}
