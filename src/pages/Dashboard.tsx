import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import Chart from "../components/Chart";
import Chat from "../components/Chat";
import OrderModal, { type OrderPreset } from "../components/OrderModal";
import { cad, money, pct, shortDate, signedCad } from "../lib/format";
import { ASSETS, RANGE_KEYS, assetOf, fxOf, prevClose, type RangeKey } from "../lib/market";
import { ALL, computePortfolio, series } from "../lib/portfolio";
import { useApp } from "../lib/store";
import { ACCOUNTS } from "../lib/types";

const ACCOUNT_OPTIONS = [ALL, ...ACCOUNTS];
const PALETTE = ["var(--red)", "#f3a3a6", "#111318", "#6b7280", "#d6d9de", "#a1a6b0", "#c3141a"];
const colorFor = (name: string, i: number) => (name === "Liquidités" ? "#d6d9de" : PALETTE[i % PALETTE.length]);
const fmtDate = (ts: number) => new Date(ts).toLocaleDateString("fr-CA", { day: "numeric", month: "short", year: "numeric" });

function Alloc({ items }: { items: { name: string; value: number; pct: number }[] }) {
  return (
    <>
      <div className="alloc-bar">{items.filter((a) => a.pct > 0).map((a, i) => <span key={a.name} style={{ width: `${a.pct}%`, background: colorFor(a.name, i) }} title={`${a.name} ${money(a.pct, 1)} %`} />)}</div>
      <ul className="legend">
        {items.map((a, i) => (
          <li key={a.name}><span className="dot" style={{ background: colorFor(a.name, i) }} />{a.name}<span className="legend-value">{cad(a.value, 0)}</span><span className="pct filled">{money(a.pct, 1)} %</span></li>
        ))}
      </ul>
    </>
  );
}

