import { useEffect, useState, type FormEvent } from "react";
import { useLocation } from "react-router-dom";
import { errorText } from "../api/errors";
import type { InvestorProfile, Jurisdiction, Portfolio } from "../api/types";
import AppHeader from "../components/AppHeader";
import { listPortfolios } from "../api/endpoints";
import RiskForm, { RiskResult } from "../components/RiskForm";
import { PROVINCES, PROVINCE_LABELS, loadLatestRisk, loadRisk, QUESTIONS, saveRisk, syncRisk, type PortfolioRisk } from "../lib/risk";
import { levelLabel, retainedLevel, VOLATILITY_ASSUMPTION } from "../lib/riskScale";
import IndustryPicker from "../components/IndustryPicker";
import { industryPrefs, splitPreferences } from "../lib/industries";
import { useApp } from "../lib/store";

/* Questionnaire interactif : consultation des réponses enregistrées, modification, résultat par portefeuille. */
function RiskQuestionnaire({ userId }: { userId: string }) {
  const [latest, setLatest] = useState<PortfolioRisk | null>(() => loadLatestRisk(userId));
  const [stored, setStored] = useState<Record<string, PortfolioRisk>>(() => loadRisk(userId));
  const [portfolios, setPortfolios] = useState<Portfolio[] | null>(null);
  const [editing, setEditing] = useState(latest === null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  // Les portefeuilles créés après le dernier questionnaire reçoivent le dernier résultat.
  useEffect(() => {
    listPortfolios()
      .then(({ items }) => { setPortfolios(items); setStored(syncRisk(userId, items.map((p) => p.portfolioId))); })
      .catch(() => setPortfolios([]));
  }, [userId]);

  async function submit(answers: Record<string, number>, province: Jurisdiction) {
    setMsg(""); setErr("");
    setBusy(true);
    try {
      const items = portfolios ?? (await listPortfolios()).items;
      const r = saveRisk(userId, items.map((p) => p.portfolioId), answers, province);
      setLatest(r);
      setStored(loadRisk(userId));
      setEditing(false);
      setMsg(`Réponses enregistrées pour ${items.length} portefeuille(s).`);
    } catch (x) { setErr(errorText(x)); } finally { setBusy(false); }
  }

  const name = (id: string) => portfolios?.find((p) => p.portfolioId === id)?.name ?? id;
  const shown = portfolios ? portfolios.filter((p) => stored[p.portfolioId]).map((p) => p.portfolioId) : Object.keys(stored);

  return (
    <section style={{ marginBottom: 48 }}>
      <h2 className="auth-h" style={{ fontSize: 20, marginBottom: 16 }}>Questionnaire interactif</h2>
      {msg && <div className="banner ok" style={{ marginBottom: 16 }}>{msg}</div>}

      {editing ? (
        <>
          <RiskForm initial={latest?.answers ?? {}} initialProvince={latest?.province ?? ""} submitLabel={busy ? "Enregistrement…" : "Enregistrer mes réponses"} busy={busy} onSubmit={submit}>
            {err && <p className="error" role="alert">{err}</p>}
          </RiskForm>
          {latest && <button type="button" className="link" style={{ marginTop: 12 }} onClick={() => setEditing(false)}>Annuler</button>}
        </>
      ) : latest && (
        <div className="stack">
          <RiskResult answers={latest.answers} province={latest.province} />
          <table className="risk-answers">
            <thead><tr><th>Question</th><th>Votre réponse</th><th>Points</th></tr></thead>
            <tbody>
              {QUESTIONS.map((q, i) => (
                <tr key={q.id}><td>{i + 1}. {q.label}</td><td>{q.options[latest.answers[q.id]]}</td><td>{latest.answers[q.id] + 1} / 5</td></tr>
              ))}
              <tr className="total"><td colSpan={2}>Score total</td><td>{latest.score} / 25</td></tr>
            </tbody>
          </table>
          <p className="muted small">Enregistré le {new Date(latest.computedAt).toLocaleString("fr-CA")}</p>
          <div>
            <h3 className="section-title" style={{ margin: "8px 0" }}>Résultat par portefeuille</h3>
            {shown.length ? (
              <ul className="risk-portfolios">
                {shown.map((id) => (
                  <li key={id}>
                    <span>{name(id)}</span>
                    <strong>
                      {levelLabel(retainedLevel(stored[id].answers.maxLoss + 1, stored[id].answers.capacity + 1), "fr")}
                    </strong>
                    <span className="muted small">score {stored[id].score}/25</span>
                  </li>
                ))}
              </ul>
            ) : <p className="muted small">{portfolios === null ? "Chargement…" : "Votre portefeuille est vide pour le moment."}</p>}
          </div>
          <div><button type="button" className="btn" onClick={() => { setMsg(""); setEditing(true); }}>Modifier mes réponses</button></div>
        </div>
      )}
    </section>
  );
}

const lines = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);

