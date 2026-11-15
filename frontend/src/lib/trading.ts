import { assetOf, fxOf } from "./market";
import type { Holding, Order, OrderInput, Prices, Transaction, UserData } from "./types";

/* SIMULATION UNIQUEMENT — aucun ordre réel n'est transmis. */

export const FEE = 0; // frais simulés par ordre ($ CAD)
const r2 = (n: number) => Math.round(n * 100) / 100;
const uid = (p: string) => `${p}${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

export type Preview = {
  errors: string[];
  price: number;
  currency: "CAD" | "USD";
  fx: number;
  executesNow: boolean;
  gross: number;
  fee: number;
  total: number;
};

function conditionMet(i: OrderInput, price: number) {
  if (i.type === "market") return true;
  if (!i.limitPrice) return false;
  return i.side === "buy" ? price <= i.limitPrice : price >= i.limitPrice;
}

export function preview(d: UserData, prices: Prices, i: OrderInput): Preview {
  const errors: string[] = [];
  const asset = assetOf(i.symbol);
  if (!asset) errors.push("Choisissez un titre.");
  const market = prices[i.symbol] ?? 0;
  const fx = fxOf(i.symbol);
  if (!Number.isInteger(i.quantity) || i.quantity <= 0) errors.push("La quantité doit être un nombre entier positif.");
  if (i.type === "limit" && !(i.limitPrice && i.limitPrice > 0)) errors.push("Entrez un prix limite valide.");
  const executesNow = conditionMet(i, market);
  const price = i.type === "limit" && !executesNow ? i.limitPrice ?? market : market;
  const gross = r2(Math.max(0, i.quantity || 0) * price * fx);
  const fee = FEE;
  const total = i.side === "buy" ? r2(gross + fee) : r2(gross - fee);

  if (i.side === "buy" && total > d.cash && errors.length === 0) errors.push("Liquidités insuffisantes pour cet ordre.");
  if (i.side === "sell") {
    const h = d.holdings.find((x) => x.id === i.holdingId);
    if (!h) errors.push("Choisissez une position à vendre.");
    else if (i.quantity > h.quantity) errors.push(`Vous ne possédez que ${h.quantity} titre${h.quantity > 1 ? "s" : ""}.`);
  }
  return { errors, price, currency: asset?.currency ?? "CAD", fx, executesNow, gross, fee, total };
}

function execute(d: UserData, o: Order, price: number): UserData {
  const fx = fxOf(o.symbol);
  const asset = assetOf(o.symbol)!;
  const gross = r2(o.quantity * price * fx);
  let holdings: Holding[];
  let cash: number;

  if (o.side === "buy") {
    cash = r2(d.cash - gross - FEE);
    const ex = d.holdings.find((h) => h.symbol === o.symbol && h.account === o.account);
    holdings = ex
      ? d.holdings.map((h) =>
          h === ex ? { ...h, quantity: h.quantity + o.quantity, avgCost: r2((h.quantity * h.avgCost + o.quantity * price) / (h.quantity + o.quantity)) } : h,
        )
      : [...d.holdings, { id: uid("h"), symbol: o.symbol, name: asset.name, account: o.account, category: asset.category, sector: asset.sector, quantity: o.quantity, avgCost: price }];
  } else {
    cash = r2(d.cash + gross - FEE);
    holdings = d.holdings
      .map((h) => (h.id === o.holdingId ? { ...h, quantity: h.quantity - o.quantity } : h))
      .filter((h) => h.quantity > 0);
  }
  const tx: Transaction = {
    id: uid("t"), date: Date.now(), symbol: o.symbol, side: o.side, quantity: o.quantity, price,
    currency: asset.currency, totalCad: o.side === "buy" ? r2(gross + FEE) : r2(gross - FEE), account: o.account,
  };
  const orders = d.orders.map((x) => (x.id === o.id ? { ...x, status: "filled" as const, fillPrice: price } : x));
  return { ...d, cash, holdings, transactions: [tx, ...d.transactions], orders };
}

export function placeOrder(d: UserData, prices: Prices, i: OrderInput): { data: UserData; order?: Order; errors: string[] } {
  const p = preview(d, prices, i);
  if (p.errors.length) return { data: d, errors: p.errors };
  const h = d.holdings.find((x) => x.id === i.holdingId);
  const order: Order = {
    ...i, account: h?.account ?? i.account, id: uid("o"), date: Date.now(),
    name: assetOf(i.symbol)?.name ?? i.symbol, status: "pending",
  };
  const withOrder = { ...d, orders: [order, ...d.orders] };
  if (!p.executesNow) return { data: withOrder, order, errors: [] };
  const data = execute(withOrder, order, prices[i.symbol]);
  return { data, order: data.orders.find((x) => x.id === order.id), errors: [] };
}

/** Réévalue les ordres à cours limité en attente quand les prix changent. */
export function evaluatePending(d: UserData, prices: Prices): UserData {
  let cur = d;
  for (const o of d.orders.filter((x) => x.status === "pending")) {
    const price = prices[o.symbol];
    if (!conditionMet(o, price)) continue;
    const p = preview({ ...cur, orders: cur.orders }, prices, { ...o, type: "market" });
    if (p.errors.length) {
      cur = { ...cur, orders: cur.orders.map((x) => (x.id === o.id ? { ...x, status: "rejected", note: p.errors[0] } : x)) };
    } else cur = execute(cur, o, price);
  }
  return cur;
}

export function cancelOrder(d: UserData, id: string): UserData {
  return { ...d, orders: d.orders.map((o) => (o.id === id && o.status === "pending" ? { ...o, status: "cancelled" } : o)) };
}
