import { Link } from "react-router-dom";
import { useApp } from "../lib/store";
import { time } from "../lib/format";
import type { ReactNode } from "react";

export default function AppHeader({ children, showRefresh = false }: { children?: ReactNode; showRefresh?: boolean }) {
  const { user, logout, updatedAt, refreshPrices } = useApp();
  return (
    <header className="header">
      <div className="wrap">
        <Link to="/tableau-de-bord" className="logo"><span className="logo-mark" aria-hidden="true" />Portefeuille</Link>
        <div className="header-right">
          {showRefresh && (
            <>
              <span className="updated hide-sm">Mis à jour à {time(new Date(updatedAt))}</span>
              <button type="button" className="icon" title="Actualiser les cours" aria-label="Actualiser les cours" onClick={refreshPrices}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2.5v3h-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </button>
            </>
          )}
          {children}
          <Link to="/profil" className="link hide-sm">{user?.firstName}</Link>
          <button type="button" className="link" onClick={logout}>Déconnexion</button>
        </div>
      </div>
    </header>
  );
}
