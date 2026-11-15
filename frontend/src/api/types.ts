/* Types du contrat d'API AlphaForge v0.3.0 (section data_schemas). Toute modification passe par l'équipe. */

export type Currency = "CAD" | "USD";
export type RiskLevel = "low" | "low_moderate" | "moderate" | "high";

export type ErrorCode =
  | "UNAUTHORIZED" | "FORBIDDEN" | "VALIDATION_ERROR" | "CONVERSATION_NOT_FOUND"
  | "PORTFOLIO_NOT_FOUND" | "ASSET_NOT_FOUND" | "AGENT_TIMEOUT" | "INTERNAL"
  | "NETWORK"; // NETWORK : côté client seulement (aucune réponse du serveur)

export type InvestorProfile = {
  riskLevel: RiskLevel;
  horizonMinYears: number;
  horizonMaxYears?: number | null;
  objective: string;
  constraints?: string[];
  preferences?: string[];
  excludedAssetClasses?: string[];
};

export type User = {
  userId: string;
  username: string;
  displayName?: string;
  baseCurrency?: Currency;
  investorProfile: InvestorProfile | null;
};

export type Conversation = { sessionId: string; title?: string; createdAt: string; updatedAt: string };
export type Page<T> = { items: T[]; nextCursor?: string | null };

export type ExplanationSource = { id: string; dataset?: string; asOf?: string; note?: string };
export type ExplanationStep = {
  agentId: string; tool: string; params?: Record<string, unknown>;
  status: "ok" | "error" | "empty"; durationMs?: number;
};
export type ExplanationCheck = {
  agentId: string; rule: string; status: "pass" | "warn" | "fail" | "not_verified"; message: string;
};
export type Explanation = {
  sources: ExplanationSource[];
  assumptions?: string[];
  limitations?: string[];
  steps: ExplanationStep[];
  checks?: ExplanationCheck[];
};

export type Message = {
  messageId: string;
  sessionId: string;
  role: "user" | "assistant";
  content: string;
  status: "done" | "pending" | "error";
  createdAt: string;
  explanation?: Explanation;
};
export type MessageCreateResponse = { userMessage: Message; assistantMessage: Message };

export type Holding = { ticker: string; quantity: number; avgCost: number };
export type Portfolio = { portfolioId: string; name: string; baseCurrency: Currency; holdings: Holding[]; updatedAt: string };

export type SummaryRange = "1m" | "6m" | "1y" | "5y";
export type Slice = { label: string; weight: number };
export type SummaryHolding = {
  ticker: string; name: string; assetClass: string; quantity: number; avgCost: number; currency: string;
  price: number; value: number; weight: number; pnl: number; pnlPct: number; dayChangePct: number;
  sector?: string; stale?: boolean;
};
export type PortfolioSummary = {
  portfolioId: string;
  baseCurrency: Currency;
  asOf: string;
  totals: { value: number; cost: number; pnl: number; pnlPct: number; dayChange: number; dayChangePct: number };
  holdings: SummaryHolding[];
  allocation: { byAssetClass: Slice[]; bySector: Slice[]; byCurrency: Slice[] };
  performance: { range: SummaryRange; points: { date: string; value: number }[] };
  risk: { volatility: number; maxDrawdown: number };
  warnings?: string[];
  explanation?: Explanation;
};

export type Asset = { ticker: string; name: string; assetClass: string; market?: string; currency?: string; sector?: string };

export type AgentInfo = { id: string; name: string; role: string; allowedTools: string[]; delegatesTo?: string[]; limits?: Record<string, number> };
export type ToolInfo = { id: string; description: string; reads?: string[] };
export type AgentsRegistry = { agents: AgentInfo[]; tools: ToolInfo[] };
