/*
 * MODE DÉMO (VITE_DEMO=1 à la construction) : remplace Cognito et l'API /v1 par une simulation locale
 * qui respecte le contrat (mêmes routes, mêmes schémas, mêmes codes d'erreur). Données dans localStorage.
 * Prix et historiques FICTIFS. Sans VITE_DEMO, ce module n'est jamais appelé.
 */
import { ApiError } from "./errors";
import type {
  AgentsRegistry, Asset, Conversation, Explanation, Holding, InvestorProfile, Message, Portfolio,
  PortfolioSummary, Slice, SummaryRange, User,
} from "./types";

export const DEMO = import.meta.env.VITE_DEMO === "1";

/* ---------- Base locale ---------- */

type DemoUser = { userId: string; username: string; displayName?: string; email: string; password: string; investorProfile: InvestorProfile | null };
type DB = {
  users: Record<string, DemoUser>; // clé : username en minuscules
  portfolios: Record<string, Portfolio[]>; // clé : userId
  conversations: Record<string, Conversation[]>;
  messages: Record<string, Message[]>; // clé : sessionId
};

const DB_KEY = "af.demo.db";
const now = () => new Date().toISOString();
const id = (p: string) => `${p}_${Math.random().toString(36).slice(2, 10)}`;

function seed(): DB {
  const demo: DemoUser = { userId: "u_demo", username: "demo", email: "demo@example.com", password: "demo1234", investorProfile: null };
  return {
    users: { demo },
    portfolios: { u_demo: [starter("Principal")] },
    conversations: { u_demo: [] },
    messages: {},
  };
}

function starter(name: string): Portfolio {
  return {
    portfolioId: "main", name, baseCurrency: "CAD", updatedAt: now(),
    holdings: [
      { ticker: "XIC", quantity: 120, avgCost: 33.1 },
      { ticker: "VFV", quantity: 40, avgCost: 118.5 },
      { ticker: "ZAG", quantity: 150, avgCost: 13.9 },
      { ticker: "RY", quantity: 15, avgCost: 142.0 },
      { ticker: "MSFT", quantity: 6, avgCost: 380.0 },
    ],
  };
}

function load(): DB {
  try {
    const v = JSON.parse(localStorage.getItem(DB_KEY) ?? "null");
    if (v && v.users) return v;
  } catch { /* base illisible : on repart du jeu de départ */ }
  const db = seed();
  save(db);
  return db;
}
const save = (db: DB) => localStorage.setItem(DB_KEY, JSON.stringify(db));

/* ---------- Authentification simulée ---------- */

const TOKEN_PREFIX = "demo.";

export function demoSignIn(username: string, password: string): string {
  const u = load().users[username.trim().toLowerCase()];
  if (!u || u.password !== password) throw new ApiError("UNAUTHORIZED", "Identifiants invalides.", 401);
  return TOKEN_PREFIX + u.userId;
}

export function demoSignUp(username: string, password: string, email: string, displayName: string) {
  const db = load();
  const k = username.trim().toLowerCase();
  if (db.users[k]) throw new ApiError("VALIDATION_ERROR", "Ce nom d'utilisateur est déjà pris.", 400);
  if (password.length < 8) throw new ApiError("VALIDATION_ERROR", "Mot de passe refusé : au moins 8 caractères.", 400);
  const userId = id("u");
  db.users[k] = { userId, username: username.trim(), displayName, email, password, investorProfile: null };
  db.portfolios[userId] = [starter("Principal")];
  db.conversations[userId] = [];
  save(db);
}

/* ---------- Univers d'actifs et prix fictifs ---------- */

