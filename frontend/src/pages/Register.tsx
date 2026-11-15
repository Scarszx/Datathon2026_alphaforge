import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { signUp } from "../api/auth";
import { listPortfolios } from "../api/endpoints";
import { ApiError, errorText } from "../api/errors";
import type { Jurisdiction } from "../api/types";
import PublicHeader from "../components/PublicHeader";
import RiskForm from "../components/RiskForm";
import { profileFromAnswers, saveRisk } from "../lib/risk";
import { useApp } from "../lib/store";
import { EMPTY_INDUSTRIES, type IndustryChoice } from "../lib/industries";
import { loadPersonalAnswers } from "../lib/personalDraft";

/*
 * Inscription : 1) compte  2) questionnaire de risque. Le compte est confirmé d'office (déclencheur pre sign-up), sans code par courriel.
 * Ensuite : connexion, PUT /v1/me/profile avec le profil déduit du questionnaire, et résultat enregistré
 * pour les portefeuilles existants (comme sur /profil). Le mot de passe ne vit qu'en mémoire pendant le parcours.
 */
type Answers = Record<string, number>;
type Step = "account" | "risk" | "done";

export default function Register() {
  const { status, login, saveProfile } = useApp();
  const nav = useNavigate();
  const [step, setStep] = useState<Step>("account");
  const [f, setF] = useState({ firstName: "", lastName: "", email: "", username: "", age: "", password: "", confirm: "" });
  const [terms, setTerms] = useState(false);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const answers = useRef<Answers | null>(null);
  const provinceRef = useRef<Jurisdiction | null>(null);
  const industriesRef = useRef<IndustryChoice>(EMPTY_INDUSTRIES);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const finishing = useRef(false);

  // Un utilisateur déjà connecté n'a rien à faire ici (sauf pendant la fin du parcours).
  if (status === "authed" && !finishing.current) return <Navigate to="/portefeuille" replace />;

  const set = (k: keyof typeof f) => (e: ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  function next(e: FormEvent) {
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
    if (Object.keys(x).length === 0) { setErr(""); setStep("risk"); }
  }

  async function create(a: Answers, province: Jurisdiction, industries: IndustryChoice) {
    answers.current = a;
    industriesRef.current = industries;
    provinceRef.current = province;
    setBusy(true); setErr("");
    try {
      await signUp(f.username.trim(), f.password, f.email.trim(), f.firstName.trim(), f.lastName.trim());
    } catch (x) {
      setErr(errorText(x)); setBusy(false);
      // Nom d'utilisateur pris, mot de passe refusé, courriel invalide : à corriger à l'étape 1.
      // Autres erreurs (Cognito non configuré, réseau) : affichées ici, sous le bouton.
      if (x instanceof ApiError && x.code === "VALIDATION_ERROR") setStep("account");
      return;
    }
    await finish().catch(afterAccountError);
    setBusy(false);
  }

  /** Le compte existe déjà : on ne revient pas à l'étape 1, on invite à se connecter. */
  function afterAccountError(x: unknown) {
    setErr(`Compte créé, mais la connexion a échoué : ${errorText(x)}`);
    setStep("done");
  }

  /** Compte créé et confirmé : connexion, puis enregistrement du profil. */
  async function finish() {
    finishing.current = true;
    let userId: string;
    try {
      userId = (await login(f.username, f.password)).userId;
    } catch (x) {
      finishing.current = false;
      throw x;
    }
    const a = answers.current!;
    const province = provinceRef.current!;
    let warning = "";
    try {
      await saveProfile(profileFromAnswers(a, province, industriesRef.current));
    } catch (x) {
      warning = `Compte créé, mais le profil n'a pas pu être enregistré : ${errorText(x)} Vous pouvez le remplir sur cette page.`;
    }
    // Résultat gardé pour l'utilisateur, et pour chaque portefeuille existant. Les portefeuilles créés plus tard
    // le reçoivent à l'ouverture de /profil (syncRisk).
    let ids: string[] = [];
    try { ids = (await listPortfolios()).items.map((p) => p.portfolioId); } catch { /* liste indisponible */ }
    saveRisk(userId, ids, a, province);
    nav(warning ? "/profil" : "/portefeuille", { replace: true, state: warning ? { warning } : undefined });
  }

  const fld = (k: keyof typeof f, label: string, type = "text", auto?: string) => (
    <div className="field">
      <label htmlFor={k}>{label}</label>
      <input id={k} type={type} autoComplete={auto} value={f[k]} onChange={set(k)} aria-invalid={!!errs[k]} />
      {errs[k] && <span className="error">{errs[k]}</span>}
    </div>
  );

  if (step === "risk")
    return (
      <>
        <PublicHeader />
        <main className="wrap" style={{ maxWidth: 720, padding: "40px 24px 80px" }}>
          <h1 className="auth-h">Votre profil financier</h1>
          <p className="muted" style={{ margin: "6px 0 24px" }}>
            Cinq questions pour situer votre tolérance au risque, plus votre province et vos industries d'intérêt. Aucune information sensible n'est requise.
          </p>
          <RiskForm showIndustries initial={loadPersonalAnswers() ?? {}} busy={busy} submitLabel={busy ? "Création…" : "Créer mon compte"} onSubmit={create}>
            {err && <p className="error" role="alert">{err}</p>}
          </RiskForm>
          <button type="button" className="link" style={{ marginTop: 16 }} onClick={() => setStep("account")}>← Retour</button>
        </main>
      </>
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
                <p className="muted small">Votre profil de risque pourra être rempli sur la page Profil après la connexion.</p>
                <Link to="/login" className="btn">Aller à la connexion</Link>
              </div>
            </>
          ) : (
            <>
              <h1>Créer un compte</h1>
              <form onSubmit={next} className="stack" noValidate>
                <div className="row2">{fld("firstName", "Prénom", "text", "given-name")}{fld("lastName", "Nom", "text", "family-name")}</div>
                {fld("email", "Courriel", "email", "email")}
                <div className="row2">{fld("username", "Nom d'utilisateur", "text", "username")}{fld("age", "Âge")}</div>
                <div className="row2">{fld("password", "Mot de passe", "password", "new-password")}{fld("confirm", "Confirmation", "password", "new-password")}</div>
                <label className="check"><input type="checkbox" checked={terms} onChange={(e) => setTerms(e.target.checked)} /> J'ai lu et j'accepte les conditions et l'avis de non-responsabilité : cet outil est éducatif et ne constitue pas un conseil financier.</label>
                {errs.terms && <span className="error">{errs.terms}</span>}
                {err && <p className="error" role="alert">{err}</p>}
                <button className="btn">Continuer</button>
                <div className="auth-links"><Link to="/login" className="link">Déjà inscrit ? Se connecter</Link></div>
              </form>
            </>
          )}
        </div>
      </main>
    </>
  );
}
