import { useState, type FormEvent, type ReactNode } from "react";
import { isComplete, PROVINCES, QUESTIONS, riskCalc, riskLevelOf, RISK_LABELS, SCORE_MAX, SCORE_MIN, totalScore } from "../lib/risk";
import type { Jurisdiction } from "../api/types";

type Answers = Record<string, number>;

/**
 * Questionnaire de risque (lib/risk.ts) + province (v0.4.0 : filtre de la Knowledge Base, mentions R9).
 * N'enregistre rien : `onSubmit` reçoit les réponses complètes et la province choisie.
 */
export default function RiskForm({
  initial = {}, initialProvince = "", submitLabel, busy = false, onSubmit, children,
}: {
  initial?: Answers; initialProvince?: string; submitLabel: string; busy?: boolean;
  onSubmit: (a: Answers, province: Jurisdiction) => void; children?: ReactNode;
}) {
  const [answers, setAnswers] = useState<Answers>(initial);
  const [province, setProvince] = useState(initialProvince);
  const [tried, setTried] = useState(false);
  const done = QUESTIONS.filter((q) => answers[q.id] !== undefined).length;
  const missingProvince = !PROVINCES.some((p) => p.code === province);

  function submit(e: FormEvent) {
    e.preventDefault();
    setTried(true);
    if (isComplete(answers) && !missingProvince) onSubmit(answers, province as Jurisdiction);
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
      {tried && (!isComplete(answers) || missingProvince) && <p className="error" role="alert">Répondez à toutes les questions, y compris la province.</p>}
      {children}
      <div><button className="btn" disabled={busy}>{submitLabel}</button></div>
    </form>
  );
}

/** Résultat affiché : score, niveau de risque du contrat, tolérance/capacité séparées et province (R1). */
export function RiskResult({ answers, province }: { answers: Answers; province?: string }) {
  const score = totalScore(answers);
  const fill = ((score - SCORE_MIN) / (SCORE_MAX - SCORE_MIN)) * 100;
  return (
    <div className="profile-card">
      <div className="eyebrow">Votre tolérance au risque</div>
      <div className="profile-top">
        <div className="big filled" style={{ fontSize: 40 }}>{RISK_LABELS[riskLevelOf(score)]}</div>
        <div className="score"><strong>{score}</strong><span>/ {SCORE_MAX}</span></div>
      </div>
      <div className="alloc-bar" style={{ margin: "16px 0" }}><span style={{ width: `${fill}%`, background: "var(--red)" }} /></div>
      <p className="desc" style={{ WebkitLineClamp: "unset" }}>
        Tolérance à la perte : <strong>{answers.maxLoss + 1} / 5</strong> · Capacité à encaisser : <strong>{answers.capacity + 1} / 5</strong>
        {province ? <> · Province : <strong>{province}</strong></> : null}
        <br />Résultat du calcul : <strong>{riskCalc(score).toFixed(2)}</strong> (10 = très prudent, 1 = très tolérant au risque).
      </p>
    </div>
  );
}
