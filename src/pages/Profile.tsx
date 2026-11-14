import { useState, type FormEvent } from "react";
import { errorText } from "../api/errors";
import type { InvestorProfile, RiskLevel } from "../api/types";
import AppHeader from "../components/AppHeader";
import { listPortfolios } from "../api/endpoints";
import { loadRisk, QUESTIONS, saveRisk, SCORE_MAX, type PortfolioRisk } from "../lib/risk";
import { useApp } from "../lib/store";

const RISK: { value: RiskLevel; label: string }[] = [
  { value: "low", label: "Faible" },
  { value: "low_moderate", label: "Faible à modéré" },
  { value: "moderate", label: "Modéré" },
  { value: "high", label: "Élevé" },
];
function RiskQuestionnaire({ userId }: { userId: string }) {
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [missing, setMissing] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [stored, setStored] = useState<Record<string, PortfolioRisk>>(() => loadRisk(userId));
  const done = Object.keys(answers).length;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg(""); setErr("");
    if (done < QUESTIONS.length) { setMissing(true); return setErr("Répondez à toutes les questions."); }
    setBusy(true);
    try {
      const { items } = await listPortfolios();
      if (!items.length) return setErr("Aucun portefeuille à mettre à jour.");
      const r = saveRisk(userId, items.map((p) => p.portfolioId), answers);
      setStored(loadRisk(userId));
      setMsg(`Score ${r.score}/${SCORE_MAX} · résultat ${r.value.toFixed(2)} enregistré pour ${items.length} portefeuille(s).`);
    } catch (x) { setErr(errorText(x)); } finally { setBusy(false); }
  }

  return (
    <form className="questionnaire" onSubmit={submit} noValidate style={{ marginBottom: 48 }}>
      <h2 className="auth-h" style={{ fontSize: 20 }}>Questionnaire de risque</h2>
      <div className="q-progress muted small">{done} / {QUESTIONS.length} réponses</div>
      {QUESTIONS.map((q, i) => (
        <fieldset key={q.id} className={`q${missing && answers[q.id] === undefined ? " missing" : ""}`}>
          <legend>{i + 1}. {q.label}</legend>
          <div className="opts">
            {q.options.map((o, j) => (
              <label key={o} className={`opt${answers[q.id] === j ? " on" : ""}`}>
                <input type="radio" name={q.id} checked={answers[q.id] === j} onChange={() => setAnswers({ ...answers, [q.id]: j })} />
                {o}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      {err && <p className="error" role="alert">{err}</p>}
      {msg && <div className="banner ok">{msg}</div>}
      <div><button className="btn" disabled={busy}>{busy ? "Calcul…" : "Calculer et enregistrer"}</button></div>
      {Object.keys(stored).length > 0 && (
        <p className="muted small">
          {Object.entries(stored).map(([id, r]) => `${id} : ${r.value.toFixed(2)} (score ${r.score}/${SCORE_MAX})`).join(" · ")}
        </p>
      )}
    </form>
  );
}

const lines = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);

export default function Profile() {
  const { user, saveProfile } = useApp();
  const p = user?.investorProfile;
  const [risk, setRisk] = useState<RiskLevel>(p?.riskLevel ?? "moderate");
  const [hMin, setHMin] = useState(p ? String(p.horizonMinYears) : "");
  const [hMax, setHMax] = useState(p?.horizonMaxYears != null ? String(p.horizonMaxYears) : "");
  const [objective, setObjective] = useState(p?.objective ?? "");
  const [constraints, setConstraints] = useState((p?.constraints ?? []).join("\n"));
  const [preferences, setPreferences] = useState((p?.preferences ?? []).join("\n"));
  const [excluded, setExcluded] = useState((p?.excludedAssetClasses ?? []).join("\n"));
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaved(false);
    const min = Number(hMin), max = hMax.trim() === "" ? undefined : Number(hMax);
    if (!Number.isInteger(min) || min < 0) return setErr("L'horizon minimum doit être un nombre entier d'années.");
    if (max !== undefined && (!Number.isInteger(max) || max < min)) return setErr("L'horizon maximum doit être un entier supérieur ou égal au minimum.");
    if (!objective.trim()) return setErr("L'objectif est requis.");
    const body: InvestorProfile = {
      riskLevel: risk, horizonMinYears: min, ...(max !== undefined ? { horizonMaxYears: max } : {}),
      objective: objective.trim(), constraints: lines(constraints), preferences: lines(preferences), excludedAssetClasses: lines(excluded),
    };
    setErr(""); setBusy(true);
    try { await saveProfile(body); setSaved(true); } catch (x) { setErr(errorText(x)); } finally { setBusy(false); }
  }

  return (
    <>
      <AppHeader />
      <main className="wrap" style={{ maxWidth: 760 }}>
        <div className="stock-hero"><div>
          <h1 className="auth-h">Profil investisseur</h1>
          <div className="meta">@{user?.username}{user?.baseCurrency ? ` · devise d'affichage : ${user.baseCurrency}` : ""}</div>
        </div></div>
        {!p && <div className="banner" style={{ background: "var(--ghost)", marginBottom: 20 }}>Profil non rempli : l'agent de gouvernance ne pourra pas vérifier l'adéquation de ses réponses tant qu'il n'est pas complété.</div>}
        {saved && <div className="banner ok" style={{ marginBottom: 20 }}>Profil enregistré.</div>}
        {user && <RiskQuestionnaire userId={user.userId} />}
        <form className="stack" onSubmit={submit} noValidate style={{ paddingBottom: 64 }}>
          <div className="field"><label htmlFor="risk">Niveau de risque</label>
            <select id="risk" className="input" value={risk} onChange={(e) => setRisk(e.target.value as RiskLevel)}>{RISK.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</select></div>
          <div className="row2">
            <div className="field"><label htmlFor="hmin">Horizon minimum (années)</label><input id="hmin" inputMode="numeric" value={hMin} onChange={(e) => setHMin(e.target.value)} /></div>
            <div className="field"><label htmlFor="hmax">Horizon maximum (facultatif)</label><input id="hmax" inputMode="numeric" value={hMax} onChange={(e) => setHMax(e.target.value)} /></div>
          </div>
          <div className="field"><label htmlFor="obj">Objectif</label><input id="obj" placeholder="ex. croissance à long terme" value={objective} onChange={(e) => setObjective(e.target.value)} /></div>
          <div className="field"><label htmlFor="con">Contraintes (une par ligne)</label><textarea id="con" rows={3} placeholder="ex. diversification minimale" value={constraints} onChange={(e) => setConstraints(e.target.value)} /></div>
          <div className="field"><label htmlFor="pre">Préférences (une par ligne)</label><textarea id="pre" rows={3} placeholder="ex. ESG" value={preferences} onChange={(e) => setPreferences(e.target.value)} /></div>
          <div className="field"><label htmlFor="exc">Classes d'actifs exclues (une par ligne)</label><textarea id="exc" rows={2} placeholder="ex. crypto" value={excluded} onChange={(e) => setExcluded(e.target.value)} /></div>
          {err && <p className="error" role="alert">{err}</p>}
          <div><button className="btn" disabled={busy}>{busy ? "Enregistrement…" : "Enregistrer"}</button></div>
          <p className="muted small">Profil fictif : n'entrez aucune donnée personnelle réelle.</p>
        </form>
      </main>
    </>
  );
}
