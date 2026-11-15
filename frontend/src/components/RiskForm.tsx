import { useState, type FormEvent, type ReactNode } from "react";
import { isComplete, PROVINCES, QUESTIONS, totalScore, SCORE_MAX, type ProfileChoices } from "../lib/risk";
import { levelLabel, retainedLevel, VOLATILITY_ASSUMPTION } from "../lib/riskScale";
import type { Jurisdiction } from "../api/types";
import IndustryPicker from "./IndustryPicker";
import { EMPTY_INDUSTRIES, type IndustryChoice } from "../lib/industries";
import { ESG_ANSWERS, MARKETS, toggleMarket, type Market } from "../lib/esgMarket";

type Answers = Record<string, number>;

/**
 * Questionnaire de risque (lib/risk.ts) + province (v0.4.0 : filtre de la Knowledge Base, mentions R9).
 * Avec `showPreferences` (création du portefeuille) : critères ESG et marché géographique, obligatoires
 * (lib/esgMarket.ts), puis industries, facultatives. Ces questions ne comptent pas dans le score.
 * N'enregistre rien : `onSubmit` reçoit les réponses complètes, la province choisie et ces choix.
 */
export default function RiskForm({
  initial = {}, initialProvince = "", showPreferences = false, submitLabel, busy = false, onSubmit, children,
}: {
  initial?: Answers; initialProvince?: string; showPreferences?: boolean; submitLabel: string; busy?: boolean;
  onSubmit: (a: Answers, province: Jurisdiction, choices: ProfileChoices) => void; children?: ReactNode;
}) {
  const [answers, setAnswers] = useState<Answers>(initial);
  const [province, setProvince] = useState(initialProvince);
  const [esg, setEsg] = useState<boolean | undefined>(undefined);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [industries, setIndustries] = useState<IndustryChoice>(EMPTY_INDUSTRIES);
  const [tried, setTried] = useState(false);
  const missingProvince = !PROVINCES.some((p) => p.code === province);
  const missingEsg = showPreferences && esg === undefined;
  const missingMarket = showPreferences && markets.length === 0;
  // Progression : toutes les questions obligatoires (risque, province, et ESG + marché à la création).
  const required = [
    ...QUESTIONS.map((q) => answers[q.id] !== undefined),
    !missingProvince,
    ...(showPreferences ? [!missingEsg, !missingMarket] : []),
  ];
  const done = required.filter(Boolean).length;

  function submit(e: FormEvent) {
    e.preventDefault();
    setTried(true);
    if (isComplete(answers) && !missingProvince && !missingEsg && !missingMarket)
      onSubmit(answers, province as Jurisdiction, { esg: esg === true, markets, industries });
  }

  return (
    <form className="questionnaire" onSubmit={submit} noValidate>
      <div className="q-progress" aria-live="polite">
        <div className="alloc-bar" style={{ margin: 0, flex: 1, height: 6 }}><span style={{ width: `${(done / required.length) * 100}%`, background: "var(--red)" }} /></div>
        <span className="muted small">{done} / {required.length}</span>
      </div>
      {QUESTIONS.map((q, i) => (
        <fieldset key={q.id} className={`q risk-question${tried && answers[q.id] === undefined ? " missing" : ""}`}>
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
      <fieldset className={`q province-question${tried && missingProvince ? " missing" : ""}`}>
        <legend>{QUESTIONS.length + 1}. Province ou territoire de résidence</legend>
        <div className="field province-field">
          <select className="input" value={province} onChange={(e) => setProvince(e.target.value)} aria-label="Province ou territoire">
            <option value="">Sélectionner…</option>
            {PROVINCES.map((p) => <option key={p.code} value={p.code}>{p.label} ({p.code})</option>)}
          </select>
        </div>
        <p className="muted small" style={{ margin: "6px 0 0" }}>Sert à afficher les mentions propres à votre province. Aucune autre donnée personnelle n'est requise.</p>
      </fieldset>
      {showPreferences && (
        <>
          <fieldset className={`q choice-question${tried && missingEsg ? " missing" : ""}`}>
            <legend>{QUESTIONS.length + 2}. Critères ESG (environnementaux, sociaux et de gouvernance) : voulez-vous en tenir compte dans vos simulations ?</legend>
            <div className="opts">
              {ESG_ANSWERS.map((o) => (
                <label key={o.label} className={`opt${esg === o.value ? " on" : ""}`}>
                  <input type="radio" name="esg" checked={esg === o.value} onChange={() => setEsg(o.value)} />
                  {o.label}
                </label>
              ))}
            </div>
            <p className="muted small" style={{ margin: "10px 0 0" }}>Si oui, la règle R8 signale dans vos simulations les titres sans méthode ESG publiée par l'émetteur. L'outil n'attribue aucune note ESG.</p>
          </fieldset>
          <fieldset className={`q choice-question${tried && missingMarket ? " missing" : ""}`}>
            <legend>{QUESTIONS.length + 3}. Marché géographique : où voulez-vous investir ? (plusieurs choix possibles)</legend>
            <div className="opts">
              {MARKETS.map((m) => (
                <label key={m} className={`opt${markets.includes(m) ? " on" : ""}`}>
                  <input type="checkbox" checked={markets.includes(m)} onChange={() => setMarkets(toggleMarket(markets, m))} />
                  {m}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset className="q preference-question">
            <legend>{QUESTIONS.length + 4}. Industries : ce que vous aimez et ce que vous préférez éviter (facultatif, plusieurs choix possibles)</legend>
            <IndustryPicker value={industries} onChange={setIndustries} />
          </fieldset>
        </>
      )}
      {tried && (!isComplete(answers) || missingProvince || missingEsg || missingMarket) && <p className="error" role="alert">Répondez à toutes les questions, y compris la province.</p>}
      {children}
      <div className="questionnaire-actions"><button className="btn" disabled={busy}>{submitLabel}</button></div>
    </form>
  );
}

/** Résultat affiché : tolérance (1 à 5), capacité (1 à 5) et niveau retenu = le plus bas des deux (R1). */
export function RiskResult({ answers, province }: { answers: Answers; province?: string }) {
  const score = totalScore(answers);
  const tolerance = answers.maxLoss + 1, capacity = answers.capacity + 1;
  const retained = retainedLevel(tolerance, capacity);
  return (
    <div className="profile-card">
      <div className="eyebrow">Tolérance et capacité de perte</div>
      <div className="profile-top">
        <div className="big filled" style={{ fontSize: 40 }}>{levelLabel(retained, "fr")}</div>
        <div className="score"><strong>{score}</strong><span>/ {SCORE_MAX}</span></div>
      </div>
      <p className="desc" style={{ WebkitLineClamp: "unset" }}>
        Tolérance à la perte : <strong>{tolerance} / 5</strong> · Capacité à encaisser : <strong>{capacity} / 5</strong>
        {province ? <> · Province : <strong>{province}</strong></> : null}
        <br />Niveau retenu (R1) : <strong>{retained} / 5</strong> — le plus bas des deux.
        <br /><span className="muted small">{VOLATILITY_ASSUMPTION.fr}</span>
      </p>
    </div>
  );
}
