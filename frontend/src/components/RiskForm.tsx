import { useState, type FormEvent, type ReactNode } from "react";
import { isComplete, PROVINCES, QUESTIONS, qLabel, qOptions } from "../lib/risk";
import { colon } from "../lib/format";
import { useT } from "../lib/i18n";
import { levelName, levelText, retainedLevel, VOLATILITY_ASSUMPTION } from "../lib/riskScale";
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
  const { lang, L } = useT();
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
        <fieldset key={q.id} className={`q risk-question${tried && answers[q.id] === undefined ? " missing" : ""}`}>
          <legend>{i + 1}. {qLabel(q, lang)}</legend>
          <div className="opts">
            {qOptions(q, lang).map((o, j) => (
              <label key={o} className={`opt${answers[q.id] === j ? " on" : ""}`}>
                <input type="radio" name={q.id} checked={answers[q.id] === j} onChange={() => setAnswers({ ...answers, [q.id]: j })} />
                {o}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      <fieldset className={`q province-question${tried && missingProvince ? " missing" : ""}`}>
        <legend>{QUESTIONS.length + 1}. {L("Province ou territoire de résidence", "Province or territory of residence")}</legend>
        <div className="field province-field">
          <select className="input" value={province} onChange={(e) => setProvince(e.target.value)} aria-label={L("Province ou territoire", "Province or territory")}>
            <option value="">{L("Sélectionner…", "Select…")}</option>
            {PROVINCES.map((p) => <option key={p.code} value={p.code}>{lang === "en" ? p.en : p.label} ({p.code})</option>)}
          </select>
        </div>
        <p className="muted small" style={{ margin: "6px 0 0" }}>{L("Sert à afficher les mentions propres à votre province. Aucune autre donnée personnelle n'est requise.", "Used to show the notices specific to your province. No other personal data is required.")}</p>
      </fieldset>
      {showIndustries && (
        <fieldset className="q preference-question">
          <legend>{QUESTIONS.length + 2}. {L("Industries : ce que vous aimez et ce que vous préférez éviter (facultatif, plusieurs choix possibles)", "Industries: what you like and what you prefer to avoid (optional, several choices possible)")}</legend>
          <IndustryPicker value={industries} onChange={setIndustries} />
        </fieldset>
      )}
      {tried && (!isComplete(answers) || missingProvince) && <p className="error" role="alert">{L("Répondez à toutes les questions, y compris la province.", "Answer every question, including the province.")}</p>}
      {children}
      <div className="questionnaire-actions"><button className="btn" disabled={busy}>{submitLabel}</button></div>
    </form>
  );
}

/** Résultat affiché : niveau retenu en mots (le plus bas de la tolérance et de la capacité, R1), puis le détail. */
export function RiskResult({ answers, province }: { answers: Answers; province?: string }) {
  const { lang, L } = useT();
  const tolerance = answers.maxLoss + 1, capacity = answers.capacity + 1;
  const retained = retainedLevel(tolerance, capacity);
  return (
    <div className="profile-card">
      <div className="eyebrow">{L("Tolérance et capacité de perte", "Loss tolerance and capacity")}</div>
      <div className="profile-top">
        <div className="big filled" style={{ fontSize: 40 }}>{levelName(retained, lang)}</div>
      </div>
      <p className="desc" style={{ WebkitLineClamp: "unset" }}>
        {levelText(retained, lang)}
        <br />
        {L("Tolérance à la perte", "Loss tolerance")}{colon()} <strong>{levelName(tolerance, lang)}</strong> · {L("Capacité à encaisser", "Loss capacity")}{colon()} <strong>{levelName(capacity, lang)}</strong>
        {province ? <> · {L("Province", "Province")}{colon()} <strong>{province}</strong></> : null}
        <br />{L("Niveau retenu (R1) : le plus bas des deux.", "Retained level (R1): the lower of the two.")}
        <br /><span className="muted small">{VOLATILITY_ASSUMPTION[lang]}</span>
      </p>
    </div>
  );
}
