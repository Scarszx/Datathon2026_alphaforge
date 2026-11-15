/*
 * MODE DÉMO (VITE_DEMO=1 à la construction) : remplace Cognito et l'API /v1 par une simulation locale
 * qui respecte le contrat (mêmes routes, mêmes schémas, mêmes codes d'erreur). Données dans localStorage.
 * Prix et historiques FICTIFS. Sans VITE_DEMO, ce module n'est jamais appelé.
 */
import { ApiError } from "./errors";
import type {
  AgentsRegistry, Asset, Conversation, Evidence, Explanation, Holding, InvestorProfile, Mandate,
  MandateCreateRequest, MandateMode, Message, Narrative, Portfolio, PortfolioSummary, Run,
  Slice, SummaryRange, User, VerifierReport,
} from "./types";

export const DEMO = import.meta.env.VITE_DEMO === "1";

/* ---------- Base locale ---------- */

type DemoUser = { userId: string; username: string; displayName?: string; email: string; password: string; investorProfile: InvestorProfile | null };
type Analyses = { mandates: Mandate[]; runs: Record<string, Run> };
type DB = {
  users: Record<string, DemoUser>; // clé : username en minuscules
  portfolios: Record<string, Portfolio[]>; // clé : userId
  conversations: Record<string, Conversation[]>;
  messages: Record<string, Message[]>; // clé : sessionId
  analyses: Record<string, Analyses>; // clé : sessionId (mandats et runs)
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
    analyses: {},
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

/* ---------- Orchestrateur simulé (v0.4.0 : cadrage → mandat confirmé → analyse) ---------- */

const RISK_FR: Record<string, string> = { low: "faible", low_moderate: "faible à modéré", moderate: "modéré", high: "élevé" };
const QUICK_REPLIES = ["Et si j'ajoutais un titre ?", "Rééquilibrer mon portefeuille", "Diagnostiquer mon portefeuille"];

function detectMode(text: string): MandateMode | null {
  const t = text.toLowerCase();
  if (/diagnost|diagnose|santé|sante|état/.test(t)) return "diagnose";
  if (/rééquilibr|reequilibr|rebalance|repondér/.test(t)) return "rebalance";
  if (/ajout|achèt|achet|add|nvda|tesla|apple|msft|position/.test(t)) return "add_asset";
  return null;
}

function objectiveEnum(o: string): MandateCreateRequest["objective"] {
  const s = o.toLowerCase();
  if (/revenu|income/.test(s)) return "income";
  if (/préserv|preserv|capital/.test(s)) return "preservation";
  if (/retrait|retire/.test(s)) return "retirement";
  if (/projet|condo|project/.test(s)) return "project";
  return "growth";
}

function detectTicker(text: string): string | undefined {
  const up = text.toUpperCase();
  return ASSETS.find((a) => a.ticker.length > 2 && up.includes(a.ticker))?.ticker;
}

/** Mandat proposé : déduit du profil investisseur (persona) et du portefeuille, champs texte en anglais. */
function draftFrom(u: DemoUser, p: Portfolio, mode: MandateMode, text: string): MandateCreateRequest {
  const prof = u.investorProfile;
  const subject = detectTicker(text);
  const s = summary(p, "1y");
  return {
    portfolioId: p.portfolioId,
    mode,
    objective: prof ? objectiveEnum(prof.objective) : "growth",
    horizonYears: prof?.horizonMinYears ?? 10,
    riskTolerance: prof?.riskTolerance ?? 3,
    riskCapacity: prof?.riskCapacity ?? 3,
    maxAcceptableLossPct: prof?.horizonMinYears ? (prof.horizonMinYears < 3 ? 10 : prof.horizonMinYears <= 8 ? 20 : 35) : 20,
    constraints: prof?.constraints ?? ["diversification minimale"],
    preferences: prof?.preferences?.some((x) => /esg/i.test(x)) ? { esg: true, excludedSectors: [], excludedAssetClasses: ["crypto"] } : { excludedSectors: [], excludedAssetClasses: prof?.excludedAssetClasses ?? [] },
    province: prof?.province ?? "QC",
    userLanguage: "fr",
    operations: mode === "add_asset" && subject ? [{ action: "add", ticker: subject, amount: Math.round(s.totals.value * 0.1), currency: "CAD" }] : [],
    subjectTicker: mode === "diagnose" ? subject : undefined,
    fieldSources: { mode: "user_answer", objective: "persona", horizonYears: "persona", riskTolerance: "persona", riskCapacity: "persona", maxAcceptableLossPct: "team_assumption", province: "persona", ...(subject ? { subjectTicker: "user_answer" } : {}) },
  };
}

const MODE_FR: Record<MandateMode, string> = { add_asset: "l'ajout d'un titre", rebalance: "le rééquilibrage", diagnose: "le diagnostic de votre portefeuille" };

const JURISDICTIONS = ["CA", "QC", "ON", "BC", "AB", "SK", "MB", "NB", "NS", "PE", "NL", "YT", "NT", "NU"];
const OBJECTIVES = ["growth", "income", "preservation", "project", "retirement"];

/** Validation serveur (Lambda API, sans LLM) : enums, bornes, province ≠ CA, présence des champs requis. */
function validateMandate(req: MandateCreateRequest, portfolios: Portfolio[]): void {
  const fail = (msg: string) => { throw new ApiError("VALIDATION_ERROR", msg, 422); };
  if (!req || typeof req !== "object") fail("Corps de la requête invalide.");
  if (!portfolios.some((p) => p.portfolioId === req.portfolioId))
    throw new ApiError("PORTFOLIO_NOT_FOUND", "", 404);
  if (!["add_asset", "rebalance", "diagnose"].includes(req.mode)) fail(`Mode inconnu : ${req.mode}.`);
  if (!OBJECTIVES.includes(req.objective)) fail(`Objectif inconnu : ${req.objective}.`);
  if (!Number.isInteger(req.horizonYears) || req.horizonYears < 1 || req.horizonYears > 100)
    fail("L'horizon doit être un nombre entier d'années entre 1 et 100.");
  if (!Number.isInteger(req.riskTolerance) || req.riskTolerance < 1 || req.riskTolerance > 5)
    fail("La tolérance à la perte doit être un entier de 1 à 5.");
  if (!Number.isInteger(req.riskCapacity) || req.riskCapacity < 1 || req.riskCapacity > 5)
    fail("La capacité à encaisser une perte doit être un entier de 1 à 5.");
  if (req.maxAcceptableLossPct !== undefined && (typeof req.maxAcceptableLossPct !== "number" || req.maxAcceptableLossPct <= 0 || req.maxAcceptableLossPct > 100))
    fail("La perte maximale acceptable doit être un pourcentage entre 0 (exclu) et 100.");
  if (!JURISDICTIONS.includes(req.province)) fail(`Province inconnue : ${req.province}.`);
  if (req.province === "CA") fail("La province « CA » désigne les textes nationaux, pas une province de résidence : choisissez votre province.");
  for (const op of req.operations ?? []) {
    if (!["add", "remove", "set_weight"].includes(op.action)) fail(`Opération inconnue : ${op.action}.`);
    if (!op.ticker?.trim()) fail("Chaque opération doit nommer un ticker.");
  }
}

/** Champs dont la valeur a changé depuis la version précédente (contrat : changedFields). */
function changedFields(prev: MandateCreateRequest, next: MandateCreateRequest): string[] {
  const keys = new Set([...Object.keys(prev), ...Object.keys(next)]);
  const out: string[] = [];
  for (const k of keys) {
    if (k === "fieldSources") continue;
    if (JSON.stringify((prev as Record<string, unknown>)[k]) !== JSON.stringify((next as Record<string, unknown>)[k])) out.push(k);
  }
  return out;
}

/** Réponse de l'orchestrateur simulé : cadrage (quickReplies), brouillon de mandat, ou suivi sur le registre. */
function orchestratorReply(db: DB, u: DemoUser, sessionId: string, text: string): Message {
  const base = { sessionId, status: "done" as const, createdAt: now() };
  const p = db.portfolios[u.userId]?.[0];
  const prior = (db.messages[sessionId] ?? []).filter((x) => x.role === "assistant");
  const prof = u.investorProfile;
  const profLine = prof
    ? `Votre profil indique un risque ${RISK_FR[prof.riskLevel] ?? prof.riskLevel}${prof.riskTolerance ? `, une tolérance de ${prof.riskTolerance}/5 et une capacité de ${prof.riskCapacity ?? "?"}/5` : ""}${prof.province ? ` (province : ${prof.province})` : ""}.`
    : "Votre profil investisseur n'est pas rempli (page Profil) : le mandat utilisera des valeurs par défaut prudentes.";

  // 1. Cadrage : au plus une étape de questions, aucun calcul tant que le mandat n'est pas confirmé.
  if (!prior.length) {
    const welcome = p && p.holdings.length
      ? `Je comprends que vous voulez tester une idée. Je ne calcule rien et je ne recommande rien : je cadre votre intention en un mandat, puis j'audite l'analyse contre les textes réglementaires canadiens. ${profLine}`
      : `Votre portefeuille est vide : ajoutez des positions sur la page Portefeuille, puis revenez cadrer votre idée. ${profLine}`;
    return { ...base, messageId: id("m"), role: "assistant", content: welcome, quickReplies: QUICK_REPLIES, explanation: demoExplanation("assistant.frame", { sessionId }) };
  }

  // 2. Intention reconnue : brouillon de mandat à confirmer (aucun run lancé ici).
  const mode = detectMode(text);
  if (mode && p) {
    const draft = draftFrom(u, p, mode, text);
    return {
      ...base, messageId: id("m"), role: "assistant",
      content: `Voici le mandat proposé pour ${MODE_FR[mode]}. Vérifiez chaque champ (la source de chaque ligne est affichée), puis confirmez pour lancer l'analyse. Les curseurs « et si » resteront disponibles après la confirmation.`,
      mandateDraft: draft,
      explanation: demoExplanation("assistant.propose_mandate", { sessionId, mode }),
    };
  }

  // 3. Suivi : réponse à partir du registre du dernier run, sans nouveau calcul.
  const lastRun = Object.values(db.analyses[sessionId]?.runs ?? {}).sort((a, b) => b.createdAt.localeCompare(a.createdAt))[0];
  if (lastRun?.narrative) {
    const why = lastRun.narrative.sections.find((x) => x.key === "why")?.text ?? "";
    return { ...base, messageId: id("m"), role: "assistant", content: `D'après le registre de la dernière analyse : ${why}`, runId: lastRun.runId, explanation: demoExplanation("assistant.read_evidence", { sessionId, runId: lastRun.runId }) };
  }
  return { ...base, messageId: id("m"), role: "assistant", content: `Je n'ai encore rien calculé : confirmez d'abord un mandat (carte ci-dessus) ou utilisez les curseurs « et si ». ${profLine}`, explanation: demoExplanation("assistant.frame", { sessionId }) };
}

/* ---------- Analyse simulée (module-engine, règles, auditeur, rédacteur, vérificateur) ---------- */

const DEMO_SOURCE = "Prix fictifs (mode démo)";
const worstWindow = (v: number[], days: number) => {
  let w = 0;
  for (let i = days; i < v.length; i++) w = Math.max(w, (v[i - days] - v[i]) / v[i - days]);
  return w * 100;
};

function scenarioPortfolios(p: Portfolio, mandate: MandateCreateRequest): { holdings: { ticker: string; quantity: number }[]; label: string; description?: string; proxyNote?: string }[] {
  const cur = p.holdings.map(({ ticker, quantity }) => ({ ticker, quantity }));
  const s0 = { holdings: cur, label: "Portefeuille actuel" };
  const s1 = { holdings: applyOps(cur, mandate, p), label: "Idée telle quelle" };
  const broad = mandate.mode === "diagnose" ? (mandate.subjectTicker ? "XIC" : undefined) : mandate.subjectTicker ? "XIC" : undefined;
  const altHoldings = mandate.subjectTicker
    ? cur.map((h) => (h.ticker === mandate.subjectTicker && broad ? { ticker: broad, quantity: Math.round((h.quantity * (asset(mandate.subjectTicker!)?.price ?? 1)) / (asset(broad)?.price ?? 1)) } : h))
    : cur;
  const s2 = { holdings: altHoldings, label: "Alternative (par catégorie d'actifs)", description: "Exposition large équivalente, formulée par catégorie d'actifs : jamais la recommandation d'un titre précis.", proxyNote: mandate.subjectTicker ? `Exposition approchée par XIC pour le calcul (mode démo).` : undefined };
  return [s0, s1, s2];
}

function applyOps(holdings: { ticker: string; quantity: number }[], mandate: MandateCreateRequest, p: Portfolio): { ticker: string; quantity: number }[] {
  let out = holdings.map((h) => ({ ...h }));
  for (const op of mandate.operations ?? []) {
    const price = asset(op.ticker)?.price ?? 0;
    const fxr = asset(op.ticker)?.currency === "USD" ? USDCAD : 1;
    const qty = price ? (op.amount ?? 0) / (price * fxr) : 0;
    if (op.action === "add") out = out.some((h) => h.ticker === op.ticker) ? out.map((h) => (h.ticker === op.ticker ? { ...h, quantity: h.quantity + qty } : h)) : [...out, { ticker: op.ticker, quantity: qty }];
    else if (op.action === "remove") out = out.map((h) => (h.ticker === op.ticker ? { ...h, quantity: Math.max(0, h.quantity - qty) } : h)).filter((h) => h.quantity > 0);
    else if (op.action === "set_weight") {
      const total = out.reduce((s, h) => s + h.quantity * (asset(h.ticker)?.price ?? 0), 0);
      const target = (op.weight ?? 0) / 100 * total / (price * fxr || 1);
      out = out.map((h) => (h.ticker === op.ticker ? { ...h, quantity: target } : h));
    }
  }
  return out.length ? out : p.holdings.map(({ ticker, quantity }) => ({ ticker, quantity }));
}

function scenarioValues(holdings: { ticker: string; quantity: number }[], days: number): number[] {
  const series = holdings.map((h) => history(asset(h.ticker) ?? ASSETS[0], days));
  return series[0]?.map((_, i) => holdings.reduce((s, h, j) => s + h.quantity * series[j][i] * fx(asset(h.ticker)?.currency), 0)) ?? [];
}

/** Statistique d'un scénario : métriques fictives dérivées de l'historique fictif, marquées démo. */
function metricsOf(values: number[]) {
  const rets = values.slice(1).map((v, i) => Math.log(v / values[i]));
  const mean = rets.reduce((a, b) => a + b, 0) / (rets.length || 1);
  const vol = Math.sqrt(rets.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(1, rets.length - 1)) * Math.sqrt(252) * 100;
  let peak = -Infinity, mdd = 0;
  for (const v of values) { peak = Math.max(peak, v); mdd = Math.max(mdd, (peak - v) / peak); }
  return { vol, mdd: mdd * 100, stress2022: worstWindow(values, 60) * 1.15, stressRates: worstWindow(values, 60) * 0.9 };
}

/** Preuve EV-nn d'une métrique de scénario. */
function ev(id: string, kind: Evidence["kind"], label: string, value: number, scenario: number, extra: Partial<Evidence> = {}): Evidence {
  return { id, kind, label, value: round(value), formatted: `${value.toFixed(1)} %`, scenario, source: DEMO_SOURCE, asOf: now().slice(0, 10), caveats: ["Valeur fictive générée en mode démo."], ...extra };
}

function bandProfile(vol: number) { return vol <= 10 ? 1 : vol <= 14 ? 2 : vol <= 18 ? 3 : vol <= 25 ? 4 : 5; }

/** Analyse complète d'un mandat confirmé : scénarios, preuves, verdicts (partial), puis narrative + vérificateur (done). */
function buildRun(db: DB, u: DemoUser, sessionId: string, mandate: Mandate, runId: string): Run {
  const p = db.portfolios[u.userId]?.find((x) => x.portfolioId === mandate.mandate.portfolioId) ?? db.portfolios[u.userId]?.[0];
  const m = mandate.mandate;
  const evidence: Evidence[] = [];
  const scenarios: Run["scenarios"] = [];
  const verdicts: Run["verdicts"] = [];
  const alts = scenarioPortfolios(p!, m);
  let evN = 0;
  const evFor = (label: string, value: number, sc: number, extra: Partial<Evidence> = {}) => ev(`EV-${String(++evN).padStart(2, "0")}`, "metric", label, value, sc, extra);

  alts.forEach((sc, i) => {
    const values = scenarioValues(sc.holdings, 252);
    const st = metricsOf(values);
    const ids = {
      volatility: evFor(`Volatilité annualisée, scénario ${i}`, st.vol, i, { method: "écart-type × √252 (démo)", window: "252 derniers jours fictifs" }).id,
      maxDrawdown: evFor(`Pire baisse, scénario ${i}`, st.mdd, i, { method: "baisses maximales (démo)" }).id,
      stress2022: evFor(`Test de résistance 2022, scénario ${i}`, st.stress2022, i, { method: "pire baisse de 60 jours × 1,15 (démo)" }).id,
      stressRates: evFor(`Test hausses de taux, scénario ${i}`, st.stressRates, i, { method: "pire baisse de 60 jours × 0,9 (démo)" }).id,
      topSingleWeight: (() => {
        const total = values[values.length - 1] ?? 0;
        const weights = sc.holdings.map((h) => h.quantity * (asset(h.ticker)?.price ?? 0) * fx(asset(h.ticker)?.currency));
        const top = Math.max(...weights, 0);
        return evFor(`Poids du premier titre, scénario ${i}`, total ? (top / total) * 100 : 0, i).id;
      })(),
      techWeightLookThrough: (() => {
        const total = values[values.length - 1] ?? 0;
        const tech = sc.holdings.filter((h) => asset(h.ticker)?.sector === "Technologie").reduce((s, h) => s + h.quantity * (asset(h.ticker)?.price ?? 0) * fx(asset(h.ticker)?.currency), 0);
        return evFor(`Poids techno (décomposé), scénario ${i}`, total ? (tech / total) * 100 : 0, i).id;
      })(),
    };
    const implied = bandProfile(st.vol);
    const diff = implied - mandate.riskProfile;
    const r1Status = i === 0 ? (diff > 0 ? "warn" : "pass") : diff >= 2 ? "fail" : diff === 1 ? "warn" : "pass";
    const r2Status = st.mdd > mandate.effectiveMaxLossPct ? "fail" : st.mdd > mandate.effectiveMaxLossPct * 0.8 ? "warn" : "pass";
    const top = parseFloat(evidence.find((e) => e.id === ids.topSingleWeight)!.formatted!) || 0;
    const r6Status = top > 20 ? "fail" : top > 10 ? "warn" : "pass";
    scenarios.push({
      index: i as 0 | 1 | 2, label: sc.label, description: sc.description, proxyNote: sc.proxyNote,
      allocation: (() => {
        const total = values[values.length - 1] ?? 0;
        const byClass = sc.holdings.reduce<Record<string, number>>((acc, h) => {
          const v = h.quantity * (asset(h.ticker)?.price ?? 0) * fx(asset(h.ticker)?.currency);
          const c = asset(h.ticker)?.assetClass ?? "etf";
          acc[c] = (acc[c] ?? 0) + v; return acc;
        }, {});
        return Object.entries(byClass).map(([label, v]) => ({ label, weight: total ? round((v / total) * 100) : 0 })).sort((a, b) => b.weight - a.weight);
      })(),
      metrics: { volatility: ids.volatility, maxDrawdown: ids.maxDrawdown, stress2022: ids.stress2022, stressRates: ids.stressRates, topSingleWeight: ids.topSingleWeight, techWeightLookThrough: ids.techWeightLookThrough },
      verdict: (r1Status === "fail" || r2Status === "fail" || r6Status === "fail") ? "fail" : (r1Status === "warn" || r2Status === "warn" || r6Status === "warn") ? "warn" : "pass",
    });
    const cryptoWeight = scenarios[i].allocation?.find((a) => /crypto/i.test(a.label))?.weight ?? 0;
    const mk = (rule: string, status: "pass" | "warn" | "fail" | "not_verified", reasonCode: string, messageEn: string, evs: string[] = [], citations: string[] = [], threshold?: { value: number; nature: "text" | "team_assumption" }) =>
      verdicts.push({ rule, scenario: i, status, reasonCode, evidence: evs, citations, ...(threshold ? { threshold } : {}), messageEn, message: messageEn } as Run["verdicts"][number]);
    mk("R1", r1Status, diff >= 1 ? "RISK_PROFILE_MISMATCH" : "RISK_PROFILE_OK", `Implied risk profile ${implied} versus mandate profile ${mandate.riskProfile}.`, [ids.volatility], r1Status === "fail" ? ["KB-01"] : [], { value: mandate.riskProfile, nature: "text" });
    mk("R2", r2Status, r2Status === "fail" ? "MAX_LOSS_EXCEEDED" : "MAX_LOSS_OK", `Worst drop ${st.mdd.toFixed(1)}% versus accepted loss ${mandate.effectiveMaxLossPct}%.`, [ids.maxDrawdown, ids.stress2022], r2Status === "fail" ? ["KB-01"] : [], { value: mandate.effectiveMaxLossPct, nature: "team_assumption" });
    mk("R3", "pass", "DIVERSIFICATION_OK", `${sc.holdings.length} holdings in the scenario.`, [], []);
    mk("R4", cryptoWeight > 5 ? "warn" : "pass", cryptoWeight > 5 ? "CRYPTO_CAP_HIGH" : "CRYPTO_CAP_OK", `Crypto weight ${cryptoWeight.toFixed(1)}% (team assumption: 5%).`, [], [], { value: 5, nature: "team_assumption" });
    mk("R5", "pass", "NO_SINGLE_NAME_ADVICE", "No specific security is recommended; alternatives are expressed by asset class.", [], []);
    mk("R6", r6Status, r6Status === "pass" ? "CONCENTRATION_OK" : "CONCENTRATION_HIGH", `Top holding weight ${top.toFixed(1)}% (team assumption: 10%).`, [ids.topSingleWeight], [], { value: 10, nature: "team_assumption" });
    mk("R7", "not_verified", "ESG_NOT_VERIFIED", "No invented ESG indicator for individual equities: left unverified unless a cited source exists.", [], cryptoWeight > 0 ? ["KB-02"] : []);
    mk("R8", "pass", "NO_INVENTED_ESG", "No ESG indicator is invented for individual equities.", [], []);
    mk("R9", "pass", "JURISDICTION_OK", `Notices for ${m.province} are displayed.`, [], []);
    mk("R10", "pass", "NO_LOOKAHEAD", "Monthly macro series are not used before their publication date (demo: fictitious data).", [], []);
  });

  return {
    runId, sessionId, mandateVersion: mandate.version, status: "partial", datasetVersion: "demo", userLanguage: "fr",
    scenarios, verdicts, evidence, jurisdictionNotices: noticesFor(m.province), createdAt: now(),
  };
}

/* agent-auditor simulé : citations KB (titres réels du corpus, extrait simulé), puis rédacteur + vérificateur. */
const KB_DEMO: Evidence[] = [
  {
    id: "KB-01", kind: "regulation", label: "Avis 31-368 des ACVM : obligation de convenance", document: "Avis conjoint 31-368 (mode démo)",
    section: "Résumé (extrait simulé)", excerpt: "[Extrait simulé en mode démo : le texte réglementaire n'est pas reproduit ici.]",
    jurisdiction: "CA", source: "docs/for_KB (démo)", url: "https://www.osc.ca", caveats: ["Extrait et référence simulés pour la démonstration."],
  },
  {
    id: "KB-02", kind: "regulation", label: "Avis 21-332 : plateformes de crypto-actifs", document: "Avis conjoint 21-332 (mode démo)",
    section: "Exigences (extrait simulé)", excerpt: "[Extrait simulé en mode démo : le texte réglementaire n'est pas reproduit ici.]",
    jurisdiction: "CA", source: "docs/for_KB (démo)", caveats: ["Extrait et référence simulés pour la démonstration."],
  },
];

function completeRun(run: Run): Run {
  const narrative = narrativeFor(run);
  return {
    ...run, status: "done", evidence: [...run.evidence, ...KB_DEMO],
    narrative, verifier: verifierFor({ ...run, narrative }), completedAt: now(),
  };
}

function noticesFor(province: string): string[] {
  if (province === "QC") return ["[démo] Simulation pédagogique. Ni l'outil ni les agents ne sont inscrits au registre de l'AMF ; aucune information présentée ne constitue un conseil financier."];
  if (province === "ON") return ["[démo] Educational simulation. The tool is not registered with the OSC and nothing shown is investment advice."];
  return ["[démo] Simulation pédagogique : aucune information présentée ne constitue un conseil financier."];
}

function narrativeFor(run: Run): Narrative {
  const s1 = run.scenarios[1], s2 = run.scenarios[2];
  const evOf = (id: string) => run.evidence.find((e) => e.id === id);
  const vol1 = evOf(s1.metrics?.volatility ?? ""), dd1 = evOf(s1.metrics?.maxDrawdown ?? "");
  const vol2 = evOf(s2.metrics?.volatility ?? "");
  const fails = run.verdicts.filter((v) => v.scenario === 1 && v.status === "fail").map((v) => v.rule);
  return {
    language: "fr",
    sections: [
      { key: "data_used", textEn: `Built from the demo price history (fictitious) and the confirmed mandate. Scenario 1 volatility: {${vol1?.id}}, worst drop: {${dd1?.id}}.`, text: `Construit à partir de l'historique de prix fictif du mode démo et du mandat confirmé. Volatilité du scénario 1 : {${vol1?.id}} ; pire baisse : {${dd1?.id}}.` },
      { key: "why", textEn: fails.length ? `Scenario 1 fails rule(s) ${fails.join(", ")}: see the verdicts above and the citations.` : `Scenario 1 passes the checks; the alternative keeps the exposure while reducing risk ({${vol2?.id}}).`, text: fails.length ? `Le scénario 1 échoue sur la ou les règles ${fails.join(", ")} : voir les verdicts et les citations.` : `Le scénario 1 passe les contrôles ; l'alternative garde l'exposition tout en réduisant le risque ({${vol2?.id}}).` },
      { key: "limits", textEn: "All figures come from fictitious demo prices; they are not market data. Past results never predict the future.", text: "Tous les chiffres viennent de prix fictifs du mode démo ; ce ne sont pas des données de marché. Le passé ne prédit jamais le futur." },
      { key: "what_would_change", textEn: "Lowering the position size, extending the horizon, or diversifying across sectors would change the verdicts.", text: "Réduire la taille de la position, allonger l'horizon ou diversifier les secteurs changerait les verdicts." },
    ],
    hiddenSentences: [],
  };
}

function verifierFor(run: Run): VerifierReport {
  // Chaque emplacement des 4 rubriques compte comme résolu ; match EN/langue = true en démo.
  const all = run.narrative?.sections.map((s) => s.text + "\n" + s.textEn).join("\n") ?? "";
  const total = (all.match(/\{(EV|KB)-\d+\}/g) ?? []).length;
  return { placeholdersResolved: total, placeholdersTotal: total, handwrittenNumbers: 0, forbiddenPhrases: 0, placeholdersMatch: true };
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
      const content = String(o.body?.content ?? "");
      if (!content.trim()) throw new ApiError("VALIDATION_ERROR", "Le message est vide.", 422);
      if (content.length > 2000) throw new ApiError("VALIDATION_ERROR", "Le message dépasse 2 000 caractères.", 422);
      const base = { sessionId: c.sessionId, status: "done" as const, createdAt: now() };
      const userMessage: Message = { ...base, messageId: id("m"), role: "user", content };
      const assistantMessage: Message = orchestratorReply(db, u, c.sessionId, content);
      msgs.push(userMessage, assistantMessage);
      c.updatedAt = now();
      return done({ userMessage, assistantMessage });
    }

    /* v0.4.0 : mandats confirmés (Lambda API, sans LLM) et runs (Lambda agents). */
    const ana = (db.analyses[c.sessionId] ??= { mandates: [], runs: {} });
    if (seg[2] === "mandates") {
      if (seg.length === 3 && m === "GET") return { items: [...ana.mandates].sort((a, b) => b.version - a.version) };
      if (seg.length === 3 && m === "POST") {
        const req = o.body as MandateCreateRequest;
        validateMandate(req, portfolios);
        const prev = ana.mandates[ana.mandates.length - 1];
        const version = prev ? prev.version + 1 : 1;
        const riskProfile = Math.min(req.riskTolerance, req.riskCapacity); // R1
        const effectiveMaxLossPct = req.maxAcceptableLossPct ?? (req.horizonYears < 3 ? 10 : req.horizonYears <= 8 ? 20 : 35);
        const warnings: string[] = [];
        if (riskProfile < (req.riskTolerance ?? 0) && req.riskCapacity < req.riskTolerance)
          warnings.push("[démo] Risk capacity is lower than risk tolerance: the retained profile follows the capacity (R1).");
        const mandate: Mandate = {
          sessionId: c.sessionId, version, mandate: req, riskProfile, effectiveMaxLossPct,
          warnings: warnings.length ? warnings : undefined, confirmedAt: now(),
          changedFields: prev ? changedFields(prev.mandate, req) : undefined,
        };
        ana.mandates.push(mandate);
        return done(mandate);
      }
    }
    if (seg[2] === "runs") {
      if (seg.length === 3 && m === "POST") {
        const version = Number(o.body?.mandateVersion);
        const mandate = ana.mandates.find((x) => x.version === version)
          ?? (() => { throw new ApiError("MANDATE_NOT_FOUND", `Version ${version || "?"} introuvable dans cette session.`, 404); })();
        const runId = id("r");
        const run = buildRun(db, u, c.sessionId, mandate, runId);
        ana.runs[runId] = run;
        return done(run);
      }
      if (seg.length === 4 && m === "GET") {
        const run = ana.runs[seg[3]] ?? (() => { throw new ApiError("RUN_NOT_FOUND", "", 404); })();
        // Affichage progressif : le run complet arrive ~4 s après sa création.
        if (run.status === "partial" && Date.now() - new Date(run.createdAt).getTime() > 4000) {
          const full = completeRun(run);
          ana.runs[run.runId] = full;
          return done(full);
        }
        return run;
      }
    }
  }

  if (seg[0] === "agents" && m === "GET") {
    const r: AgentsRegistry = {
      agents: [
        { id: "agent-orchestrator", name: "Orchestrateur (démo)", role: "Cadrage de l'intention en un mandat, suivi sur le registre", allowedTools: ["portfolio.summary", "market.search"], delegatesTo: ["agent-rules", "agent-narrative"] },
        { id: "agent-rules", name: "Contrôles de règles (démo)", role: "Vérification R1 à R10 sur les scénarios", allowedTools: ["rules.evaluate"] },
        { id: "agent-auditor", name: "Auditeur (démo)", role: "Citations réglementaires depuis la Knowledge Base", allowedTools: ["kb.search"] },
        { id: "agent-narrative", name: "Rédacteur (démo)", role: "Explication en 4 rubriques avec emplacements de preuves", allowedTools: ["registry.get"] },
      ],
      modules: [
        { id: "module-engine", name: "Moteur de simulation (démo)", role: "Scénarios 0/1/2 et mesures à partir du portefeuille et du mandat" },
        { id: "module-verifier", name: "Vérificateur (démo)", role: "Contrôle des emplacements, des chiffres masqués et des formules interdites" },
      ],
      tools: [
        { id: "portfolio.summary", description: "Résumé calculé du portefeuille (prix fictifs)", reads: ["portfolios"] },
        { id: "market.search", description: "Recherche dans l'univers d'actifs", reads: ["assets"] },
        { id: "rules.evaluate", description: "Verdicts des règles R1-R10 (simulés en démo)", reads: ["scenarios"] },
        { id: "kb.search", description: "Knowledge Base réglementaire canadienne (extraits simulés en démo)", reads: ["for_KB"] },
        { id: "registry.get", description: "Registre de preuves d'un run", reads: ["runs"] },
      ],
    };
    return r;
  }

  throw new ApiError("VALIDATION_ERROR", `Route non simulée en mode démo : ${m} /v1${path}`, 400);
}
