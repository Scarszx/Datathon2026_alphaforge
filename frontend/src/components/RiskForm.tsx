import { useState, type FormEvent, type ReactNode } from "react";
import { isComplete, PROVINCES, QUESTIONS, totalScore, SCORE_MAX } from "../lib/risk";
import { levelLabel, retainedLevel, VOLATILITY_ASSUMPTION } from "../lib/riskScale";
import type { Jurisdiction } from "../api/types";
import IndustryPicker from "./IndustryPicker";
import { EMPTY_INDUSTRIES, type IndustryChoice } from "../lib/industries";

type Answers = Record<string, number>;

/**
 * Questionnaire de risque (lib/risk.ts) + province (v0.4.0 : filtre de la Knowledge Base, mentions R9).
 * N'enregistre rien : `onSubmit` reçoit les réponses complètes et la province choisie.
 */
export default function RiskForm({
  initial = {}, initialProvince = "", showIndustries = false, submitLabel, busy = false, onSubmit, children,
}: {
  initial?: Answers; initialProvince?: string; showIndustries?: boolean; submitLabel: string; busy?: boolean;
  onSubmit: (a: Answers, province: Jurisdiction, industries: IndustryChoice) => void; children?: ReactNode;
}) {
  const [answers, setAnswers] = useState<Answers>(initial);
  const [province, setProvince] = useState(initialProvince);
  const [industries, setIndustries] = useState<IndustryChoice>(EMPTY_INDUSTRIES);
  const [tried, setTried] = useState(false);
  const done = QUESTIONS.filter((q) => answers[q.id] !== undefined).length;
  const missingProvince = !PROVINCES.some((p) => p.code === province);

  function submit(e: FormEvent) {
    e.preventDefault();
    setTried(true);
    if (isComplete(answers) && !missingProvince) onSubmit(answers, province as Jurisdiction, industries);
  }

  return (
    <form className="questionnaire" onSubmit={submit} noValidate>
      <div className="q-progress" aria-live="polite">
        <div className="alloc-bar" style={{ margin: 0, flex: 1, height: 6 }}><span style={{ width: `${(done / QUESTIONS.length) * 100}%`, background: "var(--red)" }} /></div>
        <span className="muted small">{done} / {QUESTIONS.length}</span>
      </div>
      {QUESTIONS.map((q, i) => (
        <fieldset key={q.id} className={`q${tried && answers[q.id] === undefined ? " missing" : ""}`}>
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
      <fieldset className={`q${tried && missingProvince ? " missing" : ""}`}>
        <legend>{QUESTIONS.length + 1}. Province ou territoire de résidence</legend>
        <div className="field" style={{ maxWidth: 320 }}>
          <select className="input" value={province} onChange={(e) => setProvince(e.target.value)} aria-label="Province ou territoire">
            <option value="">Sélectionner…</option>
            {PROVINCES.map((p) => <option key={p.code} value={p.code}>{p.label} ({p.code})</option>)}
          </select>
        </div>
        <p className="muted small" style={{ margin: "6px 0 0" }}>Sert à afficher les mentions propres à votre province. Aucune autre donnée personnelle n'est requise.</p>
      </fieldset>
      {showIndustries && (
        <fieldset className="q">
          <legend>{QUESTIONS.length + 2}. Industries : ce que vous aimez et ce que vous préférez éviter (facultatif, plusieurs choix possibles)</legend>
          <IndustryPicker value={industries} onChange={setIndustries} />
        </fieldset>
      )}
      {tried && (!isComplete(answers) || missingProvince) && <p className="error" role="alert">Répondez à toutes les questions, y compris la province.</p>}
      {children}
      <div><button className="btn" disabled={busy}>{submitLabel}</button></div>
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
