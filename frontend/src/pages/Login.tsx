import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { DEMO } from "../api/demo";
import { errorText } from "../api/errors";
import { AuthShell } from "../components/PublicHeader";
import { useApp } from "../lib/store";

export default function Login() {
  const { login, status } = useApp();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [pw, setPw] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (status === "authed") return <Navigate to="/accueil" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !pw) return setErr("Entrez votre nom d'utilisateur et votre mot de passe.");
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
    <AuthShell title="Connexion">
      <form onSubmit={submit} className="stack" noValidate>
        <div className="field"><label htmlFor="u">Nom d'utilisateur</label><input id="u" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} /></div>
        <div className="field">
          <label htmlFor="pw">Mot de passe</label>
          <input id="pw" type={show ? "text" : "password"} autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} />
          <button type="button" className="link show-pw" onClick={() => setShow(!show)}>{show ? "Masquer" : "Afficher"}</button>
        </div>
        {err && <p className="error" role="alert">{err}</p>}
        <button className="btn" disabled={busy}>{busy ? "Connexion…" : "Se connecter"}</button>
        <div className="auth-links"><Link to="/" className="link">← Accueil</Link><Link to="/inscription" className="link">Créer un compte</Link></div>
        {DEMO && <p className="notice">Mode démo (sans Cognito ni API) : <strong>demo</strong> / <strong>demo1234</strong></p>}
      </form>
    </AuthShell>
  );
}
