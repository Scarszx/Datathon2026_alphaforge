/* Questionnaire de profil de risque : chaque réponse vaut de 1 à 5 points (score total : 5 à 25).
 * v0.4.6 : UNE SEULE échelle de risque 1 à 5 — la tolérance (ce que la personne accepte de subir) vient
 * de la question « Perte maximale acceptable », la capacité (ce qu'elle peut encaisser) de la question
 * « Capacité financière ». Le niveau retenu (R1, avis 31-368) est le plus bas des deux, partout :
 * accueil, profil, mandat, R1, catégorie de comparaison. L'ancienne échelle à quatre libellés
 * (riskLevel) n'est plus envoyée à l'API. La description des niveaux est dans lib/riskScale.ts. */
import { EMPTY_INDUSTRIES, industryPrefs, type IndustryChoice } from "./industries";
import type { InvestorProfile, Jurisdiction } from "../api/types";

export type Question = { id: string; label: string; options: string[] }; // options[i] vaut i + 1 point

export const QUESTIONS: Question[] = [
  { id: "horizon", label: "Horizon d'investissement",
    options: ["Moins de 2 ans", "2 à 5 ans", "5 à 10 ans", "10 à 20 ans", "Plus de 20 ans"] },
  { id: "maxLoss", label: "Perte maximale acceptable sur un an",
    options: ["5 %", "10 %", "20 %", "30 %", "40 % ou plus"] },
  { id: "reaction", label: "Si votre portefeuille perd 20 %, que faites-vous ?",
    options: ["Je vends tout", "Je vends une partie", "J'attends sans rien changer", "Je conserve et je rééquilibre", "J'investis davantage"] },
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

export type PortfolioRisk = { score: number; answers: Record<string, number>; province?: Jurisdiction; computedAt: string };

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
  const result: PortfolioRisk = { score: totalScore(answers), answers, ...(province ? { province } : {}), computedAt: new Date().toISOString() };
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

/** Horizon (index de réponse) → [min, max] en années; max null = sans borne. */
const HORIZONS: [number, number | null][] = [[0, 2], [2, 5], [5, 10], [10, 20], [20, null]];

export function isComplete(answers: Record<string, number>) {
  return QUESTIONS.every((q) => answers[q.id] !== undefined);
}

/**
 * Profil investisseur déduit du questionnaire (contraintes, préférences et exclusions laissées vides).
 * v0.4.6 : tolérance (1 à 5, question « Perte maximale ») et capacité (1 à 5, question « Capacité
 * financière ») obligatoires et envoyées telles quelles ; riskLevel n'est plus envoyé (R1 : le niveau
 * retenu est calculé côté API comme le plus bas des deux).
 */
export function profileFromAnswers(answers: Record<string, number>, province?: Jurisdiction, industries: IndustryChoice = EMPTY_INDUSTRIES): InvestorProfile {
  const [min, max] = HORIZONS[answers.horizon];
  const goal = QUESTIONS.find((q) => q.id === "goal")!.options[answers.goal];
  return {
    riskTolerance: answers.maxLoss + 1,
    riskCapacity: answers.capacity + 1,
    ...(province ? { province } : {}),
    horizonMinYears: min,
    ...(max !== null ? { horizonMaxYears: max } : {}),
    objective: goal,
    constraints: [], preferences: industryPrefs(industries), excludedAssetClasses: [],
  };
}
