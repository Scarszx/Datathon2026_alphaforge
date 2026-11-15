import { useState, type FormEvent } from "react";
import { OPTIONAL_QUESTIONS, QUESTIONS, computeProfile, isComplete } from "../lib/profile";
import type { Answers } from "../lib/types";

export function ProfileSummary({ answers }: { answers: Answers }) {
  const p = computeProfile(answers);
  return (
    <div className="profile-card">
      <div className="eyebrow">Votre profil préliminaire</div>
      <div className="profile-top">
        <div className="big filled" style={{ fontSize: 40 }}>{p.label}</div>
        <div className="score"><strong>{p.score}</strong><span>/ 100</span></div>
      </div>
      <div className="alloc-bar" style={{ margin: "16px 0" }}><span style={{ width: `${p.score}%`, background: "var(--red)" }} /></div>
      <p className="desc" style={{ WebkitLineClamp: "unset" }}>{p.summary}</p>
    </div>
  );
}

export default function Questionnaire({
  initial = {}, optional = false, submitLabel, onSubmit,
}: { initial?: Answers; optional?: boolean; submitLabel: string; onSubmit: (a: Answers) => void }) {
  const [a, setA] = useState<Answers>(initial);
  const [tried, setTried] = useState(false);
  const done = QUESTIONS.filter((q) => a[q.id]).length;

  function submit(e: FormEvent) {
    e.preventDefault();
    setTried(true);
    if (isComplete(a)) onSubmit(a);
  }

  const block = (q: (typeof QUESTIONS)[number], i?: number) => (
    <fieldset key={q.id} className={`q${tried && !a[q.id] && i !== undefined ? " missing" : ""}`}>
      <legend>{i !== undefined ? `${i + 1}. ` : ""}{q.label}</legend>
      <div className="opts">
        {q.options.map((o) => (
          <label key={o.value} className={a[q.id] === o.value ? "opt on" : "opt"}>
            <input type="radio" name={q.id} value={o.value} checked={a[q.id] === o.value} onChange={() => setA({ ...a, [q.id]: o.value })} />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );

  return (
    <form onSubmit={submit} className="questionnaire">
      <div className="q-progress" aria-live="polite">
        <div className="alloc-bar" style={{ margin: 0, flex: 1, height: 6 }}><span style={{ width: `${(done / QUESTIONS.length) * 100}%`, background: "var(--red)" }} /></div>
        <span className="muted small">{done} / {QUESTIONS.length}</span>
      </div>
      {QUESTIONS.map((q, i) => block(q, i))}
      {optional && <><h3 className="section-title" style={{ margin: "8px 0 0" }}>Contexte financier</h3>{OPTIONAL_QUESTIONS.map((q) => block(q))}</>}
      {tried && !isComplete(a) && <p className="error" role="alert">Veuillez répondre à toutes les questions.</p>}
      <div><button type="submit" className="btn">{submitLabel}</button></div>
    </form>
  );
}
