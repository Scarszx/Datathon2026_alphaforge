/* Questionnaire de profil de risque : chaque réponse vaut de 1 à 5 points (score total : 5 à 25). */

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

/** Score total : somme des points (1 à 5) de chaque réponse. `answers` = index d'option (0 à 4) par question. */
export function totalScore(answers: Record<string, number>): number {
  return QUESTIONS.reduce((sum, q) => sum + answers[q.id] + 1, 0);
}

/** Premier calcul : 10 - 9 x ((score - 5) / 20). Donne 10 pour un score de 5 et 1 pour un score de 25. */
export function riskCalc(score: number): number {
  return 10 - 9 * ((score - SCORE_MIN) / (SCORE_MAX - SCORE_MIN));
}

export type PortfolioRisk = { score: number; value: number; answers: Record<string, number>; computedAt: string };

const key = (userId: string) => `af.risk.${userId}`;

/** Résultats stockés par portefeuille pour un utilisateur : { [portfolioId]: PortfolioRisk }. */
export function loadRisk(userId: string): Record<string, PortfolioRisk> {
  try {
    const v = JSON.parse(localStorage.getItem(key(userId)) ?? "{}");
    return v && typeof v === "object" && !Array.isArray(v) ? v : {};
  } catch { return {}; }
}

export function saveRisk(userId: string, portfolioIds: string[], answers: Record<string, number>): PortfolioRisk {
  const score = totalScore(answers);
  const result: PortfolioRisk = { score, value: riskCalc(score), answers, computedAt: new Date().toISOString() };
  const all = loadRisk(userId);
  for (const id of portfolioIds) all[id] = result;
  localStorage.setItem(key(userId), JSON.stringify(all));
  return result;
}
