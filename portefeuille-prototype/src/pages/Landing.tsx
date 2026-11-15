import { useState } from "react";
import { Link } from "react-router-dom";
import Questionnaire, { ProfileSummary } from "../components/Questionnaire";
import type { Answers } from "../lib/types";

export const TEMP_KEY = "proto.public.answers";

export default function Landing() {
  const [answers, setAnswers] = useState<Answers | null>(() => {
    try { return JSON.parse(sessionStorage.getItem(TEMP_KEY) ?? "null"); } catch { return null; }
  });
  const [editing, setEditing] = useState(false);

  return (
    <>
      <header className="header">
        <div className="wrap">
          <div className="logo"><span className="logo-mark" aria-hidden="true" />Portefeuille</div>
          <div className="header-right">
            <Link to="/connexion" className="link">Connexion</Link>
            <Link to="/inscription" className="btn">Créer un compte</Link>
          </div>
        </div>
      </header>

      <main className="wrap">
        <section className="landing-hero">
          <div className="eyebrow">Pour investisseurs particuliers<span className="tag">Prototype</span></div>
          <h1 className="big filled">Votre portefeuille,<br />enfin clair.</h1>
          <p className="lead">Suivez vos placements, comprenez votre risque et posez vos questions à un assistant IA, le tout avec des données simulées pour explorer sans risque.</p>
          <div className="actions-row">
            <Link to="/inscription" className="btn">Créer un compte</Link>
            <a href="#profil" className="link">Découvrir mon profil d'investisseur →</a>
          </div>
        </section>

        <section className="stats">
          {[["Tableau de bord", "Valeur, rendement et répartition en un coup d'œil."], ["Assistant IA", "Des réponses fondées sur vos données, jamais inventées."], ["Ordres simulés", "Achetez et vendez sans risque réel."], ["Profil de risque", "Un portefeuille évalué selon vos objectifs."]].map(([t, d]) => (
            <div key={t} className="stat"><div className="stat-label" style={{ color: "var(--ink)", fontWeight: 600 }}>{t}</div><div className="stat-sub" style={{ marginTop: 6 }}>{d}</div></div>
          ))}
        </section>

        <section id="profil" className="landing-q">
          <h2 className="section-title">Quel investisseur êtes-vous ?</h2>
          <p className="muted" style={{ marginBottom: 24 }}>Six questions, sans compte. Votre profil temporaire n'est conservé que si vous vous inscrivez.</p>
          {answers && !editing ? (
            <>
              <ProfileSummary answers={answers} />
              <div className="actions-row" style={{ marginTop: 24 }}>
                <Link to="/inscription" className="btn">Créer un compte avec ce profil</Link>
                <button type="button" className="link" onClick={() => setEditing(true)}>Modifier mes réponses</button>
              </div>
            </>
          ) : (
            <Questionnaire
              initial={answers ?? {}}
              submitLabel="Voir mon profil"
              onSubmit={(a) => { setAnswers(a); setEditing(false); try { sessionStorage.setItem(TEMP_KEY, JSON.stringify(a)); } catch {} }}
            />
          )}
        </section>
      </main>

      <footer className="footer"><div className="wrap">Prototype à des fins éducatives. Données et prix fictifs; aucune transaction réelle. Ne constitue pas un conseil financier.</div></footer>
    </>
  );
}
