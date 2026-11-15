export type Category = "Actions" | "Revenu fixe" | "Fonds et FNB";
export const ACCOUNTS = ["CELI", "REER", "CELIAPP", "REEE", "Non enregistré"] as const;
export type Account = (typeof ACCOUNTS)[number];

export type User = {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  username: string;
  age: number;
  salt: string;
  passwordHash: string;
};

export type Answers = Record<string, string>;
export type RiskLabel = "Conservateur" | "Modéré" | "Dynamique";

export type FinancialProfile = {
  answers: Answers;
  score: number; // 0-100
  label: RiskLabel;
  objective: string;
  horizon: string;
  experience: string;
  summary: string;
  updatedAt: number;
};

export type Holding = {
  id: string;
  symbol: string;
  name: string;
  account: Account;
  category: Category;
  sector: string;
  quantity: number;
  /** Prix moyen payé, dans la devise du titre */
  avgCost: number;
};

export type Transaction = {
  id: string;
  date: number;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  currency: "CAD" | "USD";
  totalCad: number;
  account: Account;
};

export type OrderInput = {
  side: "buy" | "sell";
  symbol: string;
  holdingId?: string;
  account: Account;
  type: "market" | "limit";
  quantity: number;
  limitPrice?: number;
};

export type Order = OrderInput & {
  id: string;
  date: number;
  name: string;
  status: "pending" | "filled" | "cancelled" | "rejected";
  fillPrice?: number;
  note?: string;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  tools?: string[];
  createdAt: number;
};

export type Conversation = { id: string; title: string; updatedAt: number; messages: Message[] };

export type UserData = {
  profile: FinancialProfile;
  cash: number;
  holdings: Holding[];
  transactions: Transaction[];
  orders: Order[];
  watchlist: string[];
  conversations: Conversation[];
};

export type Prices = Record<string, number>;
