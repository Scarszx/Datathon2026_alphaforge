/* Marchés : explorateur de l'univers d'actifs, via l'API (api-market-search).
 * Le front ne calcule rien : prix, indicateurs et séries historiques viennent du back
 * (portefeuille : GET /portfolios/{id}/summary ; univers : GET /market/search). */
import { useEffect, useMemo, useRef, useState } from "react";
import AppHeader from "../components/AppHeader";
import { searchAssets } from "../api/endpoints";
import { errorText } from "../api/errors";
import type { Asset } from "../api/types";
import TickerLogo, { TickerLabel } from "../components/TickerLogo";

const CLASS_LABELS: Record<string, string> = {
  equity: "Action", etf: "FNB", etf_equity: "FNB d'actions", etf_bond: "FNB d'obligations",
  etf_commodity: "FNB de matières premières", etf_reit: "FNB immobilier", crypto: "Crypto",
};

export default function Markets() {
  const [q, setQ] = useState("");
  const [assetClass, setAssetClass] = useState("");
  const [items, setItems] = useState<Asset[]>([]);
  const [selected, setSelected] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Recherche avec délai : chaque frappe ne déclenche l'appel qu'après 300 ms d'inactivité. */
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const query = q.trim();
    if (!query && !assetClass) { setItems([]); setError(""); return; }
    timer.current = setTimeout(async () => {
      setLoading(true); setError("");
      try {
        const { items } = await searchAssets(query, assetClass || undefined);
        setItems(items);
      } catch (x) { setError(errorText(x)); } finally { setLoading(false); }
    }, 300);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [q, assetClass]);

  const classes = useMemo(() => ["equity", "etf", "crypto"], []);
  const labelOf = (a: Asset) => CLASS_LABELS[a.assetClass] ?? a.assetClass;

  return (
    <>
      <AppHeader />
      <main className="wrap">
        <section className="hero">
          <div>
            <div className="eyebrow">Marchés<span className="tag">Univers de l'outil</span></div>
            <div className="big filled" style={{ fontSize: 28 }}>Recherche d'actifs</div>
            <div className="sub">L'univers couvert par la simulation : actions, FNB et cryptomonnaies du jeu de données.</div>
          </div>
        </section>

        <section style={{ padding: "8px 0 16px" }}>
          <div className="actions-row">
            <input
              className="input" style={{ flex: 1, minWidth: 220 }}
              placeholder="Rechercher un ticker ou un nom (ex. RY.TO, NVDA, XEQT)…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              aria-label="Recherche d'actif"
            />
            <label className="muted small">Catégorie{" "}
              <select value={assetClass} onChange={(e) => setAssetClass(e.target.value)}>
                <option value="">Toutes</option>
                {classes.map((c) => <option key={c} value={c}>{labelOf({ ticker: c, name: "", assetClass: c })}</option>)}
              </select>
            </label>
          </div>
        </section>

        {loading && <p className="muted small">Chargement…</p>}
        {error && <div className="banner warn" role="status"><p>{error}</p></div>}
        {!loading && !error && q.trim() && !items.length && <p className="muted">Aucun actif ne correspond à cette recherche.</p>}
        {!loading && !q.trim() && !assetClass && (
          <p className="muted">Tapez au moins quelques lettres pour interroger l'univers d'actifs.</p>
        )}

        {items.length > 0 && (
          <section style={{ padding: "8px 0 32px" }}>
            <div className="table-wrap">
              <table className="tbl">
                <thead><tr><th>Ticker</th><th>Nom</th><th>Catégorie</th><th>Marché</th><th>Devise</th><th>Secteur</th></tr></thead>
                <tbody>
                  {items.map((a) => (
                    <tr key={a.ticker} style={{ cursor: "pointer" }} onClick={() => setSelected(a)}>
                      <td><TickerLabel ticker={a.ticker} /></td>
                      <td>{a.name}</td>
                      <td>{labelOf(a)}</td>
                      <td>{a.market ?? "—"}</td>
                      <td>{a.currency ?? "—"}</td>
                      <td>{a.sector ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {selected && (
          <section className="profile-card" style={{ padding: "16px 0 32px", marginBottom: 32 }}>
            <div className="eyebrow">Actif sélectionné</div>
            <div className="big filled" style={{ fontSize: 26, display: "flex", alignItems: "center", gap: 12 }}><TickerLogo ticker={selected.ticker} size={40} />{selected.ticker}</div>
            <div className="sub">{selected.name}</div>
            <table className="tbl" style={{ marginTop: 12 }}>
              <tbody>
                <tr><td>Catégorie</td><td>{labelOf(selected)}</td></tr>
                <tr><td>Marché</td><td>{selected.market ?? "—"}</td></tr>
                <tr><td>Devise de cotation</td><td>{selected.currency ?? "—"}</td></tr>
                <tr><td>Secteur</td><td>{selected.sector ?? "—"}</td></tr>
              </tbody>
            </table>
            <p className="muted small" style={{ marginTop: 12 }}>
              Prix, valeur, poids et mesures de risque sont calculés par le back. Ajoutez ce titre dans votre portefeuille
              (page Portefeuille), puis lancez une analyse depuis la session pour le voir étudié scénario par scénario.
            </p>
          </section>
        )}
      </main>
      <footer className="footer"><div className="wrap footer-row"><span>Simulation pédagogique, pas un conseil financier. Les chiffres affichés ailleurs dans l'outil viennent de l'API et sont sourcés dans le registre de preuves.</span></div></footer>
    </>
  );
}
