import { useT } from "../lib/i18n";
import { INDUSTRIES, type IndustryChoice } from "../lib/industries";
/* Industries en deux sections : ce que le client aime, ce qu'il préfère éviter (facultatif, choix multiple).
 * Cocher une industrie dans une section la retire de l'autre. */
export default function IndustryPicker({ value, onChange }: { value: IndustryChoice; onChange: (v: IndustryChoice) => void }) {
  const { lang, L } = useT();
  const toggle = (side: keyof IndustryChoice, label: string) => {
    const other: keyof IndustryChoice = side === "liked" ? "avoided" : "liked";
    const on = value[side].includes(label);
    onChange({
      [side]: on ? value[side].filter((x) => x !== label) : [...value[side], label],
      [other]: value[other].filter((x) => x !== label),
    } as IndustryChoice);
  };
  const section = (side: keyof IndustryChoice, title: string, hint: string) => (
    <div className={`industry-side ${side}`}>
      <div className="industry-head">
        <strong>{title}</strong>
        <span className="muted small">{value[side].length ? L(`${value[side].length} choisie(s)`, `${value[side].length} selected`) : hint}</span>
      </div>
      <div className="opts">
        {INDUSTRIES.map((i) => (
          <label key={i.label} className={`opt${value[side].includes(i.label) ? " on" : ""}`} title={i.covers}>
            <input type="checkbox" checked={value[side].includes(i.label)} onChange={() => toggle(side, i.label)} />
            {lang === "en" ? i.en : i.label}
          </label>
        ))}
      </div>
    </div>
  );
  return (
    <div className="industry-picker">
      {section("liked", L("Ce que j'aime", "What I like"), L("Aucune pour l'instant", "None yet"))}
      {section("avoided", L("Ce que je préfère éviter", "What I prefer to avoid"), L("Aucune pour l'instant", "None yet"))}
    </div>
  );
}
