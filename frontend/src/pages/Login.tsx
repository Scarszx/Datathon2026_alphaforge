import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { DEMO } from "../api/demo";
import { errorText } from "../api/errors";
import { AuthShell } from "../components/PublicHeader";
import { useT } from "../lib/i18n";
import { useApp } from "../lib/store";

export default function Login() {
  const { login, status } = useApp();
  const { L } = useT();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [pw, setPw] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (status === "authed") return <Navigate to="/accueil" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !pw) return setErr(L("Entrez votre nom d'utilisateur et votre mot de passe.", "Enter your username and password."));
    setBusy(true); setErr("");
    try {
      await login(username, pw);
      nav("/accueil", { replace: true });
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title={L("Connexion", "Log in")}>
      <form onSubmit={submit} className="stack" noValidate>
        <div className="field"><label htmlFor="u">{L("Nom d'utilisateur", "Username")}</label><input id="u" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} /></div>
        <div className="field">
          <label htmlFor="pw">{L("Mot de passe", "Password")}</label>
          <input id="pw" type={show ? "text" : "password"} autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} />
          <button type="button" className="link show-pw" onClick={() => setShow(!show)}>{show ? L("Masquer", "Hide") : L("Afficher", "Show")}</button>
        </div>
        {err && <p className="error" role="alert">{err}</p>}
        <button className="btn" disabled={busy}>{busy ? L("Connexion…", "Signing in…") : L("Se connecter", "Log in")}</button>
        <div className="auth-links"><Link to="/" className="link">{L("← Accueil", "← Home")}</Link><Link to="/inscription" className="link">{L("Créer un compte", "Create an account")}</Link></div>
        {DEMO && <p className="notice">{L("Mode démo (sans Cognito ni API) :", "Demo mode (no Cognito or API):")} <strong>demo</strong> / <strong>demo1234</strong></p>}
      </form>
    </AuthShell>
  );
}
