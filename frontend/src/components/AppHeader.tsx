import { NavLink } from "react-router-dom";
import growLogo from "../assets/grow-logo.svg";
import { useApp } from "../lib/store";
import Avatar from "./Avatar";

export default function AppHeader() {
  const { user, logout } = useApp();
  const cls = ({ isActive }: { isActive: boolean }) => `nav-link${isActive ? " on" : ""}`;
  return (
    <header className="header">
      <div className="wrap">
        <NavLink to="/accueil" className="logo" aria-label="Grow — Accueil">
          <img className="brand-logo" src={growLogo} alt="Grow" />
        </NavLink>
        <nav className="nav" aria-label="Navigation principale">
          <NavLink to="/chat" className={cls}>Session</NavLink>
          <NavLink to="/portefeuille" className={cls}>Portefeuille</NavLink>
          <NavLink to="/marches" className={cls}>Marchés</NavLink>
          <NavLink to="/profil" className={cls}>Profil</NavLink>
        </nav>
        <div className="header-right desktop-session-actions">
          {user ? (
            <>
              <span className="header-user">
                <Avatar seed={user.userId} size={28} label={user.displayName ?? user.username} />
                <span className="muted small hide-sm">{user.displayName ?? user.username}</span>
              </span>
              <button type="button" className="link" onClick={logout}>Déconnexion</button>
            </>
          ) : (
            <NavLink to="/login" className="link">Connexion</NavLink>
          )}
        </div>
        <details className="mobile-menu">
          <summary aria-label="Ouvrir la navigation">
            <span aria-hidden="true" />
            <span aria-hidden="true" />
            <span aria-hidden="true" />
          </summary>
          <nav className="mobile-menu-panel" aria-label="Navigation mobile">
            <NavLink to="/chat" className={cls}>Session</NavLink>
            <NavLink to="/portefeuille" className={cls}>Portefeuille</NavLink>
            <NavLink to="/marches" className={cls}>Marchés</NavLink>
            <NavLink to="/profil" className={cls}>Profil</NavLink>
            <div className="mobile-menu-account">
              {user ? (
                <>
                  <span>{user.displayName ?? user.username}</span>
                  <button type="button" className="link" onClick={logout}>Déconnexion</button>
                </>
              ) : (
                <NavLink to="/login" className="link">Connexion</NavLink>
              )}
            </div>
          </nav>
        </details>
      </div>
    </header>
  );
}
