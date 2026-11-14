import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { errorText } from "../api/errors";
import { useApp } from "../lib/store";

export default function Login() {
  const { login, status } = useApp();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [pw, setPw] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (status === "authed") return <Navigate to="/portefeuille" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !pw) return setErr("Entrez votre nom d'utilisateur et votre mot de passe.");
    setBusy(true); setErr("");
    try {
      await login(username, pw);
      nav("/portefeuille", { replace: true });
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="header"><div className="wrap"><span className="logo"><span className="logo-mark" aria-hidden="true" />AlphaForge</span></div></header>
      <main className="auth">
        <div className="auth-card">
          <h1>Connexion</h1>
          <form onSubmit={submit} className="stack" noValidate>
            <div className="field"><label htmlFor="u">Nom d'utilisateur</label><input id="u" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} /></div>
            <div className="field">
              <label htmlFor="pw">Mot de passe</label>
              <input id="pw" type={show ? "text" : "password"} autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} />
              <button type="button" className="link show-pw" onClick={() => setShow(!show)}>{show ? "Masquer" : "Afficher"}</button>
            </div>
            {err && <p className="error" role="alert">{err}</p>}
            <button className="btn" disabled={busy}>{busy ? "Connexion…" : "Se connecter"}</button>
            <p className="notice">Simulation seulement : aucune transaction réelle, aucun conseil financier personnalisé. Les comptes sont créés par l'équipe.</p>
          </form>
        </div>
      </main>
    </>
  );
}
