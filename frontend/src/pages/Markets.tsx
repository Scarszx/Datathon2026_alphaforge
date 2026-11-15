/* Marchés : explorateur de l'univers d'actifs, via l'API (api-market-search).
 * Le front ne calcule rien : prix, indicateurs et séries historiques viennent du back
 * (portefeuille : GET /portfolios/{id}/summary ; univers : GET /market/search). */
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { searchAssets } from "../api/endpoints";
import { errorText } from "../api/errors";
import type { Asset } from "../api/types";
import TickerLogo from "../components/TickerLogo";
import "../markets.css";

const CLASS_LABELS: Record<string, string> = {
  equity: "Action", etf: "FNB", etf_equity: "FNB d'actions", etf_bond: "FNB d'obligations",
  etf_commodity: "FNB de matières premières", etf_reit: "FNB immobilier", crypto: "Crypto",
};
const CLASS_TONE: Record<string, string> = { equity: "eq", etf: "etf", crypto: "cr" };
const FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Tout" },
  { value: "equity", label: "Actions" },
  { value: "etf", label: "FNB" },
  { value: "crypto", label: "Crypto" },
];
const SUGGESTIONS = ["RY.TO", "NVDA", "XEQT", "BTC-USD"];

const labelOf = (a: Pick<Asset, "assetClass">) => CLASS_LABELS[a.assetClass] ?? a.assetClass;
const toneOf = (a: Pick<Asset, "assetClass">) => CLASS_TONE[a.assetClass.split("_")[0]] ?? "eq";

