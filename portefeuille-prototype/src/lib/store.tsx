import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ask } from "../agent/agent";
import { initialPrices, jitter } from "./market";
import { computeProfile } from "./profile";
import { cancelOrder as cancel, evaluatePending, placeOrder as place } from "./trading";
import type { Answers, Conversation, Message, OrderInput, Prices, User, UserData } from "./types";

/*
 * Stockage LOCAL (localStorage) — remplace temporairement la base de données et l'API.
 * Les mots de passe sont salés + hachés (SHA-256) : suffisant pour un prototype, pas pour la production
 * (utiliser bcrypt/argon2 côté serveur, puis Cognito sur AWS).
 */

type DB = { users: User[]; data: Record<string, UserData>; session: string | null };
const KEY = "portefeuille.proto.v1";
const uid = (p: string) => `${p}${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
const day = 86400000;

async function sha256(s: string) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

const DEMO_ANSWERS: Answers = { objective: "Retraite", horizon: "Plus de 10 ans", reaction: "Vendre une partie", experience: "Intermédiaire", risk: "Modéré", goal: "Équilibrer", capital: "50 000 $ à 100 000 $", contributions: "Mensuelles", liquidity: "Faible" };

function seed(): DB {
  const h = (id: string, symbol: string, name: string, account: any, category: any, sector: string, quantity: number, avgCost: number) => ({ id, symbol, name, account, category, sector, quantity, avgCost });
  const now = Date.now();
  const data: UserData = {
    profile: computeProfile(DEMO_ANSWERS),
    cash: 6420,
    holdings: [
      h("d1", "XEQT.TO", "iShares Core Equity ETF Portfolio", "CELI", "Fonds et FNB", "Diversifié", 650, 31.2),
      h("d2", "NA.TO", "National Bank of Canada", "REER", "Actions", "Finance", 100, 128.5),
      h("d3", "ZAG.TO", "BMO Aggregate Bond Index ETF", "REER", "Revenu fixe", "Obligations", 1300, 14.6),
      h("d4", "ENB.TO", "Enbridge Inc.", "Non enregistré", "Actions", "Énergie", 220, 52.1),
      h("d5", "SHOP.TO", "Shopify Inc.", "CELI", "Actions", "Technologie", 50, 118),
      h("d6", "AAPL", "Apple Inc.", "Non enregistré", "Actions", "Technologie", 25, 165),
    ],
    transactions: [
      { id: "t1", date: now - 6 * day, symbol: "SHOP.TO", side: "buy", quantity: 10, price: 141.5, currency: "CAD", totalCad: 1415, account: "CELI" },
      { id: "t2", date: now - 21 * day, symbol: "ENB.TO", side: "buy", quantity: 40, price: 54.2, currency: "CAD", totalCad: 2168, account: "Non enregistré" },
      { id: "t3", date: now - 48 * day, symbol: "AAPL", side: "sell", quantity: 5, price: 221.3, currency: "USD", totalCad: 1516.04, account: "Non enregistré" },
    ],
    orders: [],
    watchlist: ["MSFT", "RY.TO", "VFV.TO"],
    conversations: [
      {
        id: "c1", title: "Bienvenue", updatedAt: now - 2 * day,
        messages: [
          { id: "m1", role: "user", content: "Qu'est-ce qu'un FNB ?", createdAt: now - 2 * day },
          { id: "m2", role: "assistant", content: "Un FNB (fonds négocié en bourse) est un panier de titres qui s'achète et se vend en bourse comme une action, généralement à faibles frais.\n\n_Analyse éducative fondée sur des données simulées (prix fictifs, non en temps réel). Ce n'est pas un conseil financier._", tools: ["explain_financial_concept"], createdAt: now - 2 * day },
        ],
      },
    ],
  };
  return {
    users: [{ id: "u-demo", firstName: "Camille", lastName: "Démo", email: "demo@example.com", username: "demo", age: 34, salt: "demo-salt", passwordHash: "04c88dccabe1af11dec1c135d49914ba6995bad0986964b43e09f410198a7615" }],
    data: { "u-demo": data },
    session: null,
  };
}

function load(): DB {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as DB;
  } catch {}
  return seed();
}

type Result = { ok: true } | { ok: false; error: string };
type RegisterFields = { firstName: string; lastName: string; email: string; username: string; password: string; age: number };

type Ctx = {
  user: User | null;
  data: UserData | null;
  prices: Prices;
  updatedAt: number;
  thinking: string | null;
  login(id: string, pw: string): Promise<Result>;
  register(f: RegisterFields, answers: Answers): Promise<Result>;
  logout(): void;
  refreshPrices(): void;
  placeOrder(i: OrderInput): { ok: boolean; message: string; status?: string };
  cancelOrder(id: string): void;
  addWatch(s: string): void;
  removeWatch(s: string): void;
  saveProfile(a: Answers): void;
  newConversation(): string;
  deleteConversation(id: string): void;
  sendMessage(convId: string | null, text: string): Promise<string>;
  resetDemo(): void;
};

const C = createContext<Ctx>(null as never);
export const useApp = () => useContext(C);

export function AppProvider({ children }: { children: ReactNode }) {
  const [db, setDb] = useState<DB>(load);
  const [prices, setPrices] = useState<Prices>(initialPrices);
  const [updatedAt, setUpdatedAt] = useState(Date.now());
  const [thinking, setThinking] = useState<string | null>(null);

  const user = db.users.find((u) => u.id === db.session) ?? null;
  const data = user ? db.data[user.id] ?? null : null;
  const ref = useRef({ data, prices, user });
  ref.current = { data, prices, user };

  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch {} }, [db]);

  const update = useCallback((fn: (d: UserData) => UserData) => {
    setDb((s) => (s.session && s.data[s.session] ? { ...s, data: { ...s.data, [s.session]: fn(s.data[s.session]) } } : s));
  }, []);

  const refreshPrices = useCallback(() => {
    const next = jitter(ref.current.prices);
    setPrices(next);
    setUpdatedAt(Date.now());
    update((d) => evaluatePending(d, next));
  }, [update]);

  useEffect(() => {
    const id = setInterval(refreshPrices, 30_000);
    return () => clearInterval(id);
  }, [refreshPrices]);

  const value = useMemo<Ctx>(() => ({
    user, data, prices, updatedAt, thinking,

    async login(identifier, pw) {
      const id = identifier.trim().toLowerCase();
      const u = db.users.find((x) => x.email.toLowerCase() === id || x.username.toLowerCase() === id);
      if (!u || (await sha256(`${u.salt}:${pw}`)) !== u.passwordHash) return { ok: false, error: "Identifiants invalides." };
      setDb((s) => ({ ...s, session: u.id }));
      return { ok: true };
    },

    async register(f, answers) {
      const email = f.email.trim().toLowerCase(), username = f.username.trim().toLowerCase();
      if (db.users.some((u) => u.email.toLowerCase() === email)) return { ok: false, error: "Ce courriel est déjà utilisé." };
      if (db.users.some((u) => u.username.toLowerCase() === username)) return { ok: false, error: "Ce nom d'utilisateur est déjà pris." };
      const salt = uid("s");
      const u: User = { id: uid("u"), firstName: f.firstName.trim(), lastName: f.lastName.trim(), email, username, age: f.age, salt, passwordHash: await sha256(`${salt}:${f.password}`) };
      const d: UserData = { profile: computeProfile(answers), cash: 10000, holdings: [], transactions: [], orders: [], watchlist: ["MSFT", "RY.TO", "VFV.TO"], conversations: [] };
      setDb((s) => ({ users: [...s.users, u], data: { ...s.data, [u.id]: d }, session: u.id }));
      return { ok: true };
    },

    logout: () => setDb((s) => ({ ...s, session: null })),
    refreshPrices,

    placeOrder(i) {
      const cur = ref.current;
      if (!cur.data) return { ok: false, message: "Session expirée." };
      const r = place(cur.data, cur.prices, i);
      if (r.errors.length || !r.order) return { ok: false, message: r.errors[0] ?? "Ordre refusé." };
      update(() => r.data);
      const o = r.order;
      return { ok: true, status: o.status, message: o.status === "filled" ? `Ordre simulé exécuté : ${o.side === "buy" ? "achat" : "vente"} de ${o.quantity} ${o.symbol}.` : "Ordre à cours limité enregistré : en attente que le prix atteigne votre limite." };
    },
    cancelOrder: (id) => update((d) => cancel(d, id)),
    addWatch: (s) => update((d) => (d.watchlist.includes(s) ? d : { ...d, watchlist: [...d.watchlist, s] })),
    removeWatch: (s) => update((d) => ({ ...d, watchlist: d.watchlist.filter((x) => x !== s) })),
    saveProfile: (a) => update((d) => ({ ...d, profile: computeProfile(a) })),

    newConversation() {
      const id = uid("c");
      update((d) => ({ ...d, conversations: [{ id, title: "Nouvelle conversation", updatedAt: Date.now(), messages: [] }, ...d.conversations] }));
      return id;
    },
    deleteConversation: (id) => update((d) => ({ ...d, conversations: d.conversations.filter((c) => c.id !== id) })),

    async sendMessage(convId, text) {
      const id = convId ?? uid("c");
      const um: Message = { id: uid("m"), role: "user", content: text, createdAt: Date.now() };
      update((d) => {
        const ex = d.conversations.find((c) => c.id === id);
        const conv: Conversation = ex
          ? { ...ex, title: ex.messages.length ? ex.title : text.slice(0, 40), updatedAt: um.createdAt, messages: [...ex.messages, um] }
          : { id, title: text.slice(0, 40), updatedAt: um.createdAt, messages: [um] };
        return { ...d, conversations: [conv, ...d.conversations.filter((c) => c.id !== id)] };
      });
      setThinking(id);
      await new Promise((r) => setTimeout(r, 700));
      const cur = ref.current;
      let reply: { content: string; tools: string[] };
      try {
        reply = cur.data ? ask(text, { data: cur.data, prices: cur.prices }) : { content: "Session expirée.", tools: [] };
      } catch {
        reply = { content: "Une erreur est survenue pendant l'analyse. Réessayez.", tools: [] };
      }
      const am: Message = { id: uid("m"), role: "assistant", content: reply.content, tools: reply.tools, createdAt: Date.now() };
      update((d) => ({ ...d, conversations: d.conversations.map((c) => (c.id === id ? { ...c, updatedAt: am.createdAt, messages: [...c.messages, am] } : c)) }));
      setThinking(null);
      return id;
    },

    resetDemo() {
      localStorage.removeItem(KEY);
      setDb(seed());
    },
  }), [db, user, data, prices, updatedAt, thinking, refreshPrices, update]);

  return <C.Provider value={value}>{children}</C.Provider>;
}
