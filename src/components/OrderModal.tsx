import { useEffect, useMemo, useState } from "react";
import { cad, money } from "../lib/format";
import { ASSETS } from "../lib/market";
import { preview } from "../lib/trading";
import { useApp } from "../lib/legacyStore";
import { ACCOUNTS, type Account, type OrderInput } from "../lib/types";

export type OrderPreset = { side: "buy" | "sell"; symbol?: string; holdingId?: string };

export default function OrderModal({ preset, onClose }: { preset: OrderPreset; onClose: () => void }) {
  const { data, prices, placeOrder } = useApp();
  const d = data!;
  const [side, setSide] = useState<"buy" | "sell">(preset.side);
  const [symbol, setSymbol] = useState(preset.symbol ?? ASSETS[0].symbol);
  const [holdingId, setHoldingId] = useState(preset.holdingId ?? d.holdings[0]?.id ?? "");
  const [account, setAccount] = useState<Account>("CELI");
  const [type, setType] = useState<"market" | "limit">("market");
  const [qty, setQty] = useState("");
  const [limit, setLimit] = useState("");
  const [step, setStep] = useState<"form" | "review" | "done">("form");
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const holding = d.holdings.find((h) => h.id === holdingId);
  const sym = side === "sell" ? holding?.symbol ?? "" : symbol;
  const asset = ASSETS.find((a) => a.symbol === sym);
  const input: OrderInput = {
    side, symbol: sym, holdingId: side === "sell" ? holdingId : undefined, account,
    type, quantity: Number(qty.replace(",", ".")) || 0, limitPrice: type === "limit" ? parseFloat(limit.replace(",", ".")) || undefined : undefined,
  };
  const p = useMemo(() => preview(d, prices, input), [d, prices, side, sym, holdingId, account, type, qty, limit]); // eslint-disable-line react-hooks/exhaustive-deps
  const market = prices[sym];

  function confirm() {
    setResult(placeOrder(input));
    setStep("done");
  }

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-label="Ordre simulé">
        <div className="modal-head">
          <h2>{step === "done" ? "Résultat" : step === "review" ? "Réviser l'ordre" : "Ordre simulé"}</h2>
          <button type="button" className="icon" onClick={onClose} aria-label="Fermer"><svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="m4 4 8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg></button>
        </div>
        <p className="notice">Simulation seulement : aucun ordre réel n'est transmis.</p>

        {step === "form" && (
          <>
            <div className="segmented full" role="group" aria-label="Sens">
              <button type="button" className={side === "buy" ? "on" : undefined} onClick={() => setSide("buy")}>Acheter</button>
              <button type="button" className={side === "sell" ? "on" : undefined} onClick={() => setSide("sell")} disabled={d.holdings.length === 0}>Vendre</button>
            </div>

            {side === "buy" ? (
              <div className="field">
                <label htmlFor="sym">Titre</label>
                <select id="sym" className="input" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
                  {ASSETS.map((a) => <option key={a.symbol} value={a.symbol}>{a.symbol} — {a.name}</option>)}
                </select>
              </div>
            ) : (
              <div className="field">
                <label htmlFor="hold">Position à vendre</label>
                <select id="hold" className="input" value={holdingId} onChange={(e) => setHoldingId(e.target.value)}>
                  {d.holdings.map((h) => <option key={h.id} value={h.id}>{h.symbol} · {h.account} · {h.quantity} détenu{h.quantity > 1 ? "s" : ""}</option>)}
                </select>
              </div>
            )}

            <div className="picked">
              <span className="symbol">{sym.replace(/\.TO$/, "")}</span>
              <div className="pos-name"><strong>{asset?.name ?? "—"}</strong><span>Prix simulé : {market ? `${money(market)} ${asset?.currency}` : "—"}</span></div>
            </div>

            <div className="segmented full" role="group" aria-label="Type d'ordre">
              <button type="button" className={type === "market" ? "on" : undefined} onClick={() => setType("market")}>Au marché</button>
              <button type="button" className={type === "limit" ? "on" : undefined} onClick={() => setType("limit")}>À cours limité</button>
            </div>

            <div className="row2">
              <div className="field"><label htmlFor="q">Quantité</label><input id="q" inputMode="numeric" placeholder="0" value={qty} onChange={(e) => setQty(e.target.value)} /></div>
              {type === "limit" ? (
                <div className="field"><label htmlFor="l">Prix limite ({asset?.currency})</label><input id="l" inputMode="decimal" placeholder="0,00" value={limit} onChange={(e) => setLimit(e.target.value)} /></div>
              ) : side === "buy" ? (
                <div className="field"><label htmlFor="a">Compte</label><select id="a" className="input" value={account} onChange={(e) => setAccount(e.target.value as Account)}>{ACCOUNTS.map((a) => <option key={a}>{a}</option>)}</select></div>
              ) : <div />}
            </div>
            {type === "limit" && side === "buy" && (
              <div className="field"><label htmlFor="a2">Compte</label><select id="a2" className="input" value={account} onChange={(e) => setAccount(e.target.value as Account)}>{ACCOUNTS.map((a) => <option key={a}>{a}</option>)}</select></div>
            )}

            {Number(qty) > 0 && p.errors.length > 0 && <p className="error" role="alert">{p.errors[0]}</p>}
            <div className="modal-foot">
              <button type="button" className="link" onClick={onClose}>Annuler</button>
              <button type="button" className="btn" disabled={p.errors.length > 0 || !qty} onClick={() => setStep("review")}>Réviser</button>
            </div>
          </>
        )}

        {step === "review" && (
          <>
            <dl className="summary">
              <div><dt>Opération</dt><dd>{side === "buy" ? "Achat" : "Vente"}</dd></div>
              <div><dt>Titre</dt><dd>{sym} · {asset?.name}</dd></div>
              <div><dt>Type d'ordre</dt><dd>{type === "market" ? "Au marché" : `À cours limité (${money(input.limitPrice ?? 0)})`}</dd></div>
              <div><dt>Quantité</dt><dd>{input.quantity}</dd></div>
              <div><dt>Prix estimé</dt><dd>{money(p.price)} {p.currency}</dd></div>
              <div><dt>Frais estimés</dt><dd>{cad(p.fee)}</dd></div>
              <div className="total"><dt>Total estimé</dt><dd>{cad(p.total)}</dd></div>
            </dl>
            <p className="muted small">{p.executesNow ? "Cet ordre sera exécuté immédiatement au prix simulé actuel." : "Le prix actuel ne satisfait pas votre limite : l'ordre restera en attente."}</p>
            <div className="modal-foot">
              <button type="button" className="link" onClick={() => setStep("form")}>Retour</button>
              <button type="button" className="btn" onClick={confirm}>Confirmer l'ordre</button>
            </div>
          </>
        )}

        {step === "done" && result && (
          <>
            <div className={result.ok ? "banner ok" : "banner bad"} role="status">{result.message}</div>
            <div className="modal-foot"><button type="button" className="btn" onClick={onClose}>Fermer</button></div>
          </>
        )}
      </div>
    </div>
  );
}
