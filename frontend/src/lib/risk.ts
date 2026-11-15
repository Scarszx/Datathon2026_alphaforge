/* Questionnaire de profil de risque : chaque réponse vaut de 1 à 5 points (score total : 5 à 25).
 * v0.4.0 : tolérance et capacité de perte séparées (règle R1, avis 31-368), et province pour la Knowledge Base et les mentions R9. */
import { industryPrefs } from "./industries";
import type { InvestorProfile, Jurisdiction, RiskLevel } from "../api/types";

export type Question = { id: string; label: string; options: string[] }; // options[i] vaut i + 1 point

export const QUESTIONS: Question[] = [
  { id: "horizon", label: "Horizon d'investissement",
    options: ["Moins de 2 ans", "2 à 5 ans", "5 à 10 ans", "10 à 20 ans", "Plus de 20 ans"] },
  { id: "maxLoss", label: "Perte maximale acceptable sur un an",
    options: ["5 %", "10 %", "20 %", "30 %", "40 % ou plus"] },
  { id: "reaction", label: "Si ton portefeuille perd 20 %, que fais-tu ?",
    options: ["Je vends tout", "Je vends une partie", "J'attends sans rien changer", "Je conserve et rééquilibre", "J'investis davantage"] },
  { id: "goal", label: "Objectif financier principal",
    options: ["Préserver mon capital", "Obtenir un revenu stable", "Croissance modérée", "Croissance à long terme", "Maximiser la croissance"] },
  { id: "capacity", label: "Capacité financière à absorber une perte",
    options: [
      "Très faible : mes dépenses essentielles seraient touchées",
      "Faible : je devrais modifier mes projets",
      "Moyenne : je pourrais absorber une perte limitée",
      "Élevée : peu d'impact sur mes projets",
      "Très élevée : aucun impact significatif sur mes finances",
    ] },
];

export const SCORE_MIN = QUESTIONS.length;     // 5
export const SCORE_MAX = QUESTIONS.length * 5; // 25

/* Provinces reconnues par le contrat (conventions.jurisdictions), sans CA (textes nationaux, pas une province). */
export const PROVINCES: { code: Jurisdiction; label: string }[] = [
  { code: "QC", label: "Québec" }, { code: "ON", label: "Ontario" }, { code: "BC", label: "Colombie-Britannique" },
  { code: "AB", label: "Alberta" }, { code: "SK", label: "Saskatchewan" }, { code: "MB", label: "Manitoba" },
  { code: "NB", label: "Nouveau-Brunswick" }, { code: "NS", label: "Nouvelle-Écosse" },
  { code: "PE", label: "Île-du-Prince-Édouard" }, { code: "NL", label: "Terre-Neuve-et-Labrador" },
  { code: "YT", label: "Yukon" }, { code: "NT", label: "Territoires du Nord-Ouest" }, { code: "NU", label: "Nunavut" },
];

export const PROVINCE_LABELS: Record<Jurisdiction, string> =
  Object.fromEntries(PROVINCES.map((p) => [p.code, p.label])) as Record<Jurisdiction, string>;

/** Score total : somme des points (1 à 5) de chaque réponse. `answers` = index d'option (0 à 4) par question. */
export function totalScore(answers: Record<string, number>): number {
  return QUESTIONS.reduce((sum, q) => sum + answers[q.id] + 1, 0);
}

/** Premier calcul : 10 - 9 x ((score - 5) / 20). Donne 10 pour un score de 5 et 1 pour un score de 25. */
export function riskCalc(score: number): number {
  return 10 - 9 * ((score - SCORE_MIN) / (SCORE_MAX - SCORE_MIN));
}

export type PortfolioRisk = { score: number; value: number; answers: Record<string, number>; province?: Jurisdiction; computedAt: string };

const key = (userId: string) => `af.risk.${userId}`;