export default function Markets() {
  const [q, setQ] = useState("");
  const [assetClass, setAssetClass] = useState("");
  const [items, setItems] = useState<Asset[]>([]);
  const [selected, setSelected] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  /* Recherche avec délai : l'appel part après 300 ms d'inactivité et une requête périmée est annulée. */
  useEffect(() => {
    const query = q.trim();
    if (!query && !assetClass) { setItems([]); setError(""); setLoading(false); return; }
    const ctrl = new AbortController();
    setLoading(true);
    const t = setTimeout(async () => {
      setError("");
      try {
        const res = await searchAssets(query, assetClass || undefined, ctrl.signal);
        if (ctrl.signal.aborted) return;
        setItems(res.items);
        setSelected((cur) => (cur && res.items.some((a) => a.ticker === cur.ticker) ? cur : res.items[0] ?? null));
      } catch (x) {
        if (!ctrl.signal.aborted) { setItems([]); setError(errorText(x)); }
      } finally {
        if (!ctrl.signal.aborted) setLoading(false);
      }
    }, 300);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [q, assetClass]);

  /* Raccourci « / » pour placer le curseur dans la recherche. */
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (e.key === "/" && tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const onListKey = (e: KeyboardEvent<HTMLUListElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const i = items.findIndex((a) => a.ticker === selected?.ticker);
    const next = items[Math.min(items.length - 1, Math.max(0, i + (e.key === "ArrowDown" ? 1 : -1)))];
    if (next) {
      setSelected(next);
      (e.currentTarget.querySelector(`[data-ticker="${CSS.escape(next.ticker)}"]`) as HTMLElement | null)?.focus();
    }
  };

  const query = q.trim();
  const idle = !query && !assetClass;
  const empty = !idle && !loading && !error && items.length === 0;

  return (
    <>
      <AppHeader />
      <main className="wrap mk">
        <section className="mk-top">
          <div className="mk-title">
            <h1>Marchés</h1>
            <p>Actions, FNB et cryptomonnaies couverts par la simulation.</p>
          </div>

          <div className="mk-search">
            <svg className="mk-search-ico" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
            </svg>
            <input
              ref={inputRef}
              type="search"
              className="mk-input"
              placeholder="Rechercher un ticker ou un nom (ex. RY.TO, NVDA, XEQT)"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              aria-label="Recherche d'actif"
              autoComplete="off"
              spellCheck={false}
            />
            {q ? (
              <button type="button" className="mk-clear" onClick={() => { setQ(""); inputRef.current?.focus(); }} aria-label="Effacer la recherche">×</button>
            ) : (
              <kbd className="mk-kbd" aria-hidden="true">/</kbd>
            )}
          </div>

          <div className="mk-filters" role="group" aria-label="Catégorie">
            {FILTERS.map((f) => (
              <button
                key={f.value || "all"} type="button"
                className={`mk-chip${assetClass === f.value ? " on" : ""}`}
                aria-pressed={assetClass === f.value}
                onClick={() => setAssetClass(f.value)}
              >{f.label}</button>
            ))}
          </div>
        </section>

        {error && <div className="banner warn" role="status"><p>{error}</p></div>}

        {idle && (
          <section className="mk-empty">
            <div className="mk-empty-ico" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 17l6-6 4 4 8-8" /><path d="M15 7h6v6" /></svg>
            </div>
            <h2>Explorez l'univers d'actifs</h2>
            <p>Tapez quelques lettres d'un ticker ou d'un nom, ou choisissez une catégorie.</p>
            <div className="mk-suggest">
              <span>Essayez</span>
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" className="mk-chip ghost" onClick={() => { setQ(s); inputRef.current?.focus(); }}>
                  <TickerLogo ticker={s} size={18} />{s}
                </button>
              ))}
            </div>
          </section>
        )}

        {empty && (
          <section className="mk-empty">
            <h2>Aucun résultat</h2>
            <p>Aucun actif ne correspond à « {query || labelOf({ assetClass })} ». Vérifiez l'orthographe ou essayez un autre ticker.</p>
          </section>
        )}

        {!idle && (loading || items.length > 0) && (
          <section className="mk-grid">
            <div className="mk-listcard">
              <div className="mk-listhead">
                <span>{loading ? "Recherche…" : `${items.length} résultat${items.length > 1 ? "s" : ""}`}</span>
                <span className="mk-hide-sm">Marché · Devise</span>
              </div>
              {loading && items.length === 0 ? (
                <ul className="mk-list" aria-busy="true">
                  {[0, 1, 2, 3, 4].map((i) => <li key={i} className="mk-row skel"><span className="sk-c" /><span className="sk-l" /></li>)}
                </ul>
              ) : (
                <ul className={`mk-list${loading ? " stale" : ""}`} onKeyDown={onListKey} aria-label="Résultats de recherche">
                  {items.map((a) => (
                    <li key={a.ticker}>
                      <button
                        type="button" data-ticker={a.ticker}
                        className={`mk-row${selected?.ticker === a.ticker ? " on" : ""}`}
                        aria-pressed={selected?.ticker === a.ticker}
                        onClick={() => setSelected(a)}
                      >
                        <TickerLogo ticker={a.ticker} size={36} />
                        <span className="mk-id">
                          <strong>{a.ticker}</strong>
                          <span>{a.name}</span>
                        </span>
                        <span className={`mk-badge ${toneOf(a)}`}>{labelOf(a)}</span>
                        <span className="mk-meta mk-hide-sm">{[a.market, a.currency].filter(Boolean).join(" · ") || "—"}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <aside className="mk-detail" aria-live="polite">
              {selected ? (
                <>
                  <div className="mk-detail-head">
                    <TickerLogo ticker={selected.ticker} size={52} />
                    <div>
                      <h2>{selected.ticker}</h2>
                      <p>{selected.name}</p>
                    </div>
                  </div>
                  <span className={`mk-badge ${toneOf(selected)}`}>{labelOf(selected)}</span>
                  <dl className="mk-facts">
                    <div><dt>Marché</dt><dd>{selected.market ?? "—"}</dd></div>
                    <div><dt>Devise</dt><dd>{selected.currency ?? "—"}</dd></div>
                    <div className="wide"><dt>Secteur</dt><dd>{selected.sector ?? "—"}</dd></div>
                  </dl>
                  <p className="mk-note">
                    Prix, valeur, poids et mesures de risque sont calculés par le back. Ajoutez ce titre à votre portefeuille,
                    puis lancez une analyse depuis la session pour le voir étudié scénario par scénario.
                  </p>
                  <div className="mk-cta">
                    <Link className="btn" to={`/marches/${encodeURIComponent(selected.ticker)}`}>Voir la fiche</Link>
                    <Link className="btn-ghost" to="/portefeuille">Ajouter au portefeuille</Link>
                    <Link className="btn-ghost" to="/chat">Analyser en session</Link>
                  </div>
                </>
              ) : (
                <p className="mk-note">Sélectionnez un actif pour voir sa fiche.</p>
              )}
            </aside>
          </section>
        )}
      </main>
      <footer className="footer"><div className="wrap footer-row"><span>Simulation pédagogique, pas un conseil financier. Les chiffres affichés ailleurs dans l'outil viennent de l'API et sont sourcés dans le registre de preuves.</span></div></footer>
    </>
  );
}
