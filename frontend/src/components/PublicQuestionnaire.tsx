import { useState, type FormEvent } from "react";
import { isPublicComplete, PUBLIC_QUESTIONS, publicProfile, type PublicAnswers } from "../lib/publicProfile";

/* Questionnaire public de la page d'accueil (repris du prototype). */

export function PublicSummary({ answers }: { answers: PublicAnswers }) {
  const p = publicProfile(answers);
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

export default function PublicQuestionnaire({
  initial = {}, submitLabel, onSubmit,
}: { initial?: PublicAnswers; submitLabel: string; onSubmit: (a: PublicAnswers) => void }) {
  const [a, setA] = useState<PublicAnswers>(initial);
  const [tried, setTried] = useState(false);
  const done = PUBLIC_QUESTIONS.filter((q) => a[q.id]).length;

  function submit(e: FormEvent) {
    e.preventDefault();
    setTried(true);
    if (isPublicComplete(a)) onSubmit(a);
  }

  return (
    <form onSubmit={submit} className="questionnaire" noValidate>
      <div className="q-progress" aria-live="polite">
        <div className="alloc-bar" style={{ margin: 0, flex: 1, height: 6 }}><span style={{ width: `${(done / PUBLIC_QUESTIONS.length) * 100}%`, background: "var(--red)" }} /></div>
        <span className="muted small">{done} / {PUBLIC_QUESTIONS.length}</span>
      </div>
      {PUBLIC_QUESTIONS.map((q, i) => (
        <fieldset key={q.id} className={`q${tried && !a[q.id] ? " missing" : ""}`}>
          <legend>{i + 1}. {q.label}</legend>
          <div className="opts">
            {q.options.map((o) => (
              <label key={o.value} className={a[q.id] === o.value ? "opt on" : "opt"}>
                <input type="radio" name={`pub-${q.id}`} value={o.value} checked={a[q.id] === o.value} onChange={() => setA({ ...a, [q.id]: o.value })} />
                {o.label}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      {tried && !isPublicComplete(a) && <p className="error" role="alert">Veuillez répondre à toutes les questions.</p>}
      <div><button type="submit" className="btn">{submitLabel}</button></div>
    </form>
  );
}
