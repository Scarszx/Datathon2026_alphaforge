import type { Category } from "./types";

/* PRIX FICTIFS — aucune connexion à un fournisseur de cours. À remplacer par une vraie API plus tard. */

export type Asset = {
  symbol: string;
  name: string;
  category: Category;
  sector: string;
  currency: "CAD" | "USD";
  base: number;
  vol: number; // volatilité journalière
  drift: number;
};

export const USDCAD = 1.37;

export const ASSETS: Asset[] = [
  { symbol: "XEQT.TO", name: "iShares Core Equity ETF Portfolio", category: "Fonds et FNB", sector: "Diversifié", currency: "CAD", base: 36.4, vol: 0.008, drift: 0.0004 },
  { symbol: "NA.TO", name: "National Bank of Canada", category: "Actions", sector: "Finance", currency: "CAD", base: 142.3, vol: 0.011, drift: 0.0003 },
  { symbol: "ZAG.TO", name: "BMO Aggregate Bond Index ETF", category: "Revenu fixe", sector: "Obligations", currency: "CAD", base: 13.9, vol: 0.003, drift: 0.0001 },
  { symbol: "ENB.TO", name: "Enbridge Inc.", category: "Actions", sector: "Énergie", currency: "CAD", base: 55.6, vol: 0.009, drift: 0.0003 },
  { symbol: "SHOP.TO", name: "Shopify Inc.", category: "Actions", sector: "Technologie", currency: "CAD", base: 148.2, vol: 0.026, drift: 0.0006 },
  { symbol: "AAPL", name: "Apple Inc.", category: "Actions", sector: "Technologie", currency: "USD", base: 228.4, vol: 0.014, drift: 0.0005 },
  { symbol: "MSFT", name: "Microsoft Corp.", category: "Actions", sector: "Technologie", currency: "USD", base: 441.8, vol: 0.013, drift: 0.0005 },
  { symbol: "NVDA", name: "NVIDIA Corp.", category: "Actions", sector: "Technologie", currency: "USD", base: 139.6, vol: 0.03, drift: 0.0009 },
  { symbol: "RY.TO", name: "Royal Bank of Canada", category: "Actions", sector: "Finance", currency: "CAD", base: 178.9, vol: 0.01, drift: 0.0003 },
  { symbol: "TD.TO", name: "Toronto-Dominion Bank", category: "Actions", sector: "Finance", currency: "CAD", base: 84.1, vol: 0.011, drift: 0.0002 },
  { symbol: "CNQ.TO", name: "Canadian Natural Resources", category: "Actions", sector: "Énergie", currency: "CAD", base: 46.7, vol: 0.016, drift: 0.0003 },
  { symbol: "VFV.TO", name: "Vanguard S&P 500 Index ETF", category: "Fonds et FNB", sector: "Diversifié", currency: "CAD", base: 141.2, vol: 0.009, drift: 0.0005 },
  { symbol: "XIU.TO", name: "iShares S&P/TSX 60 Index ETF", category: "Fonds et FNB", sector: "Diversifié", currency: "CAD", base: 41.5, vol: 0.007, drift: 0.0003 },
  { symbol: "XBB.TO", name: "iShares Core Canadian Universe Bond", category: "Revenu fixe", sector: "Obligations", currency: "CAD", base: 27.4, vol: 0.003, drift: 0.0001 },
];

export const assetOf = (symbol: string) => ASSETS.find((a) => a.symbol === symbol);
export const fxOf = (symbol: string) => (assetOf(symbol)?.currency === "USD" ? USDCAD : 1);

export const initialPrices = () => Object.fromEntries(ASSETS.map((a) => [a.symbol, a.base]));

/** Petite variation aléatoire pour simuler le marché. */
export function jitter(prices: Record<string, number>) {
  return Object.fromEntries(
    Object.entries(prices).map(([s, p]) => [s, Math.round(p * (1 + (Math.random() - 0.5) * 0.008) * 100) / 100]),
  );
}

/* ---------- Historique simulé (déterministe) ---------- */

function rng(seed: number) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const gauss = (r: () => number) => Math.sqrt(-2 * Math.log(r() || 1e-9)) * Math.cos(2 * Math.PI * r());
const seedOf = (s: string) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 7);

const TODAY = Math.floor(Date.now() / 86400000) * 86400;
const N = 1260; // ~5 ans de jours ouvrables
let timeline: number[] | null = null;
const cache = new Map<string, number[]>();

export function timestamps() {
  if (!timeline) {
    const t: number[] = [];
    for (let ts = TODAY; t.length < N; ts -= 86400) {
      const wd = new Date(ts * 1000).getUTCDay();
      if (wd !== 0 && wd !== 6) t.unshift(ts);
    }
    timeline = t;
  }
  return timeline;
}

export function closes(symbol: string) {
  let c = cache.get(symbol);
  if (!c) {
    const a = assetOf(symbol);
    const r = rng(seedOf(symbol));
    const raw: number[] = [100];
    for (let i = 1; i < N; i++) raw.push(raw[i - 1] * (1 + (a?.drift ?? 0.0003) + (a?.vol ?? 0.01) * gauss(r)));
    const k = (a?.base ?? 100) / raw[N - 1];
    c = raw.map((v) => v * k);
    cache.set(symbol, c);
  }
  return c;
}

export const prevClose = (symbol: string) => closes(symbol)[N - 2];

export const RANGE_KEYS = ["1M", "3M", "AAJ", "1A", "Max"] as const;
export type RangeKey = (typeof RANGE_KEYS)[number];

/** Index de départ dans la ligne du temps pour une période. */
export function rangeStart(key: RangeKey) {
  const t = timestamps();
  if (key === "Max") return 0;
  const from =
    key === "AAJ"
      ? Math.floor(Date.UTC(new Date().getUTCFullYear(), 0, 1) / 1000)
      : TODAY - { "1M": 30, "3M": 90, "1A": 365 }[key] * 86400;
  const i = t.findIndex((x) => x >= from);
  return i < 0 ? 0 : i;
}