type DemoAsset = Asset & { price: number; vol: number; drift: number };
const ASSETS: DemoAsset[] = [
  { ticker: "XIC", name: "iShares Core S&P/TSX Capped Composite", assetClass: "etf", market: "TSX", currency: "CAD", sector: "Diversifié", price: 38.4, vol: 0.13, drift: 0.07 },
  { ticker: "VFV", name: "Vanguard S&P 500 Index ETF", assetClass: "etf", market: "TSX", currency: "CAD", sector: "Diversifié", price: 142.2, vol: 0.15, drift: 0.1 },
  { ticker: "ZAG", name: "BMO Aggregate Bond Index ETF", assetClass: "bond", market: "TSX", currency: "CAD", sector: "Obligations", price: 13.7, vol: 0.05, drift: 0.02 },
  { ticker: "XEF", name: "iShares Core MSCI EAFE IMI", assetClass: "etf", market: "TSX", currency: "CAD", sector: "Diversifié", price: 36.9, vol: 0.14, drift: 0.06 },
  { ticker: "RY", name: "Banque Royale du Canada", assetClass: "equity", market: "TSX", currency: "CAD", sector: "Finance", price: 168.3, vol: 0.18, drift: 0.08 },
  { ticker: "TD", name: "Banque Toronto-Dominion", assetClass: "equity", market: "TSX", currency: "CAD", sector: "Finance", price: 84.1, vol: 0.2, drift: 0.04 },
  { ticker: "ENB", name: "Enbridge", assetClass: "equity", market: "TSX", currency: "CAD", sector: "Énergie", price: 58.6, vol: 0.17, drift: 0.05 },
  { ticker: "SHOP", name: "Shopify", assetClass: "equity", market: "TSX", currency: "CAD", sector: "Technologie", price: 152.0, vol: 0.45, drift: 0.15 },
  { ticker: "AAPL", name: "Apple", assetClass: "equity", market: "NASDAQ", currency: "USD", sector: "Technologie", price: 228.5, vol: 0.25, drift: 0.12 },
  { ticker: "MSFT", name: "Microsoft", assetClass: "equity", market: "NASDAQ", currency: "USD", sector: "Technologie", price: 431.0, vol: 0.24, drift: 0.13 },
  { ticker: "NVDA", name: "NVIDIA", assetClass: "equity", market: "NASDAQ", currency: "USD", sector: "Technologie", price: 142.8, vol: 0.5, drift: 0.25 },
  { ticker: "CASH", name: "Encaisse (CAD)", assetClass: "cash", currency: "CAD", sector: "Encaisse", price: 1, vol: 0, drift: 0 },
];
const USDCAD = 1.37;
const fx = (c?: string) => (c === "USD" ? USDCAD : 1);
const asset = (t: string) => ASSETS.find((a) => a.ticker === t.toUpperCase());

const RANGE_DAYS: Record<SummaryRange, number> = { "1m": 21, "6m": 126, "1y": 252, "5y": 1260 };

/** Historique déterministe (même ticker → même courbe), qui se termine au prix actuel. */
function history(a: DemoAsset, days: number): number[] {
  let s = [...a.ticker].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
  const rnd = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 2 ** 32; };
  const sd = a.vol / Math.sqrt(252), mu = a.drift / 252;
  const logs = [0];
  for (let i = 1; i < 1261; i++) {
    const z = Math.sqrt(-2 * Math.log(rnd() || 1e-9)) * Math.cos(2 * Math.PI * rnd());
    logs.push(logs[i - 1] + mu + sd * z);
  }
  const last = logs[logs.length - 1];
  return logs.slice(-days - 1).map((l) => a.price * Math.exp(l - last));
}

function summary(p: Portfolio, range: SummaryRange): PortfolioSummary {
  const days = RANGE_DAYS[range];
  const rows = p.holdings.map((h) => ({ h, a: asset(h.ticker)! }));
  const series = rows.map(({ a }) => history(a, days));
  const values = series[0]?.map((_, i) => rows.reduce((s, { h, a }, j) => s + h.quantity * series[j][i] * fx(a.currency), 0)) ?? [];
  const value = values[values.length - 1] ?? 0;
  const prevDay = values[values.length - 2] ?? value;
  const cost = rows.reduce((s, { h, a }) => s + h.quantity * h.avgCost * fx(a.currency), 0);
  const step = Math.max(1, Math.floor(values.length / 120)); // ~120 points max pour le graphique
  const dates = values.map((_, i) => new Date(Date.now() - (values.length - 1 - i) * 86400000 * (365 / 252)).toISOString().slice(0, 10));

  const holdings = rows.map(({ h, a }, j) => {
    const price = series[j][series[j].length - 1], prev = series[j][series[j].length - 2] ?? price;
    const v = h.quantity * price * fx(a.currency), c = h.quantity * h.avgCost * fx(a.currency);
    return {
      ticker: a.ticker, name: a.name, assetClass: a.assetClass, sector: a.sector, currency: a.currency ?? "CAD",
      quantity: h.quantity, avgCost: h.avgCost, price: round(price), value: round(v),
      weight: round(value ? (v / value) * 100 : 0), pnl: round(v - c), pnlPct: round(c ? ((v - c) / c) * 100 : 0),
      dayChangePct: round(prev ? ((price - prev) / prev) * 100 : 0),
    };
  });
  const group = (key: (x: (typeof holdings)[number]) => string): Slice[] => {
    const m = new Map<string, number>();
    for (const x of holdings) m.set(key(x), (m.get(key(x)) ?? 0) + x.weight);
    return [...m].map(([label, weight]) => ({ label, weight: round(weight) })).sort((a, b) => b.weight - a.weight);
  };
  const rets = values.slice(1).map((v, i) => Math.log(v / values[i]));
  const mean = rets.reduce((a, b) => a + b, 0) / (rets.length || 1);
  const vol = Math.sqrt(rets.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(1, rets.length - 1)) * Math.sqrt(252) * 100;
  let peak = -Infinity, mdd = 0;
  for (const v of values) { peak = Math.max(peak, v); mdd = Math.min(mdd, (v - peak) / peak); }

  return {
    portfolioId: p.portfolioId, baseCurrency: p.baseCurrency, asOf: now(),
    totals: {
      value: round(value), cost: round(cost), pnl: round(value - cost), pnlPct: round(cost ? ((value - cost) / cost) * 100 : 0),
      dayChange: round(value - prevDay), dayChangePct: round(prevDay ? ((value - prevDay) / prevDay) * 100 : 0),
    },
    holdings,
    allocation: { byAssetClass: group((x) => x.assetClass), bySector: group((x) => x.sector ?? "Autre"), byCurrency: group((x) => x.currency) },
    performance: {
      range,
      points: values.flatMap((v, i) => (i % step === 0 || i === values.length - 1 ? [{ date: dates[i], value: round(v) }] : [])),
    },
    risk: { volatility: round(vol), maxDrawdown: round(Math.abs(mdd) * 100) },
    warnings: ["Mode démo : prix et historiques fictifs, générés dans le navigateur."],
    explanation: demoExplanation("portfolio.summary", { portfolioId: p.portfolioId, range }),
  };
}
const round = (n: number) => Math.round(n * 100) / 100;