export default function Profile() {
  const { user, saveProfile } = useApp();
  const warning = (useLocation().state as { warning?: string } | null)?.warning;
  const p = user?.investorProfile;
  const [tolerance, setTolerance] = useState(p?.riskTolerance != null ? String(p.riskTolerance) : "");
  const [capacity, setCapacity] = useState(p?.riskCapacity != null ? String(p.riskCapacity) : "");
  const [province, setProvince] = useState<Jurisdiction | "">(p?.province ?? "");
  const [hMin, setHMin] = useState(p ? String(p.horizonMinYears) : "");
  const [hMax, setHMax] = useState(p?.horizonMaxYears != null ? String(p.horizonMaxYears) : "");
  const [objective, setObjective] = useState(p?.objective ?? "");
  const [constraints, setConstraints] = useState((p?.constraints ?? []).join("\n"));
  const initialPrefs = splitPreferences(p?.preferences);
  const [industries, setIndustries] = useState<string[]>(initialPrefs.industries);
  const [preferences, setPreferences] = useState(initialPrefs.others.join("\n"));
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
    const tol = Number(tolerance);
    const cap = Number(capacity);
    if (!Number.isInteger(tol) || tol < 1 || tol > 5) return setErr("La tolérance à la perte est un entier de 1 à 5.");
    if (!Number.isInteger(cap) || cap < 1 || cap > 5) return setErr("La capacité à encaisser une perte est un entier de 1 à 5.");
    const body: InvestorProfile = {
      riskTolerance: tol, riskCapacity: cap, // v0.4.6 : une seule échelle 1 à 5 ; riskLevel n'est plus envoyé
      ...(province ? { province } : {}),
      horizonMinYears: min, ...(max !== undefined ? { horizonMaxYears: max } : {}),
      objective: objective.trim(), constraints: lines(constraints), preferences: [...lines(preferences), ...industryPrefs(industries)], excludedAssetClasses: lines(excluded),
    };
    setErr(""); setBusy(true);
    try { await saveProfile(body); setSaved(true); } catch (x) { setErr(errorText(x)); } finally { setBusy(false); }
  }

  const retained = p?.riskTolerance != null && p?.riskCapacity != null ? retainedLevel(p.riskTolerance, p.riskCapacity) : null;

  return (
    <>
      <AppHeader />
      <main className="wrap" style={{ maxWidth: 760 }}>
        <div className="stock-hero"><div>
          <h1 className="auth-h">Profil investisseur</h1>
          <div className="meta">@{user?.username}{user?.baseCurrency ? ` · devise d'affichage : ${user.baseCurrency}` : ""}</div>
        </div></div>
        {warning && !p && <div className="banner warn" style={{ marginBottom: 20 }}>{warning}</div>}
        {!p && <div className="banner" style={{ background: "var(--ghost)", marginBottom: 20 }}>Profil non rempli : remplissez la tolérance, la capacité, l'horizon et l'objectif pour lancer une analyse.</div>}
        {p && retained === null && (
          <div className="banner warn" style={{ marginBottom: 20 }}>Profil ancien incomplet : la capacité à encaisser une perte manque. Complétez-la ci-dessous : le prochain enregistrement la rendra obligatoire.</div>
        )}
        {saved && <div className="banner ok" style={{ marginBottom: 20 }}>Profil enregistré.</div>}
        {p && (
          <div className="profile-card" style={{ marginBottom: 48 }}>
            <div className="eyebrow">Niveau retenu (R1) : le plus bas de la tolérance et de la capacité</div>
            <div className="big filled" style={{ fontSize: 32 }}>{retained !== null ? levelLabel(retained, "fr") : "À compléter"}</div>
            <p className="desc" style={{ WebkitLineClamp: "unset" }}>
              Tolérance : <strong>{p.riskTolerance != null ? `${p.riskTolerance} / 5` : "à compléter"}</strong> ·
              Capacité : <strong>{p.riskCapacity != null ? `${p.riskCapacity} / 5` : "à compléter"}</strong>
              {p.province ? <> · Province : <strong>{PROVINCE_LABELS[p.province]} ({p.province})</strong></> : null}
              <br /><span className="muted small">{VOLATILITY_ASSUMPTION.fr}</span>
            </p>
          </div>
        )}
        {user && <RiskQuestionnaire userId={user.userId} />}
        <form className="stack" onSubmit={submit} noValidate style={{ paddingBottom: 64 }}>
          <div className="row2">
            <div className="field"><label htmlFor="tol">Tolérance à la perte (1 à 5)</label>
              <select id="tol" className="input" value={tolerance} onChange={(e) => setTolerance(e.target.value)}>
                <option value="">Non renseignée</option>
                {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
              </select></div>
            <div className="field"><label htmlFor="cap">Capacité à encaisser une perte (1 à 5)</label>
              <select id="cap" className="input" value={capacity} onChange={(e) => setCapacity(e.target.value)}>
                <option value="">Non renseignée</option>
                {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
              </select></div>
          </div>
          <div className="field"><label htmlFor="prov">Province ou territoire</label>
            <select id="prov" className="input" value={province} onChange={(e) => setProvince(e.target.value as Jurisdiction | "")}>
              <option value="">Non renseignée</option>
              {PROVINCES.map((pr) => <option key={pr.code} value={pr.code}>{pr.label} ({pr.code})</option>)}
            </select></div>
          <div className="row2">
            <div className="field"><label htmlFor="hmin">Horizon minimum (années)</label><input id="hmin" inputMode="numeric" value={hMin} onChange={(e) => setHMin(e.target.value)} /></div>
            <div className="field"><label htmlFor="hmax">Horizon maximum (facultatif)</label><input id="hmax" inputMode="numeric" value={hMax} onChange={(e) => setHMax(e.target.value)} /></div>
          </div>
          <div className="field"><label htmlFor="obj">Objectif</label><input id="obj" placeholder="ex. croissance à long terme" value={objective} onChange={(e) => setObjective(e.target.value)} /></div>
          <div className="field"><label htmlFor="con">Contraintes (une par ligne)</label><textarea id="con" rows={3} placeholder="ex. diversification minimale" value={constraints} onChange={(e) => setConstraints(e.target.value)} /></div>
          <div className="field"><label htmlFor="pre">Préférences (une par ligne)</label><textarea id="pre" rows={3} placeholder="ex. ESG" value={preferences} onChange={(e) => setPreferences(e.target.value)} /></div>
          <div className="field"><label>Industries qui vous intéressent (plusieurs choix possibles)</label><IndustryPicker value={industries} onChange={setIndustries} /></div>
          <div className="field"><label htmlFor="exc">Classes d'actifs exclues (une par ligne)</label><textarea id="exc" rows={2} placeholder="ex. crypto" value={excluded} onChange={(e) => setExcluded(e.target.value)} /></div>
          {err && <p className="error" role="alert">{err}</p>}
          <div><button className="btn" disabled={busy}>{busy ? "Enregistrement…" : "Enregistrer"}</button></div>
          <p className="muted small">Profil fictif : n'entrez aucune donnée personnelle réelle.</p>
        </form>
      </main>
    </>
  );
}
