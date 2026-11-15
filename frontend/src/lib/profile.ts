import type { Answers, FinancialProfile, RiskLabel } from "./types";

type Option = { value: string; label: string; points: number };
export type Question = { id: string; label: string; options: Option[] };

export const QUESTIONS: Question[] = [
  {
    id: "objective",
    label: "Quel est votre principal objectif financier ?",
    options: [
      { value: "Retraite", label: "Retraite", points: 3 },
      { value: "Croissance à long terme", label: "Accumulation de richesse à long terme", points: 4 },
      { value: "Épargne à court terme", label: "Épargne à court terme", points: 0 },
      { value: "Revenu", label: "Génération de revenus", points: 1 },
      { value: "Préservation du capital", label: "Préservation du capital", points: 0 },
      { value: "Autre", label: "Autre", points: 2 },
    ],
  },
  {
    id: "horizon",
    label: "Quel est votre horizon de placement ?",
    options: [
      { value: "Moins de 1 an", label: "Moins de 1 an", points: 0 },
      { value: "1 à 3 ans", label: "1 à 3 ans", points: 1 },
      { value: "3 à 5 ans", label: "3 à 5 ans", points: 2 },
      { value: "5 à 10 ans", label: "5 à 10 ans", points: 3 },
      { value: "Plus de 10 ans", label: "Plus de 10 ans", points: 4 },
    ],
  },
  {
    id: "reaction",
    label: "Comment réagiriez-vous si votre portefeuille perdait 20 % ?",
    options: [
      { value: "Tout vendre", label: "Je vendrais tout pour limiter les pertes", points: 0 },
      { value: "Vendre une partie", label: "Je vendrais une partie", points: 1 },
      { value: "Ne rien faire", label: "Je ne ferais rien et j'attendrais", points: 3 },
      { value: "Acheter davantage", label: "J'en profiterais pour acheter davantage", points: 4 },
    ],
  },
  {
    id: "experience",
    label: "Quelle est votre expérience en placement ?",
    options: [
      { value: "Débutant", label: "Débutant", points: 0 },
      { value: "Intermédiaire", label: "Intermédiaire", points: 2 },
      { value: "Avancé", label: "Avancé", points: 4 },
    ],
  },
  {
    id: "risk",
    label: "Quel niveau de risque financier acceptez-vous ?",
    options: [
      { value: "Faible", label: "Faible : je préfère la stabilité", points: 0 },
      { value: "Modéré", label: "Modéré : un équilibre entre risque et rendement", points: 2 },
      { value: "Élevé", label: "Élevé : je vise la croissance, malgré les fluctuations", points: 4 },
    ],
  },
  {
    id: "goal",
    label: "Quel est votre but de placement ?",
    options: [
      { value: "Protéger", label: "Protéger ce que j'ai", points: 0 },
      { value: "Équilibrer", label: "Croissance modeste et stable", points: 2 },
      { value: "Maximiser", label: "Maximiser la croissance", points: 4 },
    ],
  },
];

/** Questions facultatives (non notées). */
export const OPTIONAL_QUESTIONS: Question[] = [
  {
    id: "capital",
    label: "Capital approximatif à investir (facultatif)",
    options: ["Moins de 10 000 $", "10 000 $ à 50 000 $", "50 000 $ à 100 000 $", "Plus de 100 000 $", "Je préfère ne pas répondre"].map((v) => ({ value: v, label: v, points: 0 })),
  },
  {
    id: "contributions",
    label: "Contributions prévues (facultatif)",
    options: ["Aucune", "Occasionnelles", "Mensuelles"].map((v) => ({ value: v, label: v, points: 0 })),
  },
  {
    id: "liquidity",
    label: "Besoin de liquidités à court terme (facultatif)",
    options: ["Faible", "Moyen", "Élevé"].map((v) => ({ value: v, label: v, points: 0 })),
  },
];

const BLURB: Record<RiskLabel, string> = {
  Conservateur: "Vous privilégiez la stabilité et la protection du capital, quitte à accepter des rendements plus modestes.",
  Modéré: "Vous recherchez un équilibre entre croissance et stabilité, en acceptant des fluctuations raisonnables.",
  Dynamique: "Vous visez la croissance à long terme et acceptez des fluctuations importantes de la valeur de votre portefeuille.",
};

export function isComplete(a: Answers) {
  return QUESTIONS.every((q) => a[q.id]);
}

export function computeProfile(answers: Answers): FinancialProfile {
  const earned = QUESTIONS.reduce((s, q) => s + (q.options.find((o) => o.value === answers[q.id])?.points ?? 0), 0);
  const score = Math.round((earned / (QUESTIONS.length * 4)) * 100);
  const label: RiskLabel = score < 35 ? "Conservateur" : score < 65 ? "Modéré" : "Dynamique";
  const objective = answers.objective ?? "—";
  const horizon = answers.horizon ?? "—";
  const experience = answers.experience ?? "—";
  return {
    answers,
    score,
    label,
    objective,
    horizon,
    experience,
    summary: `${BLURB[label]} Objectif : ${objective.toLowerCase()}. Horizon : ${horizon.toLowerCase()}. Expérience : ${experience.toLowerCase()}.`,
    updatedAt: Date.now(),
  };
}

/** Part cible en actions et FNB selon le profil (valeurs indicatives, éducatives). */
export const EQUITY_RANGE: Record<RiskLabel, [number, number]> = {
  Conservateur: [0, 35],
  Modéré: [40, 65],
  Dynamique: [65, 100],
};
