import { NavLink } from "react-router-dom";
import growLogo from "../assets/grow-logo.svg";
import { useT } from "../lib/i18n";
import { useApp } from "../lib/store";
import LangSwitch from "./LangSwitch";
import Avatar from "./Avatar";

export default function AppHeader() {
  const { user, logout } = useApp();
  const { t, L } = useT();
  const cls = ({ isActive }: { isActive: boolean }) => `nav-link${isActive ? " on" : ""}`;
  return (
    <header className="header">
      <div className="wrap">
        <NavLink to="/accueil" className="logo" aria-label={L("Grow — Accueil", "Grow — Home")}>
          <img className="brand-logo" src={growLogo} alt="Grow" />
        </NavLink>
        <nav className="nav" aria-label={t("nav.aria")}>
          <NavLink to="/chat" className={cls}>{t("nav.session")}</NavLink>
          <NavLink to="/portefeuille" className={cls}>{t("nav.portfolio")}</NavLink>
          <NavLink to="/marches" className={cls}>{t("nav.markets")}</NavLink>
          <NavLink to="/profil" className={cls}>{t("nav.profile")}</NavLink>
        </nav>
        <div className="header-right desktop-session-actions">
          <LangSwitch />
          {user ? (
            <>
              <span className="header-user">
                <Avatar seed={user.userId} size={28} label={user.displayName ?? user.username} />
                <span className="muted small hide-sm">{user.displayName ?? user.username}</span>
              </span>
              <button type="button" className="link" onClick={logout}>{t("nav.logout")}</button>
            </>
          ) : (
            <NavLink to="/login" className="link">{t("nav.login")}</NavLink>
          )}
        </div>
        <details className="mobile-menu">
          <summary aria-label={L("Ouvrir la navigation", "Open navigation")}>
            <span aria-hidden="true" />
            <span aria-hidden="true" />
            <span aria-hidden="true" />
          </summary>
          <nav className="mobile-menu-panel" aria-label={L("Navigation mobile", "Mobile navigation")}>
            <NavLink to="/chat" className={cls}>{t("nav.session")}</NavLink>
            <NavLink to="/portefeuille" className={cls}>{t("nav.portfolio")}</NavLink>
            <NavLink to="/marches" className={cls}>{t("nav.markets")}</NavLink>
            <NavLink to="/profil" className={cls}>{t("nav.profile")}</NavLink>
            <div className="mobile-menu-account">
              <LangSwitch />
              {user ? (
                <>
                  <span>{user.displayName ?? user.username}</span>
                  <button type="button" className="link" onClick={logout}>{t("nav.logout")}</button>
                </>
              ) : (
                <NavLink to="/login" className="link">{t("nav.login")}</NavLink>
              )}
            </div>
          </nav>
        </details>
      </div>
    </header>
  );
}