/** Résultats stockés par portefeuille pour un utilisateur : { [portfolioId]: PortfolioRisk }. */
export function loadRisk(userId: string): Record<string, PortfolioRisk> {
  try {
    const v = JSON.parse(localStorage.getItem(key(userId)) ?? "{}");
    return v && typeof v === "object" && !Array.isArray(v) ? v : {};
  } catch { return {}; }
}

const latestKey = (userId: string) => `af.risk.latest.${userId}`;

/** Dernier résultat de l'utilisateur, consultable sur /profil même sans portefeuille. */
export function loadLatestRisk(userId: string): PortfolioRisk | null {
  try {
    const v = JSON.parse(localStorage.getItem(latestKey(userId)) ?? "null");
    return v && typeof v === "object" && v.answers && isComplete(v.answers) ? v : null;
  } catch { return null; }
}

/** Calcule le résultat, le garde comme dernier résultat et l'enregistre pour chaque portefeuille donné. */
export function saveRisk(userId: string, portfolioIds: string[], answers: Record<string, number>, province?: Jurisdiction): PortfolioRisk {
  const score = totalScore(answers);
  const result: PortfolioRisk = { score, value: riskCalc(score), answers, ...(province ? { province } : {}), computedAt: new Date().toISOString() };
  const all = loadRisk(userId);
  for (const id of portfolioIds) all[id] = result;
  localStorage.setItem(key(userId), JSON.stringify(all));
  localStorage.setItem(latestKey(userId), JSON.stringify(result));
  return result;
}

/** Applique le dernier résultat aux portefeuilles qui n'en ont pas encore (ex. créés après l'inscription). */
export function syncRisk(userId: string, portfolioIds: string[]): Record<string, PortfolioRisk> {
  const all = loadRisk(userId);
  const latest = loadLatestRisk(userId);
  const missing = portfolioIds.filter((id) => !all[id]);
  if (latest && missing.length) {
    for (const id of missing) all[id] = latest;
    localStorage.setItem(key(userId), JSON.stringify(all));
  }
  return all;
}

/* ---- Conversion vers le profil investisseur du contrat (PUT /v1/me/profile) ---- */

/** Score 5–25 → niveau du contrat : 5–9 faible, 10–14 faible à modéré, 15–19 modéré, 20–25 élevé. */
export function riskLevelOf(score: number): RiskLevel {
  return score < 10 ? "low" : score < 15 ? "low_moderate" : score < 20 ? "moderate" : "high";
}

export const RISK_LABELS: Record<RiskLevel, string> = {
  low: "Faible", low_moderate: "Faible à modéré", moderate: "Modéré", high: "Élevé",
};

/** Horizon (index de réponse) → [min, max] en années; max null = sans borne. */
const HORIZONS: [number, number | null][] = [[0, 2], [2, 5], [5, 10], [10, 20], [20, null]];

export function isComplete(answers: Record<string, number>) {
  return QUESTIONS.every((q) => answers[q.id] !== undefined);
}

/**
 * Profil investisseur déduit du questionnaire (contraintes, préférences et exclusions laissées vides).
 * v0.4.0 : tolérance et capacité de perte séparées — la question « Perte maximale acceptable » donne la
 * tolérance (ce que la personne accepte de subir), la question « Capacité financière » la capacité (R1).
 */
export function profileFromAnswers(answers: Record<string, number>, province?: Jurisdiction, industries: string[] = []): InvestorProfile {
  const [min, max] = HORIZONS[answers.horizon];
  const goal = QUESTIONS.find((q) => q.id === "goal")!.options[answers.goal];
  return {
    riskLevel: riskLevelOf(totalScore(answers)),
    riskTolerance: answers.maxLoss + 1,
    riskCapacity: answers.capacity + 1,
    ...(province ? { province } : {}),
    horizonMinYears: min,
    ...(max !== null ? { horizonMaxYears: max } : {}),
    objective: goal,
    constraints: [], preferences: industryPrefs(industries), excludedAssetClasses: [],
  };
}
