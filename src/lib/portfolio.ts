import { assetOf, closes, fxOf, prevClose, rangeStart, timestamps, type RangeKey } from "./market";
import type { Account, Category, Holding, Prices, UserData } from "./types";

export type Row = Holding & {
  price: number;
  fx: number;
  currency: "CAD" | "USD";
  value: number;
  cost: number;
  day: number;
  gainPct: number;
};

export const ALL = "Tous les comptes";

export function computePortfolio(d: UserData, prices: Prices, account: string = ALL) {
  const holdings = account === ALL ? d.holdings : d.holdings.filter((h) => h.account === (account as Account));
  const rows: Row[] = holdings
    .map((h) => {
      const fx = fxOf(h.symbol);
      const price = prices[h.symbol] ?? h.avgCost;
      return {
        ...h,
        price,
        fx,
        currency: assetOf(h.symbol)?.currency ?? "CAD",
        value: h.quantity * price * fx,
        cost: h.quantity * h.avgCost * fx,
        day: h.quantity * (price - prevClose(h.symbol)) * fx,
        gainPct: (price / h.avgCost - 1) * 100,
      } as Row;
    })
    .sort((a, b) => b.value - a.value);

  const cash = account === ALL ? d.cash : 0;
  const invested = rows.reduce((s, r) => s + r.value, 0);
  const total = invested + cash;
  const day = rows.reduce((s, r) => s + r.day, 0);
  const dayPct = invested - day > 0 ? (day / (invested - day)) * 100 : 0;
  const costTotal = rows.reduce((s, r) => s + r.cost, 0);
  const unrealized = invested - costTotal;

  const group = (key: (r: Row) => string, extraCash = true) => {
    const m = new Map<string, number>();
    rows.forEach((r) => m.set(key(r), (m.get(key(r)) ?? 0) + r.value));
    if (extraCash && cash > 0) m.set("Liquidités", cash);
    return [...m.entries()]
      .map(([name, value]) => ({ name, value, pct: total > 0 ? (value / total) * 100 : 0 }))
      .sort((a, b) => b.value - a.value);
  };

  return {
    rows, cash, invested, total, day, dayPct, costTotal, unrealized,
    byCategory: group((r) => r.category),
    bySector: group((r) => r.sector),
  };
}

/** Valeur historique des positions actuelles + liquidités. */
export function series(rows: Row[], cash: number, range: RangeKey) {
  const t = timestamps();
  const from = rangeStart(range);
  const ts = t.slice(from);
  const values = ts.map((_, k) => rows.reduce((s, r) => s + r.quantity * closes(r.symbol)[from + k] * r.fx, 0) + cash);
  return { timestamps: ts, values };
}

export function riskMetrics(rows: Row[], cash: number) {
  const total = rows.reduce((s, r) => s + r.value, 0) + cash;
  const s = series(rows, cash, "1A").values;
  const rets = s.slice(1).map((v, i) => v / s[i] - 1);
  const mean = rets.reduce((a, b) => a + b, 0) / (rets.length || 1);
  const vol = Math.sqrt(rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (rets.length || 1)) * Math.sqrt(252) * 100;
  let peak = s[0] ?? 0, maxDd = 0;
  s.forEach((v) => { peak = Math.max(peak, v); maxDd = Math.min(maxDd, v / peak - 1); });
  const w = rows.map((r) => (total > 0 ? r.value / total : 0));
  const equity = rows.filter((r) => r.category !== "Revenu fixe").reduce((a, r) => a + r.value, 0);
  const top = rows[0];
  return {
    volatilityPct: vol,
    maxDrawdownPct: maxDd * 100,
    equityPct: total > 0 ? (equity / total) * 100 : 0,
    cashPct: total > 0 ? (cash / total) * 100 : 0,
    topHolding: top ? { symbol: top.symbol, pct: (top.value / total) * 100 } : null,
    concentrationHHI: Math.round(w.reduce((a, x) => a + x * x, 0) * 10000),
  };
}

export const categoryOf = (c: Category) => c;
