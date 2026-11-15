/*
 * Questionnaire PUBLIC de la page d'accueil (sans compte), repris du prototype : 6 questions, score sur 100.
 * Distinct du questionnaire d'inscription (lib/risk.ts : 5 questions, score 5–25, calcul 10 − 9 × …).
 * Calcul local seulement : rien n'est envoyé à l'API ni repris à l'inscription.
 */
export type PublicAnswers = Record<string, string>;
export type PublicLabel = "Conservateur" | "Modéré" | "Dynamique";
type Option = { value: string; label: string; points: number };
export type PublicQuestion = { id: string; label: string; options: Option[] };

export const PUBLIC_QUESTIONS: PublicQuestion[] = [
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

const BLURB: Record<PublicLabel, string> = {
  Conservateur: "Vous privilégiez la stabilité et la protection du capital, quitte à accepter des rendements plus modestes.",
  Modéré: "Vous recherchez un équilibre entre croissance et stabilité, en acceptant des fluctuations raisonnables.",
  Dynamique: "Vous visez la croissance à long terme et acceptez des fluctuations importantes de la valeur de votre portefeuille.",
};

export const isPublicComplete = (a: PublicAnswers) => PUBLIC_QUESTIONS.every((q) => a[q.id]);

/** Score sur 100 (points obtenus / points maximum) et libellé : < 35 Conservateur, < 65 Modéré, sinon Dynamique. */
export function publicProfile(a: PublicAnswers) {
  const earned = PUBLIC_QUESTIONS.reduce((s, q) => s + (q.options.find((o) => o.value === a[q.id])?.points ?? 0), 0);
  const score = Math.round((earned / (PUBLIC_QUESTIONS.length * 4)) * 100);
  const label: PublicLabel = score < 35 ? "Conservateur" : score < 65 ? "Modéré" : "Dynamique";
  const lower = (k: string) => (a[k] ?? "—").toLowerCase();
  return {
    score, label,
    summary: `${BLURB[label]} Objectif : ${lower("objective")}. Horizon : ${lower("horizon")}. Expérience : ${lower("experience")}.`,
  };
}

/* Réponses gardées dans l'onglet pour réafficher le résultat (sessionStorage : effacées à la fermeture). */
const KEY = "af.public.answers";

export function loadPublicAnswers(): PublicAnswers | null {
  try {
    const v = JSON.parse(sessionStorage.getItem(KEY) ?? "null");
    return v && typeof v === "object" && isPublicComplete(v) ? v : null;
  } catch { return null; }
}

export function savePublicAnswers(a: PublicAnswers) {
  try { sessionStorage.setItem(KEY, JSON.stringify(a)); } catch { /* stockage indisponible */ }
}
