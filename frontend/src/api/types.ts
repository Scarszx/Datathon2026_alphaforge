/* Types du contrat d'API AlphaForge v0.4.0 (section data_schemas). Toute modification passe par l'équipe. */

export type Currency = "CAD" | "USD";
export type RiskLevel = "low" | "low_moderate" | "moderate" | "high";

export type ErrorCode =
  | "UNAUTHORIZED" | "FORBIDDEN" | "VALIDATION_ERROR" | "CONVERSATION_NOT_FOUND"
  | "PORTFOLIO_NOT_FOUND" | "ASSET_NOT_FOUND" | "MANDATE_NOT_FOUND" | "RUN_NOT_FOUND"
  | "MANDATE_NOT_CONFIRMED" | "GUARDRAIL_BLOCKED" | "AGENT_TIMEOUT" | "INTERNAL"
  | "NETWORK"; // NETWORK : côté client seulement (aucune réponse du serveur)

export type Jurisdiction =
  | "CA" | "QC" | "ON" | "BC" | "AB" | "SK" | "MB" | "NB" | "NS" | "PE" | "NL" | "YT" | "NT" | "NU";

export type InvestorProfile = {
  riskLevel: RiskLevel;
  /* v0.4.0 : tolérance et capacité de perte séparées (1 à 5), et province (règle R1, avis 31-368) */
  riskTolerance?: number;
  riskCapacity?: number;
  province?: Jurisdiction;
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

export type Conversation = {
  sessionId: string;
  title?: string;
  userLanguage?: string; // ISO 639-1, détecté par agent-orchestrator
  createdAt: string;
  updatedAt: string;
};
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
  /* v0.4.0 : cadrage de l'orchestrateur */
  quickReplies?: string[];
  mandateDraft?: MandateCreateRequest;
  runId?: string;
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
export type ModuleInfo = { id: string; name: string; role: string };
export type ToolInfo = { id: string; description: string; reads?: string[] };
export type AgentsRegistry = { agents: AgentInfo[]; modules?: ModuleInfo[]; tools: ToolInfo[] };

/* ===== v0.4.0 : mandats et runs (Analyses) ===== */

export type MandateMode = "add_asset" | "rebalance" | "diagnose";
export type MandateObjective = "growth" | "income" | "preservation" | "project" | "retirement";
export type MandateOperation = {
  action: "add" | "remove" | "set_weight";
  ticker: string;
  amount?: number;
  weight?: number;
  currency?: Currency;
};

/* schema-mandate-create-request : proposé par l'orchestrateur ou édité par les curseurs, confirmé par POST mandates */
export type MandateCreateRequest = {
  portfolioId: string;
  mode: MandateMode;
  objective: MandateObjective;
  objectiveDetail?: string;
  horizonYears: number;
  riskTolerance: number; // 1 à 5
  riskCapacity: number; // 1 à 5
  maxAcceptableLossPct?: number; // absent = défaut par horizon (hypothèse d'équipe)
  constraints?: string[];
  preferences?: { esg?: boolean; excludedSectors?: string[]; excludedAssetClasses?: string[] };
  province: Jurisdiction;
  userLanguage: string; // ISO 639-1 ; tous les champs texte du mandat sont en anglais
  operations?: MandateOperation[];
  subjectTicker?: string;
  fieldSources?: Record<string, "persona" | "user_answer" | "team_assumption" | "slider">;
};

/* schema-mandate-warning (contrat 0.4.1). Les mandats enregistrés avant 0.4.1 portent des chaînes : accepter les deux. */
export type MandateWarning = { code: string; message: string; params?: Record<string, string | number> };

/* schema-mandate : réponse de POST/GET mandates */
export type Mandate = {
  sessionId: string;
  version: number;
  mandate: MandateCreateRequest;
  riskProfile: number; // = min(riskTolerance, riskCapacity) (R1)
  effectiveMaxLossPct: number;
  warnings?: (MandateWarning | string)[];
  changedFields?: string[];
  confirmedAt: string;
};

/* schema-evidence : seule source des chiffres et citations affichés (EV-nn / KB-nn) */
export type Evidence = {
  id: string; // EV-nn ou KB-nn
  kind: "metric" | "etf_fact" | "regulation" | "assumption";
  label: string;
  value?: number;
  formatted?: string;
  scenario?: number;
  method?: string;
  window?: string;
  currency?: string;
  source: string;
  asOf?: string;
  document?: string;
  section?: string;
  excerpt?: string;
  jurisdiction?: string;
  url?: string;
  caveats?: string[];
};

/* schema-scenario : 0 actuel, 1 idée telle quelle, 2 alternative */
export type Scenario = {
  index: 0 | 1 | 2;
  label: string;
  description?: string;
  proxyNote?: string;
  allocation?: Slice[];
  metrics?: Record<string, string>; // mesure -> identifiant EV-nn
  verdict: "pass" | "warn" | "fail";
};

/* schema-rule-verdict : R1..R10 */
export type RuleVerdict = {
  rule: string;
  scenario?: number;
  status: "pass" | "warn" | "fail" | "not_verified";
  reasonCode: string;
  evidence?: string[]; // EV-nn
  citations?: string[]; // KB-nn, rempli par agent-auditor
  threshold?: { value: number; nature: "text" | "team_assumption" };
  messageEn?: string;
  message?: string; // traduit dans userLanguage par agent-orchestrator
};

/* schema-narrative : 4 sections, emplacements {EV-nn}/{KB-nn} seulement, aucun chiffre écrit à la main */
export type NarrativeSectionKey = "data_used" | "why" | "limits" | "what_would_change";
export type NarrativeSection = { key: NarrativeSectionKey; textEn: string; text: string };
export type Narrative = {
  sections: NarrativeSection[];
  language: string;
  hiddenSentences?: { section: string; reason: string }[];
};

/* schema-verifier-report : score du vérificateur (module-verifier) */
export type VerifierReport = {
  placeholdersResolved: number;
  placeholdersTotal: number;
  handwrittenNumbers: number;
  forbiddenPhrases: number;
  placeholdersMatch: boolean;
};

/* schema-run : réponse de POST runs (status = partial) puis GET runs/{runId} (partial | done | error) */
export type RunStatus = "partial" | "done" | "error";
export type Run = {
  runId: string;
  sessionId: string;
  mandateVersion: number;
  status: RunStatus;
  datasetVersion: string;
  userLanguage: string;
  scenarios: Scenario[];
  verdicts: RuleVerdict[];
  evidence: Evidence[];
  narrative?: Narrative;
  verifier?: VerifierReport;
  jurisdictionNotices?: string[];
  explanation?: Explanation;
  createdAt: string;
  completedAt?: string;
};

export type RunCreateRequest = { mandateVersion: number };