export default function Dashboard() {
  const { data, prices, resetDemo, cancelOrder, addWatch, removeWatch } = useApp();
  const d = data!;
  const [account, setAccount] = useState(ALL);
  const [period, setPeriod] = useState<RangeKey>("AAJ");
  const [order, setOrder] = useState<OrderPreset | null>(null);
  const [chatMode, setChatMode] = useState<"closed" | "widget" | "full">("closed");
  const [activeConv, setActiveConv] = useState<string | null>(null);
  const [toAdd, setToAdd] = useState("");

  const p = useMemo(() => computePortfolio(d, prices, account), [d, prices, account]);
  const empty = p.rows.length === 0;
  const chart = useMemo(() => {
    const s = series(p.rows, p.cash, period);
    return s.values.length > 1 ? s : null;
  }, [p.rows, p.cash, period]);
  const periodReturn = chart && chart.values[0] > 0 ? (chart.values[chart.values.length - 1] / chart.values[0] - 1) * 100 : null;
  const pending = d.orders.filter((o) => o.status === "pending");
  const available = ASSETS.filter((a) => !d.watchlist.includes(a.symbol));

  const stats = [
    { label: `Rendement (${period})`, value: periodReturn != null ? pct(periodReturn) : "—", tone: periodReturn != null ? (periodReturn >= 0 ? "up" : "down") : "" },
    { label: "Capital investi", value: cad(p.costTotal, 0), tone: "", sub: "Coût des positions actuelles" },
    { label: "Gain non réalisé", value: signedCad(p.unrealized), tone: p.unrealized >= 0 ? "up" : "down", sub: p.costTotal > 0 ? pct((p.unrealized / p.costTotal) * 100) : "" },
    { label: "Liquidités", value: cad(p.cash), tone: "" },
  ];

  return (
    <>
      <AppHeader showRefresh>
        <button type="button" className="btn-ghost" onClick={() => setOrder({ side: "sell" })} disabled={d.holdings.length === 0}>Vendre</button>
        <button type="button" className="btn" onClick={() => setOrder({ side: "buy" })}><span aria-hidden="true">+</span> Acheter</button>
      </AppHeader>

      <main className="wrap">
        <section className="hero">
          <div>
            <div className="eyebrow">Valeur totale<span className="tag">Données simulées · prix fictifs</span></div>
            <div className="big filled">{money(p.total)}<small>$ CAD</small></div>
            <div className={`sub ${p.day >= 0 ? "up" : "down"}`}>{signedCad(p.day)} ({pct(p.dayPct)}) <span>aujourd&apos;hui</span></div>
          </div>
          <div className="controls">
            <select className="select" aria-label="Compte" value={account} onChange={(e) => setAccount(e.target.value)}>{ACCOUNT_OPTIONS.map((a) => <option key={a}>{a}</option>)}</select>
            <div className="segmented" role="group" aria-label="Période">
              {RANGE_KEYS.map((k) => <button key={k} type="button" className={k === period ? "on" : undefined} aria-pressed={k === period} onClick={() => setPeriod(k)}>{k}</button>)}
            </div>
          </div>
        </section>

        <div className="chart-head">
          <h2>Évolution du portefeuille</h2>
          {periodReturn != null && <span className={`chip-ret ${periodReturn >= 0 ? "up" : "down"}`}>{pct(periodReturn)} · {period}</span>}
        </div>
        <section className="chart" aria-label="Évolution de la valeur">
          {chart ? (
            <Chart key={period + account} values={chart.values} timestamps={chart.timestamps} axisLabel={(t) => shortDate(t, period === "1A" || period === "Max")} format={(v) => cad(v)} />
          ) : (
            <div className="chart-empty"><p>Achetez un premier titre simulé pour suivre l&apos;évolution de votre portefeuille.</p><button type="button" className="btn" onClick={() => setOrder({ side: "buy" })}>Acheter un titre</button></div>
          )}
        </section>

        <section className="stats">
          {stats.map((s) => (
            <div key={s.label} className="stat"><div className="stat-label">{s.label}</div><div className={`stat-value filled ${s.tone}`}>{s.value}</div>{s.sub && <div className="stat-sub">{s.sub}</div>}</div>
          ))}
        </section>

        <div className="grid2">
          <section>
            <h2 className="section-title">Répartition</h2>
            {empty && p.cash === 0 ? <div className="empty"><strong>Aucune donnée</strong></div> : <Alloc items={p.byCategory} />}
          </section>
          <section>
            <div className="section-row"><h2 className="section-title">Positions</h2>{!empty && <span className="muted small">{p.rows.length} titre{p.rows.length > 1 ? "s" : ""}</span>}</div>
            {!empty ? (
              <ul className="positions">
                {p.rows.map((r) => (
                  <li key={r.id}>
                    <button type="button" className="pos-main" title="Vendre cette position" onClick={() => setOrder({ side: "sell", holdingId: r.id })}>
                      <span className="symbol">{r.symbol.replace(/\.TO$/, "")}</span>
                      <span className="pos-name"><strong>{r.name}</strong><span>{money(r.quantity, 0)} × {money(r.price)} {r.currency !== "CAD" ? r.currency : ""} · {r.account} · PMP {money(r.avgCost)}</span></span>
                      <span className="pos-value"><strong>{cad(r.value)}</strong><span className={r.gainPct >= 0 ? "up" : "down"}>{pct(r.gainPct)} · {signedCad(r.value - r.cost)}</span></span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty"><div className="empty-icon"><svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M3 15 8 9l3 3 6-7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg></div><strong>Aucune position</strong><span>{account === ALL ? "Achetez un titre simulé pour commencer." : `Aucun titre dans le compte ${account}.`}</span></div>
            )}
          </section>
        </div>

        <div className="grid2" style={{ paddingTop: 0 }}>
          <section>
            <h2 className="section-title">Secteurs</h2>
            {empty ? <div className="empty"><strong>Aucune donnée</strong></div> : <Alloc items={p.bySector} />}
          </section>
          <section>
            <div className="section-row"><h2 className="section-title">Liste de surveillance</h2></div>
            <div className="watch-add">
              <select className="select" aria-label="Ajouter à la liste" value={toAdd} onChange={(e) => setToAdd(e.target.value)}>
                <option value="">Ajouter un titre…</option>
                {available.map((a) => <option key={a.symbol} value={a.symbol}>{a.symbol} — {a.name}</option>)}
              </select>
              <button type="button" className="btn-ghost" disabled={!toAdd} onClick={() => { addWatch(toAdd); setToAdd(""); }}>Ajouter</button>
            </div>
            {d.watchlist.length ? (
              <ul className="positions">
                {d.watchlist.map((s) => {
                  const a = assetOf(s)!, price = prices[s], ch = ((price - prevClose(s)) / prevClose(s)) * 100;
                  return (
                    <li key={s}>
                      <button type="button" className="pos-main" title="Acheter" onClick={() => setOrder({ side: "buy", symbol: s })}>
                        <span className="symbol">{s.replace(/\.TO$/, "")}</span>
                        <span className="pos-name"><strong>{a.name}</strong><span>{a.sector}</span></span>
                        <span className="pos-value"><strong>{money(price)} {a.currency !== "CAD" ? a.currency : ""}</strong><span className={ch >= 0 ? "up" : "down"}>{pct(ch)}</span></span>
                      </button>
                      <button type="button" className="remove" aria-label={`Retirer ${s}`} title="Retirer" onClick={() => removeWatch(s)}><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="m4 4 8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg></button>
                    </li>
                  );
                })}
              </ul>
            ) : <div className="empty"><strong>Liste vide</strong><span>Ajoutez des titres à surveiller.</span></div>}
          </section>
        </div>

        <div className="grid2" style={{ paddingTop: 0 }}>
          <section>
            <h2 className="section-title">Transactions récentes</h2>
            {d.transactions.length ? (
              <ul className="positions">
                {d.transactions.slice(0, 6).map((t) => (
                  <li key={t.id}><div className="pos-main" style={{ cursor: "default" }}>
                    <span className="symbol">{t.symbol.replace(/\.TO$/, "")}</span>
                    <span className="pos-name"><strong>{t.side === "buy" ? "Achat" : "Vente"} · {t.quantity} × {money(t.price)} {t.currency}</strong><span>{fmtDate(t.date)} · {t.account}</span></span>
                    <span className="pos-value"><strong>{cad(t.totalCad)}</strong></span>
                  </div></li>
                ))}
              </ul>
            ) : <div className="empty"><strong>Aucune transaction</strong><span>Vos ordres simulés apparaîtront ici.</span></div>}
          </section>
          <section>
            <h2 className="section-title">Ordres en attente</h2>
            {pending.length ? (
              <ul className="positions">
                {pending.map((o) => (
                  <li key={o.id}><div className="pos-main" style={{ cursor: "default" }}>
                    <span className="symbol">{o.symbol.replace(/\.TO$/, "")}</span>
                    <span className="pos-name"><strong>{o.side === "buy" ? "Achat" : "Vente"} · {o.quantity} à cours limité {money(o.limitPrice ?? 0)}</strong><span>Prix actuel : {money(prices[o.symbol])} · {fxOf(o.symbol) > 1 ? "USD" : "CAD"}</span></span>
                    <button type="button" className="link" onClick={() => cancelOrder(o.id)}>Annuler</button>
                  </div></li>
                ))}
              </ul>
            ) : <div className="empty"><strong>Aucun ordre en attente</strong><span>Les ordres à cours limité non exécutés s&apos;affichent ici.</span></div>}
            <div className="profile-mini">
              <div><div className="stat-label">Profil de risque</div><strong>{d.profile.label} · {d.profile.score}/100</strong></div>
              <Link to="/profil" className="link">Voir / modifier</Link>
            </div>
          </section>
        </div>
      </main>

      <footer className="footer">
        <div className="wrap footer-row">
          <span>Prix fictifs générés localement; aucune donnée de marché réelle et aucun ordre réel. Les rendements passés ne sont pas garants des rendements futurs; information fournie à titre indicatif seulement.</span>
          <button type="button" className="link small" onClick={resetDemo}>Réinitialiser la démo</button>
        </div>
      </footer>

      <Chat activeId={activeConv} setActiveId={setActiveConv} mode={chatMode} setMode={setChatMode} />
      {order && <OrderModal preset={order} onClose={() => setOrder(null)} />}
    </>
  );
}