function demoExplanation(tool: string, params: Record<string, unknown>): Explanation {
  return {
    sources: [{ id: "demo-prices", dataset: "Prix fictifs (mode démo)", asOf: now().slice(0, 10) }],
    assumptions: [`Taux USD/CAD fixe : ${USDCAD}`],
    limitations: ["Simulation locale : aucune donnée de marché réelle, aucun agent réel."],
    steps: [{ agentId: "demo", tool, params, status: "ok", durationMs: 1 }],
    checks: [{ agentId: "demo", rule: "simulation_only", status: "pass", message: "Aucune transaction réelle." }],
  };
}

/* ---------- Assistant simulé ---------- */

const RISK_FR: Record<string, string> = { low: "faible", low_moderate: "faible à modéré", moderate: "modéré", high: "élevé" };

function reply(db: DB, u: DemoUser, text: string): string {
  const p = db.portfolios[u.userId]?.[0];
  const s = p && p.holdings.length ? summary(p, "1y") : null;
  const t = text.toLowerCase();
  const prof = u.investorProfile;
  const profLine = prof ? `Votre profil indique un risque ${RISK_FR[prof.riskLevel]} et un horizon d'au moins ${prof.horizonMinYears} an(s).` : "Votre profil investisseur n'est pas rempli (page Profil).";
  if (!s) return `Votre portefeuille est vide. Ajoutez des positions sur la page Portefeuille. ${profLine}`;
  const top = [...s.holdings].sort((a, b) => b.weight - a.weight)[0];
  if (/risque|volatil|baisse|perte/.test(t))
    return `Sur un an, la volatilité annualisée du portefeuille est de ${s.risk.volatility.toFixed(1)} % et la baisse maximale de ${s.risk.maxDrawdown.toFixed(1)} %. ${profLine}`;
  if (/répartition|repartition|allocation|secteur|diversif/.test(t))
    return `Répartition par secteur : ${s.allocation.bySector.map((x) => `${x.label} ${x.weight.toFixed(1)} %`).join(", ")}. Votre plus grosse position est ${top.ticker} (${top.weight.toFixed(1)} %).`;
  return `Votre portefeuille vaut ${s.totals.value.toFixed(2)} ${s.baseCurrency}, pour un gain/perte de ${s.totals.pnl.toFixed(2)} (${s.totals.pnlPct.toFixed(2)} %). ${profLine} Posez une question sur le risque ou la répartition pour plus de détails.`;
}

/* ---------- Routeur /v1 ---------- */

type Opts = { method?: string; query?: Record<string, string | number | undefined | null>; body?: any };

