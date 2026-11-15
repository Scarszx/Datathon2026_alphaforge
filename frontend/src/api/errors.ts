import type { ErrorCode } from "./types";

/** Erreur au format schema-error : { error: { code, message, requestId } } */
export class ApiError extends Error {
  constructor(public code: ErrorCode, message: string, public status: number, public requestId?: string) {
    super(message);
  }
}

const LABELS: Partial<Record<ErrorCode, string>> = {
  UNAUTHORIZED: "Votre session a expiré. Reconnectez-vous.",
  FORBIDDEN: "Accès refusé.",
  CONVERSATION_NOT_FOUND: "Conversation introuvable.",
  PORTFOLIO_NOT_FOUND: "Portefeuille introuvable.",
  ASSET_NOT_FOUND: "Un des tickers n'existe pas dans l'univers d'actifs.",
  MANDATE_NOT_FOUND: "Mandat introuvable.",
  RUN_NOT_FOUND: "Analyse introuvable.",
  MANDATE_NOT_CONFIRMED: "Le mandat doit d'abord être confirmé avant de lancer l'analyse.",
  GUARDRAIL_BLOCKED: "Cette demande ne peut pas être traitée (simulation seulement : aucune transaction, aucune promesse de rendement, aucun conseil personnalisé).",
  AGENT_TIMEOUT: "Les agents ont mis trop de temps à répondre. Réessayez.",
  NETWORK: "Le serveur est injoignable. Vérifiez votre connexion.",
};

/** Message affichable : celui du serveur s'il existe, sinon un libellé par code. */
export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    const base = e.message || LABELS[e.code] || "Une erreur est survenue.";
    return e.requestId ? `${base} (réf. ${e.requestId})` : base;
  }
  return "Une erreur est survenue.";
}
