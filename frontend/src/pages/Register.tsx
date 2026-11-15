import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { signUp } from "../api/auth";
import { errorText } from "../api/errors";
import PublicHeader from "../components/PublicHeader";
import { useApp } from "../lib/store";

/*
 * L'inscription crée uniquement le compte Cognito. Le questionnaire investisseur est présenté
 * ensuite sur /portefeuille, juste avant la création du portefeuille principal.
 */
type Step = "account" | "done";

export default function Register() {
  const { status, login } = useApp();
  const nav = useNavigate();
  const [step, setStep] = useState<Step>("account");
  const [f, setF] = useState({ firstName: "", lastName: "", email: "", username: "", age: "", password: "", confirm: "" });
  const [terms, setTerms] = useState(false);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const finishing = useRef(false);

  // Un utilisateur déjà connecté n'a rien à faire ici (sauf pendant la fin du parcours).
  if (status === "authed" && !finishing.current) return <Navigate to="/portefeuille" replace />;

  const set = (k: keyof typeof f) => (e: ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  async function create(e: FormEvent) {
    e.preventDefault();
    const x: Record<string, string> = {};
    if (!f.firstName.trim()) x.firstName = "Requis";
    if (!f.lastName.trim()) x.lastName = "Requis";
    if (!/^\S+@\S+\.\S+$/.test(f.email)) x.email = "Courriel invalide";
    if (!/^[a-zA-Z0-9_.-]{3,30}$/.test(f.username)) x.username = "3 à 30 caractères (lettres, chiffres, _ . -)";
    const age = Number(f.age);
    if (!Number.isInteger(age) || age < 18 || age > 110) x.age = "Vous devez avoir 18 ans ou plus";
    if (f.password.length < 8) x.password = "Au moins 8 caractères";
    if (f.confirm !== f.password) x.confirm = "Les mots de passe diffèrent";
    if (!terms) x.terms = "Vous devez accepter les conditions";
    setErrs(x);
    if (Object.keys(x).length > 0) return;

    setBusy(true); setErr("");
    let accountCreated = false;
    try {
      await signUp(f.username.trim(), f.password, f.email.trim(), f.firstName.trim(), f.lastName.trim());
      accountCreated = true;
      finishing.current = true;
      await login(f.username, f.password);
      nav("/portefeuille", { replace: true });
    } catch (failure) {
      finishing.current = false;
      if (accountCreated) {
        setErr(`Compte créé, mais la connexion a échoué : ${errorText(failure)}`);
        setStep("done");
      } else {
        setErr(errorText(failure));
      }
    } finally {
      setBusy(false);
    }
  }

  const fld = (k: keyof typeof f, label: string, type = "text", auto?: string) => (
    <div className="field">
      <label htmlFor={k}>{label}</label>
      <input id={k} type={type} autoComplete={auto} value={f[k]} onChange={set(k)} aria-invalid={!!errs[k]} />
      {errs[k] && <span className="error">{errs[k]}</span>}
    </div>
  );

  return (
    <>
      <PublicHeader />
      <main className="auth">
        <div className="auth-card">
          {step === "done" ? (
            <>
              <h1>Compte créé</h1>
              <div className="stack">
                <p className="error" role="alert">{err}</p>
                <p className="muted small">Après la connexion, votre profil investisseur vous sera demandé lors de la création de votre portefeuille.</p>
                <Link to="/login" className="btn">Aller à la connexion</Link>
              </div>
            </>
          ) : (
            <>
              <h1>Créer un compte</h1>
              <form onSubmit={create} className="stack" noValidate>
                <div className="row2">{fld("firstName", "Prénom", "text", "given-name")}{fld("lastName", "Nom", "text", "family-name")}</div>
                {fld("email", "Courriel", "email", "email")}
                <div className="row2">{fld("username", "Nom d'utilisateur", "text", "username")}{fld("age", "Âge")}</div>
                <div className="row2">{fld("password", "Mot de passe", "password", "new-password")}{fld("confirm", "Confirmation", "password", "new-password")}</div>
                <label className="check"><input type="checkbox" checked={terms} onChange={(e) => setTerms(e.target.checked)} /> J'ai lu et j'accepte les conditions et l'avis de non-responsabilité : cet outil est éducatif et ne constitue pas un conseil financier.</label>
                {errs.terms && <span className="error">{errs.terms}</span>}
                {err && <p className="error" role="alert">{err}</p>}
                <button className="btn" disabled={busy}>{busy ? "Création…" : "Créer mon compte"}</button>
                <div className="auth-links"><Link to="/login" className="link">Déjà inscrit ? Se connecter</Link></div>
              </form>
            </>
          )}
        </div>
      </main>
    </>
  );
}
