import { NavLink } from "react-router-dom";
import { useApp } from "../lib/store";

export default function AppHeader() {
  const { user, logout } = useApp();
  const cls = ({ isActive }: { isActive: boolean }) => `nav-link${isActive ? " on" : ""}`;
  return (
    <header className="header">
      <div className="wrap">
        <NavLink to="/portefeuille" className="logo"><span className="logo-mark" aria-hidden="true" />AlphaForge</NavLink>
        <nav className="nav" aria-label="Navigation principale">
          <NavLink to="/chat" className={cls}>Session</NavLink>
          <NavLink to="/portefeuille" className={cls}>Portefeuille</NavLink>
          <NavLink to="/marches" className={cls}>Marchés</NavLink>
          <NavLink to="/profil" className={cls}>Profil</NavLink>
        </nav>
        <div className="header-right">
          <span className="muted small hide-sm">{user?.displayName ?? user?.username}</span>
          <button type="button" className="link" onClick={logout}>Déconnexion</button>
        </div>
      </div>
    </header>
  );
}
