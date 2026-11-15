/* Page d'accueil épurée. Le questionnaire investisseur est réservé à la création du portefeuille. */
import { Link, Navigate } from "react-router-dom";
import PublicHeader from "../components/PublicHeader";
import { useApp } from "../lib/store";

export default function Landing() {
  const { status } = useApp();
  if (status === "authed") return <Navigate to="/accueil" replace />;

  return (
    <>
      <PublicHeader actions />
      <main className="wrap landing-page">
        <section className="landing-hero">
          <div className="landing-hero-content">
            <div className="eyebrow">Grow<span className="tag">Analyse quantitative</span></div>
            <h1 className="big filled">L'analyse quantitative pour tous&nbsp;!</h1>
            <p className="lead">Générez votre propre portefeuille diversifié en fonction de vos valeurs et de votre tolérance au risque, car chez Grow, nous sommes convaincus que chaque investisseur mérite son portefeuille.</p>
            <div className="actions-row">
              <Link to="/inscription" className="btn">Créer un compte</Link>
              <Link to="/portefeuille" className="btn-ghost">Explorer sans compte</Link>
            </div>
          </div>
        </section>
      </main>
      <footer className="footer"><div className="wrap">Outil éducatif. Aucune transaction réelle. Ne constitue pas un conseil financier.</div></footer>
    </>
  );
}