export async function demoRequest(path: string, o: Opts, token: string): Promise<unknown> {
  await new Promise((r) => setTimeout(r, 150)); // latence simulée
  const db = load();
  const u = Object.values(db.users).find((x) => TOKEN_PREFIX + x.userId === token);
  if (!u) throw new ApiError("UNAUTHORIZED", "Session expirée.", 401);
  const m = (o.method ?? "GET").toUpperCase();
  const seg = path.split("/").filter(Boolean).map(decodeURIComponent);
  const me = (): User => ({ userId: u.userId, username: u.username, displayName: u.displayName ?? u.username, baseCurrency: "CAD", investorProfile: u.investorProfile });
  const portfolios = (db.portfolios[u.userId] ??= []);
  const convs = (db.conversations[u.userId] ??= []);
  const findP = (pid: string) => portfolios.find((p) => p.portfolioId === pid) ?? (() => { throw new ApiError("PORTFOLIO_NOT_FOUND", "", 404); })();
  const findC = (sid: string) => convs.find((c) => c.sessionId === sid) ?? (() => { throw new ApiError("CONVERSATION_NOT_FOUND", "", 404); })();
  const done = <T>(v: T) => { save(db); return v; };

  if (seg[0] === "me" && seg.length === 1 && m === "GET") return me();
  if (seg[0] === "me" && seg[1] === "profile" && m === "PUT") { u.investorProfile = o.body; return done(me()); }

  if (seg[0] === "portfolios") {
    if (seg.length === 1 && m === "GET") return { items: portfolios };
    const p = findP(seg[1]);
    if (seg[2] === "holdings" && m === "PUT") {
      const hs: Holding[] = o.body?.holdings ?? [];
      const bad = hs.find((h) => !asset(h.ticker));
      if (bad) throw new ApiError("ASSET_NOT_FOUND", `${bad.ticker} n'existe pas dans l'univers d'actifs (démo : ${ASSETS.map((a) => a.ticker).join(", ")}).`, 404);
      p.holdings = hs.map((h) => ({ ...h, ticker: h.ticker.toUpperCase() }));
      p.updatedAt = now();
      return done(p);
    }
    if (seg[2] === "summary" && m === "GET") return summary(p, (o.query?.range as SummaryRange) ?? "1y");
  }

  if (seg[0] === "market" && seg[1] === "search") {
    const q = String(o.query?.q ?? "").toLowerCase();
    return { items: ASSETS.filter((a) => a.ticker.toLowerCase().startsWith(q) || a.name.toLowerCase().includes(q)).slice(0, 8).map(({ price, vol, drift, ...a }) => a) };
  }

  if (seg[0] === "conversations") {
    if (seg.length === 1 && m === "GET") return { items: [...convs].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)), nextCursor: null };
    if (seg.length === 1 && m === "POST") {
      const c: Conversation = { sessionId: id("s"), title: o.body?.title, createdAt: now(), updatedAt: now() };
      convs.push(c); db.messages[c.sessionId] = [];
      return done(c);
    }
    const c = findC(seg[1]);
    if (seg.length === 2 && m === "PATCH") { c.title = o.body?.title; c.updatedAt = now(); return done(c); }
    if (seg.length === 2 && m === "DELETE") {
      db.conversations[u.userId] = convs.filter((x) => x !== c); delete db.messages[c.sessionId];
      save(db); return undefined;
    }
    const msgs = (db.messages[c.sessionId] ??= []);
    if (seg[2] === "messages" && m === "GET") return { items: msgs, nextCursor: null };
    if (seg[2] === "messages" && m === "POST") {
      const base = { sessionId: c.sessionId, status: "done" as const, createdAt: now() };
      const userMessage: Message = { ...base, messageId: id("m"), role: "user", content: String(o.body?.content ?? "") };
      const assistantMessage: Message = {
        ...base, messageId: id("m"), role: "assistant", content: reply(db, u, userMessage.content),
        explanation: demoExplanation("assistant.reply", { sessionId: c.sessionId }),
      };
      msgs.push(userMessage, assistantMessage);
      c.updatedAt = now();
      return done({ userMessage, assistantMessage });
    }
  }

  if (seg[0] === "agents" && m === "GET") {
    const r: AgentsRegistry = {
      agents: [{ id: "demo", name: "Agent démo", role: "Réponses simulées à partir du portefeuille et du profil", allowedTools: ["portfolio.summary"] }],
      tools: [{ id: "portfolio.summary", description: "Résumé calculé du portefeuille (prix fictifs)", reads: ["portfolios"] }],
    };
    return r;
  }

  throw new ApiError("VALIDATION_ERROR", `Route non simulée en mode démo : ${m} /v1${path}`, 400);
}
