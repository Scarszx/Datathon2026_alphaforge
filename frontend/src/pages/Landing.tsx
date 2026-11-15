/* Page d'accueil (présentation de l'outil). v0.4.6 : le questionnaire public et la carte
 * « Votre profil préliminaire » sont retirés (une seule échelle de risque, une seule entrée :
 * le questionnaire de l'inscription). Aucun symbole de titre dans les textes. */
import { Link, Navigate } from "react-router-dom";
import PublicHeader from "../components/PublicHeader";
import { useApp } from "../lib/store";

const FEATURES: [string, string][] = [
  ["Portefeuille", "Valeur, répartition et risque calculés par le back pour vos positions."],
  ["Comparaison par catégorie", "Sur demande, comparez votre idée avec une catégorie d'actifs, au même montant."],
  ["Règles R1 à R10", "Chaque règle dit ce qu'elle a fait : non déclenchée, à vérifier ou déclenchée."],
  ["Sources affichées", "Chaque chiffre et chaque texte cité renvoie à sa preuve dans le registre."],
];

const STEPS: [string, string][] = [
  ["1. Décrivez votre intention", "En langage libre : l'orchestrateur cadre la demande et propose un mandat (objectif, horizon, tolérance, capacité)."],
  ["2. Confirmez le mandat", "Chaque champ porte sa source (profil, réponse, hypothèse d'équipe). Rien ne se calcule avant votre confirmation."],
  ["3. Lisez scénarios et règles", "L'impact sur l'ensemble du portefeuille, les règles R1 à R10 avec leur libellé, les preuves et les textes réglementaires dont elles s'inspirent."],
];

export default function Landing() {
  const { status } = useApp();
  if (status === "authed") return <Navigate to="/portefeuille" replace />;

  return (
    <>
      <PublicHeader actions />
      <main className="wrap">
        <section className="landing-hero">
          <div className="eyebrow">Pour investisseurs particuliers<span className="tag">Simulation</span></div>
          <h1 className="big filled">Vos placements,<br />expliqués simplement.</h1>
          <p className="lead">Suivez la valeur, la répartition et le risque de vos positions, et testez une idée avant de décider. Aucune transaction réelle, aucun conseil financier.</p>
          <div className="actions-row">
            <Link to="/inscription" className="btn">Créer un compte</Link>
          </div>
        </section>

        <section className="stats">
          {FEATURES.map(([t, d]) => (
            <div key={t} className="stat">
              <div className="stat-label" style={{ color: "var(--ink)", fontWeight: 600 }}>{t}</div>
              <div className="stat-sub" style={{ marginTop: 6 }}>{d}</div>
            </div>
          ))}
        </section>

        <section className="landing-q">
          <h2 className="section-title">Comment ça marche</h2>
          <p className="muted" style={{ marginBottom: 24 }}>Une session en trois étapes, du cadrage à l'analyse. Votre profil de risque (tolérance et capacité, de 1 à 5) est établi à l'inscription.</p>
          <div className="stats">
            {STEPS.map(([t, d]) => (
              <div key={t} className="stat">
                <div className="stat-label" style={{ color: "var(--ink)", fontWeight: 600 }}>{t}</div>
                <div className="stat-sub" style={{ marginTop: 6 }}>{d}</div>
              </div>
            ))}
          </div>
          <div className="actions-row" style={{ marginTop: 28 }}>
            <Link to="/inscription" className="btn">Créer un compte</Link>
          </div>
        </section>
      </main>
      <footer className="footer"><div className="wrap">Outil éducatif. Aucune transaction réelle. Ne constitue pas un conseil financier.</div></footer>
    </>
  );
}
