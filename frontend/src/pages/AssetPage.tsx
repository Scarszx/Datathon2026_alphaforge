/* Fiche d'un actif (style épuré) : prix, courbe, repères et description.
 * Tout vient de GET /market/assets/{ticker} : le front ne calcule que la position dans la fourchette 52 semaines. */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import PriceChart from "../components/PriceChart";
import TickerLogo from "../components/TickerLogo";
import { getAssetDetail } from "../api/endpoints";
import { errorText } from "../api/errors";
import type { AssetDetail, SummaryRange } from "../api/types";
import { money, pct } from "../lib/format";
import "../markets.css";

const RANGES: { value: SummaryRange; label: string }[] = [
  { value: "1m", label: "1 M" }, { value: "6m", label: "6 M" }, { value: "1y", label: "1 A" }, { value: "5y", label: "5 A" },
];
const RANGE_TEXT: Record<SummaryRange, string> = { "1m": "sur 1 mois", "6m": "sur 6 mois", "1y": "sur 1 an", "5y": "sur 5 ans" };
const CLASS_LABELS: Record<string, string> = {
  equity: "Action", etf: "FNB", etf_equity: "FNB d'actions", etf_bond: "FNB d'obligations",
  etf_commodity: "FNB de matières premières", etf_reit: "FNB immobilier", crypto: "Crypto",
};
const SYMBOL: Record<string, string> = { CAD: "$", USD: "US$" };

export default function AssetPage() {
  const { ticker = "" } = useParams();
  const [range, setRange] = useState<SummaryRange>("1y");
  const [data, setData] = useState<AssetDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => { setData(null); }, [ticker]);
  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true); setError("");
    getAssetDetail(ticker, range, ctrl.signal)
      .then((d) => { if (!ctrl.signal.aborted) setData(d); })
      .catch((x) => { if (!ctrl.signal.aborted) setError(errorText(x)); })
      .finally(() => { if (!ctrl.signal.aborted) setLoading(false); });
    return () => ctrl.abort();
  }, [ticker, range]);

  const cur = data?.currency ?? "";
  const price = (v: number | null | undefined) =>
    v == null ? "—" : `${money(v, Math.abs(v) < 1 ? 4 : 2)} ${SYMBOL[cur] ?? cur}`.trim();
  const rangePct = data?.rangeChangePct ?? null;
  const up = (rangePct ?? 0) >= 0;
  const hi = data?.stats.high52w ?? null, lo = data?.stats.low52w ?? null;
  const pos = data && hi != null && lo != null && hi > lo ? Math.min(100, Math.max(0, ((data.price - lo) / (hi - lo)) * 100)) : null;
  const classLabel = data ? CLASS_LABELS[data.assetClass] ?? data.assetClass : "";

  const facts: [string, string][] = data ? [
    ["Marché", data.market ?? "—"], ["Devise", data.currency ?? "—"],
    ["Secteur", data.sector ?? "—"], ["Industrie", data.industry ?? "—"], ["Pays", data.country ?? "—"],
    ["Historique depuis", data.stats.historyStart.slice(0, 4)],
  ] : [];
  const about = data?.description
    ?? (data ? `${data.name} (${data.ticker}) est ${data.assetClass.startsWith("etf") ? "un FNB" : data.assetClass === "crypto" ? "un cryptoactif" : "une action"}${data.market ? ` cotée au ${data.market}` : ""}${data.sector ? `, secteur ${data.sector.toLowerCase()}` : ""}. Aucune description détaillée n'est disponible dans le jeu de données.` : "");

  return (
    <>
      <AppHeader />
      <main className="wrap mk ap">
        <Link to="/marches" className="ap-back">← Marchés</Link>

        {error && !data && (
          <section className="mk-empty">
            <h2>Fiche indisponible</h2>
            <p>{error}</p>
            <Link className="btn" to="/marches">Retour aux marchés</Link>
          </section>
        )}

        {!error && !data && <div className="ap-skel" aria-busy="true"><span className="sk-l" /><span className="sk-l" /><span className="sk-l big" /></div>}

        {data && (
          <div className="ap-grid">
            <section className="ap-main">
              <header className="ap-head">
                <TickerLogo ticker={data.ticker} size={56} />
                <div>
                  <h1>{data.name}</h1>
                  <p><span className="mono">{data.ticker}</span><span className="ap-dot" />{classLabel}{data.market ? <><span className="ap-dot" />{data.market}</> : null}</p>
                </div>
              </header>

              <div className="ap-price">
                <strong>{price(data.price)}</strong>
                {rangePct !== null && (
                  <span className={`ap-chg ${up ? "up" : "down"}`}>
                    <svg viewBox="0 0 12 12" width="11" height="11" aria-hidden="true"><path d={up ? "M6 2 11 10H1z" : "M6 10 1 2h10z"} fill="currentColor" /></svg>
                    {pct(rangePct)} <em>{RANGE_TEXT[range]}</em>
                  </span>
                )}
              </div>
              <p className="ap-asof">Dernière clôture du {data.asOf}{data.dayChangePct != null && <> · jour {pct(data.dayChangePct)}</>}</p>

              <div className={`ap-chart${loading ? " stale" : ""}`}>
                <PriceChart points={data.points} up={up} format={price} />
              </div>
              <div className="ap-ranges" role="group" aria-label="Période">
                {RANGES.map((r) => (
                  <button key={r.value} type="button" className={range === r.value ? "on" : ""} aria-pressed={range === r.value} onClick={() => setRange(r.value)}>{r.label}</button>
                ))}
              </div>
              {error && <p className="mk-note" role="status">{error}</p>}
            </section>

            <aside className="ap-side">
              <div className="ap-card">
                <h2>À propos</h2>
                <p className="ap-about">{about}</p>
                {data.website && <a className="ap-link" href={data.website} target="_blank" rel="noreferrer noopener">Site officiel ↗</a>}
              </div>

              <div className="ap-card">
                <h2>Repères</h2>
                {pos !== null && (
                  <div className="ap-range52">
                    <div className="ap-range52-lbl"><span>Bas 52 sem.</span><span>Haut 52 sem.</span></div>
                    <div className="ap-range52-bar"><i style={{ left: `${pos}%` }} /></div>
                    <div className="ap-range52-val"><strong>{price(lo)}</strong><strong>{price(hi)}</strong></div>
                  </div>
                )}
                <dl className="ap-stats">
                  <div><dt>Volatilité (1 an)</dt><dd>{data.stats.volatility != null ? `${money(data.stats.volatility, 1)} %` : "—"}</dd></div>
                  <div><dt>Baisse maximale (1 an)</dt><dd>{data.stats.maxDrawdown != null ? `${money(data.stats.maxDrawdown, 1)} %` : "—"}</dd></div>
                  {facts.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
                </dl>
              </div>

              <div className="mk-cta">
                <Link className="btn" to="/portefeuille">Ajouter au portefeuille</Link>
                <Link className="btn-ghost" to="/chat">Analyser en session</Link>
              </div>
            </aside>
          </div>
        )}
      </main>
      <footer className="footer"><div className="wrap footer-row"><span>Simulation pédagogique, pas un conseil financier. Les performances passées ne prédisent pas les résultats futurs.{data?.source ? ` Source : ${data.source}.` : ""}</span></div></footer>
    </>
  );
}
