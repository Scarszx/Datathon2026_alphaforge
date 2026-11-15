import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import { errorText } from "../api/errors";
import type { InvestorProfile, Jurisdiction, Portfolio, PortfolioSummary } from "../api/types";
import AppHeader from "../components/AppHeader";
import { getSummary, listPortfolios } from "../api/endpoints";
import RiskForm, { RiskResult } from "../components/RiskForm";
import { PROVINCES, PROVINCE_LABELS, loadLatestRisk, loadRisk, QUESTIONS, saveRisk, syncRisk, type PortfolioRisk } from "../lib/risk";
import { levelLabel, retainedLevel, VOLATILITY_ASSUMPTION } from "../lib/riskScale";
import IndustryPicker from "../components/IndustryPicker";
import { industryPrefs, splitPreferences, type IndustryChoice } from "../lib/industries";
import { useApp } from "../lib/store";
import { cad, pct, plainPct } from "../lib/format";

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
/** Jauge 1 à 5 en segments (tolérance, capacité). */
function Meter({ value }: { value: number | null | undefined }) {
  return (
    <div className="meter" aria-label={value != null ? `${value} sur 5` : "non renseigné"}>
      {[1, 2, 3, 4, 5].map((n) => <span key={n} className={value != null && n <= value ? "on" : ""} />)}
    </div>
  );
}
function Chips({ items, tone, empty }: { items: string[]; tone?: "like" | "avoid"; empty: string }) {
  if (!items.length) return <p className="muted small">{empty}</p>;
  return <div className="chips">{items.map((x) => <span key={x} className={`chip ${tone ?? ""}`}>{x}</span>)}</div>;
}
function horizonText(p: InvestorProfile) {
  if (p.horizonMaxYears != null) return p.horizonMinYears === p.horizonMaxYears ? `${p.horizonMinYears} ans` : `${p.horizonMinYears} à ${p.horizonMaxYears} ans`;
  return `${p.horizonMinYears} ans et plus`;
}
/** Carte portefeuille : valeur, variation, risque et répartition lus dans le résumé du back (GET summary). */
function PortfolioCard() {
  const [state, setState] = useState<{ summary: PortfolioSummary | null; name?: string; loading: boolean }>({ summary: null, loading: true });
  useEffect(() => {
    listPortfolios()
      .then(async ({ items }) => {
        const main = items[0];
        if (!main || !main.holdings.length) return setState({ summary: null, name: main?.name, loading: false });
        const summary = await getSummary(main.portfolioId, "1y");
        setState({ summary, name: main.name, loading: false });
      })
      .catch(() => setState({ summary: null, loading: false }));
  }, []);
  const s = state.summary;
  return (
    <div className="dcard span2">
      <div className="dcard-head">
        <div><div className="dcard-title">Mon portefeuille</div><div className="muted small">{state.name ?? "Portefeuille principal"}{s ? ` · au ${s.asOf.slice(0, 10)}` : ""}</div></div>
        <Link to="/portefeuille" className="dcard-arrow" aria-label="Ouvrir le portefeuille">↗</Link>
      </div>
      {state.loading ? <p className="muted small">Chargement…</p> : !s ? (
        <p className="muted small">Aucune position pour l'instant. <Link to="/portefeuille" className="link">Ajouter des positions</Link></p>
      ) : (
        <div className="pf-grid">
          <div>
            <div className="dcard-value">{cad(s.totals.value, 0)}</div>
            <span className={`pill ${s.totals.pnlPct >= 0 ? "up" : "down"}`}>{pct(s.totals.pnlPct)}</span>
            <span className="muted small"> depuis l'achat</span>
            <div className="pf-risk">
              <div><span className="muted small">Volatilité annualisée</span><strong>{plainPct(s.risk.volatility)}</strong></div>
              <div><span className="muted small">Pire baisse</span><strong>{plainPct(s.risk.maxDrawdown)}</strong></div>
              <div><span className="muted small">Positions</span><strong>{s.holdings.length}</strong></div>
            </div>
          </div>
          <div>
            <div className="muted small" style={{ marginBottom: 6 }}>Répartition par classe d'actifs</div>
            {s.allocation.byAssetClass.slice(0, 5).map((a) => (
              <div key={a.label} className="pf-bar">
                <span className="small">{a.label}</span>
                <div className="alloc-bar"><span style={{ width: `${Math.min(100, a.weight)}%` }} /></div>
                <span className="small muted">{a.weight.toFixed(1)} %</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <p className="muted small" style={{ marginTop: 10 }}>Données passées : elles ne prédisent pas les rendements futurs.</p>
    </div>
  );
}
export default function Profile() {
  const { user, saveProfile } = useApp();
  const warning = (useLocation().state as { warning?: string } | null)?.warning;
  const p = user?.investorProfile;
  const [editing, setEditing] = useState(!p);
  const [tolerance, setTolerance] = useState(p?.riskTolerance != null ? String(p.riskTolerance) : "");
  const [capacity, setCapacity] = useState(p?.riskCapacity != null ? String(p.riskCapacity) : "");
  const [province, setProvince] = useState<Jurisdiction | "">(p?.province ?? "");
  const [hMin, setHMin] = useState(p ? String(p.horizonMinYears) : "");
  const [hMax, setHMax] = useState(p?.horizonMaxYears != null ? String(p.horizonMaxYears) : "");
  const [objective, setObjective] = useState(p?.objective ?? "");
  const [constraints, setConstraints] = useState((p?.constraints ?? []).join("\n"));
  const initialPrefs = splitPreferences(p?.preferences);
  const [industries, setIndustries] = useState<IndustryChoice>({ liked: initialPrefs.liked, avoided: initialPrefs.avoided });
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
    try { await saveProfile(body); setSaved(true); setEditing(false); } catch (x) { setErr(errorText(x)); } finally { setBusy(false); }
  }
  const retained = p?.riskTolerance != null && p?.riskCapacity != null ? retainedLevel(p.riskTolerance, p.riskCapacity) : null;
  const prefs = splitPreferences(p?.preferences);
  const name = (user?.displayName ?? user?.username ?? "").split(" ")[0];
  const today = new Date().toLocaleDateString("fr-CA", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
  return (
    <>
      <AppHeader />
      <main className="wrap dash">
        <div className="dash-hero">
          <div>
            <h1 className="dash-title">Bon retour, <span className="muted-name">{name}</span></h1>
            <p className="muted">Votre profil d'investisseur, tel que l'outil l'utilise pour cadrer vos simulations. Profil fictif : aucune donnée personnelle réelle.</p>
          </div>
          <div className="dash-actions">
            <span className="date-chip">📅 {today}</span>
            <button type="button" className="btn" onClick={() => { setSaved(false); setEditing((v) => !v); }}>
              {editing ? "Fermer la modification" : "Modifier mon profil"}
            </button>
          </div>
        </div>
        {warning && !p && <div className="banner warn" style={{ marginBottom: 16 }}>{warning}</div>}
        {!p && <div className="banner" style={{ background: "var(--ghost)", marginBottom: 16 }}>Profil non rempli : remplissez la tolérance, la capacité, l'horizon et l'objectif pour lancer une analyse.</div>}
        {p && retained === null && (
          <div className="banner warn" style={{ marginBottom: 16 }}>Profil ancien incomplet : la capacité à encaisser une perte manque. Complétez-la dans « Modifier mon profil ».</div>
        )}
        {saved && <div className="banner ok" style={{ marginBottom: 16 }}>Profil enregistré.</div>}

        {p && (
          <div className="dash-grid">
            <div className="dcard green">
              <div className="dcard-head">
                <div><div className="dcard-title">Niveau retenu</div><div className="small" style={{ opacity: .8 }}>Règle R1 : le plus bas de la tolérance et de la capacité</div></div>
              </div>
              <div className="green-inner">
                <div className="small" style={{ opacity: .8 }}>Profil de risque</div>
                <div className="green-value">{retained !== null ? levelLabel(retained, "fr") : "À compléter"}</div>
                <div className="green-foot">
                  <span>{p.province ? `${PROVINCE_LABELS[p.province]} (${p.province})` : "Province non renseignée"}</span>
                  <span>{retained !== null ? `${retained} / 5` : ""}</span>
                </div>
              </div>
            </div>
            <div className="dcard">
              <div className="dcard-head"><div><div className="dcard-title">Tolérance et capacité</div><div className="muted small">Échelle de 1 à 5</div></div></div>
              <div className="meter-row"><span className="small">Tolérance à la perte</span><strong>{p.riskTolerance ?? "—"} / 5</strong></div>
              <Meter value={p.riskTolerance} />
              <p className="muted small" style={{ margin: "4px 0 12px" }}>Ce que vous acceptez de subir.</p>
              <div className="meter-row"><span className="small">Capacité à encaisser</span><strong>{p.riskCapacity ?? "—"} / 5</strong></div>
              <Meter value={p.riskCapacity} />
              <p className="muted small" style={{ marginTop: 4 }}>Ce que vos finances peuvent absorber.</p>
            </div>
            <div className="dcard">
              <div className="dcard-head"><div><div className="dcard-title">Objectif et horizon</div><div className="muted small">Cadrent chaque session</div></div></div>
              <div className="muted small">Objectif</div>
              <div className="dcard-value sm">{p.objective}</div>
              <div className="muted small" style={{ marginTop: 14 }}>Horizon de placement</div>
              <div className="dcard-value sm">{horizonText(p)}</div>
              <p className="muted small" style={{ marginTop: 12 }}>{VOLATILITY_ASSUMPTION.fr}</p>
            </div>

            <PortfolioCard />
            <div className="dcard">
              <div className="dcard-head"><div><div className="dcard-title">Contraintes et exclusions</div><div className="muted small">Respectées par les règles</div></div></div>
              <div className="muted small">Contraintes</div>
              <Chips items={p.constraints ?? []} empty="Aucune contrainte." />
              <div className="muted small" style={{ marginTop: 12 }}>Classes d'actifs exclues</div>
              <Chips items={p.excludedAssetClasses ?? []} tone="avoid" empty="Aucune exclusion." />
              {prefs.others.length > 0 && (<><div className="muted small" style={{ marginTop: 12 }}>Autres préférences</div><Chips items={prefs.others} empty="" /></>)}
            </div>

            <div className="dcard span-half">
              <div className="dcard-head"><div><div className="dcard-title">👍 Ce que j'aime</div><div className="muted small">Industries qui vous intéressent</div></div></div>
              <Chips items={prefs.liked} tone="like" empty="Aucune industrie choisie. Ajoutez-en dans « Modifier mon profil »." />
            </div>
            <div className="dcard span-half">
              <div className="dcard-head"><div><div className="dcard-title">👎 Ce que je préfère éviter</div><div className="muted small">Industries à écarter</div></div></div>
              <Chips items={prefs.avoided} tone="avoid" empty="Aucune industrie à éviter." />
            </div>
          </div>
        )}

        {editing && (
          <div className="dcard" style={{ marginTop: 16 }} id="modifier">
            <div className="dcard-head"><div><div className="dcard-title">Modifier mon profil</div><div className="muted small">Les changements s'appliquent aux prochaines sessions</div></div></div>
            <form className="stack" onSubmit={submit} noValidate>
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
              <div className="field"><label>Industries</label><IndustryPicker value={industries} onChange={setIndustries} /></div>
              <div className="row2">
                <div className="field"><label htmlFor="con">Contraintes (une par ligne)</label><textarea id="con" rows={3} placeholder="ex. diversification minimale" value={constraints} onChange={(e) => setConstraints(e.target.value)} /></div>
                <div className="field"><label htmlFor="exc">Classes d'actifs exclues (une par ligne)</label><textarea id="exc" rows={3} placeholder="ex. crypto" value={excluded} onChange={(e) => setExcluded(e.target.value)} /></div>
              </div>
              <div className="field"><label htmlFor="pre">Autres préférences (une par ligne)</label><textarea id="pre" rows={2} placeholder="ex. ESG" value={preferences} onChange={(e) => setPreferences(e.target.value)} /></div>
              {err && <p className="error" role="alert">{err}</p>}
              <div><button className="btn" disabled={busy}>{busy ? "Enregistrement…" : "Enregistrer"}</button></div>
            </form>
          </div>
        )}

        {user && <div className="dcard" style={{ margin: "16px 0 64px" }}><RiskQuestionnaire userId={user.userId} /></div>}
      </main>
    </>
  );
}
