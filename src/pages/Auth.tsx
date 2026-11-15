import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import Questionnaire, { ProfileSummary } from "../components/Questionnaire";
import { useApp, TEMP_KEY } from "../lib/legacyStore";
import type { Answers } from "../lib/types";

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <>
      <header className="header"><div className="wrap"><Link to="/" className="logo"><span className="logo-mark" aria-hidden="true" />Portefeuille</Link></div></header>
      <main className="auth"><div className="auth-card"><h1>{title}</h1>{children}</div></main>
    </>
  );
}

export function Login() {
  const { login } = useApp();
  const nav = useNavigate();
  const [id, setId] = useState("");
  const [pw, setPw] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!id.trim() || !pw) return setErr("Entrez votre courriel (ou nom d'utilisateur) et votre mot de passe.");
    setBusy(true); setErr("");
    const r = await login(id, pw);
    setBusy(false);
    if (r.ok) nav("/tableau-de-bord"); else setErr(r.error);
  }

  return (
    <Shell title="Connexion">
      <form onSubmit={submit} className="stack" noValidate>
        <div className="field"><label htmlFor="id">Courriel ou nom d'utilisateur</label><input id="id" autoComplete="username" value={id} onChange={(e) => setId(e.target.value)} /></div>
        <div className="field">
          <label htmlFor="pw">Mot de passe</label>
          <input id="pw" type={show ? "text" : "password"} autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} />
          <button type="button" className="link show-pw" onClick={() => setShow(!show)}>{show ? "Masquer" : "Afficher"}</button>
        </div>
        {err && <p className="error" role="alert">{err}</p>}
        <button className="btn" disabled={busy}>{busy ? "Connexion…" : "Se connecter"}</button>
        <div className="auth-links"><Link to="/mot-de-passe-oublie" className="link">Mot de passe oublié ?</Link><Link to="/inscription" className="link">Créer un compte</Link></div>
        <p className="notice">Compte démo : <strong>demo@example.com</strong> / <strong>demo1234</strong></p>
      </form>
    </Shell>
  );
}

export function Forgot() {
  const [sent, setSent] = useState(false);
  const [email, setEmail] = useState("");
  return (
    <Shell title="Mot de passe oublié">
      {sent ? (
        <div className="stack"><div className="banner ok">Si un compte existe pour {email}, un lien de réinitialisation a été envoyé. (Simulation : aucun courriel réel n'est expédié.)</div><Link to="/connexion" className="link">← Retour à la connexion</Link></div>
      ) : (
        <form className="stack" onSubmit={(e) => { e.preventDefault(); if (email.includes("@")) setSent(true); }}>
          <div className="field"><label htmlFor="em">Courriel</label><input id="em" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
          <button className="btn">Envoyer le lien</button>
          <Link to="/connexion" className="link">← Retour à la connexion</Link>
        </form>
      )}
    </Shell>
  );
}

export function Register() {
  const { register } = useApp();
  const nav = useNavigate();
  const [f, setF] = useState({ firstName: "", lastName: "", email: "", username: "", password: "", confirm: "", age: "" });
  const [terms, setTerms] = useState(false);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [step, setStep] = useState<1 | 2>(1);
  const [busy, setBusy] = useState(false);
  const [serverErr, setServerErr] = useState("");
  const temp: Answers | null = (() => { try { return JSON.parse(sessionStorage.getItem(TEMP_KEY) ?? "null"); } catch { return null; } })();
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  function next(e: FormEvent) {
    e.preventDefault();
    const x: Record<string, string> = {};
    if (!f.firstName.trim()) x.firstName = "Requis";
    if (!f.lastName.trim()) x.lastName = "Requis";
    if (!/^\S+@\S+\.\S+$/.test(f.email)) x.email = "Courriel invalide";
    if (!/^[a-zA-Z0-9_.-]{3,20}$/.test(f.username)) x.username = "3 à 20 caractères (lettres, chiffres, _ . -)";
    if (f.password.length < 8) x.password = "Au moins 8 caractères";
    if (f.confirm !== f.password) x.confirm = "Les mots de passe diffèrent";
    const age = Number(f.age);
    if (!Number.isInteger(age) || age < 18 || age > 110) x.age = "Vous devez avoir 18 ans ou plus";
    if (!terms) x.terms = "Vous devez accepter les conditions";
    setErrs(x);
    if (Object.keys(x).length === 0) setStep(2);
  }

  async function finish(answers: Answers) {
    setBusy(true);
    const r = await register({ firstName: f.firstName, lastName: f.lastName, email: f.email, username: f.username, password: f.password, age: Number(f.age) }, answers);
    setBusy(false);
    if (!r.ok) { setServerErr(r.error); setStep(1); return; }
    sessionStorage.removeItem(TEMP_KEY);
    nav("/tableau-de-bord");
  }

  const fld = (k: keyof typeof f, label: string, type = "text", auto?: string) => (
    <div className="field"><label htmlFor={k}>{label}</label><input id={k} type={type} autoComplete={auto} value={f[k]} onChange={set(k)} aria-invalid={!!errs[k]} />{errs[k] && <span className="error">{errs[k]}</span>}</div>
  );

  if (step === 2)
    return (
      <>
        <header className="header"><div className="wrap"><Link to="/" className="logo"><span className="logo-mark" aria-hidden="true" />Portefeuille</Link></div></header>
        <main className="wrap" style={{ maxWidth: 720, padding: "40px 24px 80px" }}>
          <h1 className="auth-h">Votre profil financier</h1>
          <p className="muted" style={{ margin: "6px 0 24px" }}>{temp ? "Voici vos réponses précédentes : confirmez ou modifiez-les." : "Quelques questions pour personnaliser votre expérience. Aucune information sensible n'est requise."}</p>
          {temp && <div style={{ marginBottom: 24 }}><ProfileSummary answers={temp} /></div>}
          <Questionnaire initial={temp ?? {}} optional submitLabel={busy ? "Création…" : "Créer mon compte"} onSubmit={finish} />
          <button type="button" className="link" style={{ marginTop: 16 }} onClick={() => setStep(1)}>← Retour</button>
        </main>
      </>
    );

  return (
    <Shell title="Créer un compte">
      <form onSubmit={next} className="stack" noValidate>
        <div className="row2">{fld("firstName", "Prénom", "text", "given-name")}{fld("lastName", "Nom", "text", "family-name")}</div>
        {fld("email", "Courriel", "email", "email")}
        <div className="row2">{fld("username", "Nom d'utilisateur", "text", "username")}{fld("age", "Âge")}</div>
        <div className="row2">{fld("password", "Mot de passe", "password", "new-password")}{fld("confirm", "Confirmation", "password", "new-password")}</div>
        <label className="check"><input type="checkbox" checked={terms} onChange={(e) => setTerms(e.target.checked)} /> J'ai lu et j'accepte les conditions et l'avis de non-responsabilité : cet outil est éducatif et ne constitue pas un conseil financier.</label>
        {errs.terms && <span className="error">{errs.terms}</span>}
        {serverErr && <p className="error" role="alert">{serverErr}</p>}
        <button className="btn">Continuer</button>
        <div className="auth-links"><Link to="/connexion" className="link">Déjà inscrit ? Se connecter</Link></div>
      </form>
    </Shell>
  );
}
