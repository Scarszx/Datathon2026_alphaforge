import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import growLogo from "../assets/grow-logo.svg";

/** En-tête des pages sans session (même présentation que le prototype). `actions` : liens à droite (accueil). */
export default function PublicHeader({ actions = false }: { actions?: boolean }) {
  return (
    <header className="header">
      <div className="wrap">
        <Link to="/" className="logo" aria-label="Grow — Accueil">
          <img className="brand-logo" src={growLogo} alt="Grow" />
        </Link>
        {actions && (
          <div className="header-right">
            <Link to="/login" className="link">Connexion</Link>
            <Link to="/inscription" className="btn">Créer un compte</Link>
          </div>
        )}
      </div>
    </header>
  );
}

/** Carte centrée des pages de connexion et d'inscription (Shell du prototype). */
export function AuthShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <PublicHeader />
      <main className="auth"><div className="auth-card"><h1>{title}</h1>{children}</div></main>
    </>
  );
}
