/*
 * Questionnaire personnel de l'accueil (sans compte), sur le modèle du portefeuille-prototype.
 * Il reprend les cinq questions de l'inscription (lib/risk.ts) : une seule échelle de risque (contrat 0.4.6).
 * Réponses gardées dans l'onglet (sessionStorage, effacées à la fermeture) et reprises à l'inscription.
 * Rien n'est envoyé à l'API avant la création du compte.
 */
import { isComplete } from "./risk";
type Answers = Record<string, number>;
const KEY = "af.personal.answers";
export function loadPersonalAnswers(): Answers | null {
  try {
    const v = JSON.parse(sessionStorage.getItem(KEY) ?? "null");
    return v && typeof v === "object" && isComplete(v) ? v : null;
  } catch { return null; }
}
export function savePersonalAnswers(a: Answers) {
  try { sessionStorage.setItem(KEY, JSON.stringify(a)); } catch { /* stockage indisponible */ }
}
