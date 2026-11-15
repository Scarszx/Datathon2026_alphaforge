/* Une fonction par route du contrat (section apis). Le front ne calcule rien : il affiche ce que ces routes renvoient. */
import { request } from "./client";
import type {
  AgentsRegistry, Asset, Conversation, Holding, InvestorProfile, Message, MessageCreateResponse,
  Page, Portfolio, PortfolioSummary, SummaryRange, User,
} from "./types";

const enc = encodeURIComponent;

export const getMe = () => request<User>("/me");
export const putProfile = (profile: InvestorProfile) => request<User>("/me/profile", { method: "PUT", body: profile });

export const listConversations = (cursor?: string, limit = 20) =>
  request<Page<Conversation>>("/conversations", { query: { limit, cursor } });
export const createConversation = (title?: string) =>
  request<Conversation>("/conversations", { method: "POST", body: title ? { title } : {} });
export const renameConversation = (sessionId: string, title: string) =>
  request<Conversation>(`/conversations/${enc(sessionId)}`, { method: "PATCH", body: { title } });
export const deleteConversation = (sessionId: string) =>
  request<void>(`/conversations/${enc(sessionId)}`, { method: "DELETE" });

export const listMessages = (sessionId: string, cursor?: string, limit = 50) =>
  request<Page<Message>>(`/conversations/${enc(sessionId)}/messages`, { query: { limit, cursor } });
export const sendMessage = (sessionId: string, content: string) =>
  request<MessageCreateResponse>(`/conversations/${enc(sessionId)}/messages`, { method: "POST", body: { content } });

export const listPortfolios = () => request<{ items: Portfolio[] }>("/portfolios");
export const putHoldings = (portfolioId: string, holdings: Holding[]) =>
  request<Portfolio>(`/portfolios/${enc(portfolioId)}/holdings`, { method: "PUT", body: { holdings } });
export const getSummary = (portfolioId: string, range: SummaryRange) =>
  request<PortfolioSummary>(`/portfolios/${enc(portfolioId)}/summary`, { query: { range } });

export const searchAssets = (q: string, assetClass?: string, signal?: AbortSignal) =>
  request<{ items: Asset[] }>("/market/search", { query: { q, assetClass }, signal });

export const getAgentsRegistry = () => request<AgentsRegistry>("/agents");
