import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import PublicHeader from "../components/PublicHeader";
import PublicQuestionnaire, { PublicSummary } from "../components/PublicQuestionnaire";
import { loadPublicAnswers, savePublicAnswers } from "../lib/publicProfile";
import { useApp } from "../lib/store";

/*
 * Page d'accueil (présentation du prototype) avec le questionnaire PUBLIC du prototype, sans compte.
 * Calcul local seulement. L'inscription pose ensuite le questionnaire AlphaForge (lib/risk.ts).
 */
const FEATURES: [string, string][] = [
  ["Portefeuille", "Valeur, rendement, répartition et risque calculés pour vos positions."],
  ["Marchés", "Taux, devises et indicateurs pour situer vos placements."],
  ["Assistant IA", "Des réponses fondées sur vos données, avec leurs sources."],
  ["Profil de risque", "Un questionnaire pour situer votre tolérance au risque."],
];

export default function Landing() {
  const { status } = useApp();
  const [answers, setAnswers] = useState(loadPublicAnswers);
  const [editing, setEditing] = useState(false);

  if (status === "authed") return <Navigate to="/portefeuille" replace />;

  return (
    <>
      <PublicHeader actions />
      <main className="wrap">
        <section className="landing-hero">
          <div className="eyebrow">Pour investisseurs particuliers<span className="tag">Simulation</span></div>
          <h1 className="big filled">Vos placements,<br />expliqués simplement.</h1>
          <p className="lead">Suivez la valeur, la répartition et le risque de vos positions, et posez vos questions à l'assistant. Aucune transaction réelle, aucun conseil financier.</p>
          <div className="actions-row">
            <Link to="/inscription" className="btn">Créer un compte</Link>
            <a href="#profil" className="link">Découvrir mon profil d'investisseur →</a>
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

        <section id="profil" className="landing-q">
          <h2 className="section-title">Quel investisseur êtes-vous ?</h2>
          <p className="muted" style={{ marginBottom: 24 }}>Six questions, sans compte. Ce profil est indicatif; à l'inscription, un questionnaire de risque plus précis établit votre profil.</p>
          {answers && !editing ? (
            <>
              <PublicSummary answers={answers} />
              <div className="actions-row" style={{ marginTop: 24 }}>
                <Link to="/inscription" className="btn">Créer un compte</Link>
                <button type="button" className="link" onClick={() => setEditing(true)}>Modifier mes réponses</button>
              </div>
            </>
          ) : (
            <PublicQuestionnaire
              initial={answers ?? {}}
              submitLabel="Voir mon profil"
              onSubmit={(a) => { setAnswers(a); savePublicAnswers(a); setEditing(false); }}
            />
          )}
        </section>
      </main>
      <footer className="footer"><div className="wrap">Outil éducatif. Aucune transaction réelle. Ne constitue pas un conseil financier.</div></footer>
    </>
  );
}
