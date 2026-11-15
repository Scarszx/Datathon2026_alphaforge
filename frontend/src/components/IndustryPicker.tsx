import { INDUSTRIES, type IndustryChoice } from "../lib/industries";
/* Industries en deux sections : ce que le client aime, ce qu'il préfère éviter (facultatif, choix multiple).
 * Cocher une industrie dans une section la retire de l'autre. */
export default function IndustryPicker({ value, onChange }: { value: IndustryChoice; onChange: (v: IndustryChoice) => void }) {
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
        <span className="muted small">{value[side].length ? `${value[side].length} choisie(s)` : hint}</span>
      </div>
      <div className="opts">
        {INDUSTRIES.map((i) => (
          <label key={i.label} className={`opt${value[side].includes(i.label) ? " on" : ""}`} title={i.covers}>
            <input type="checkbox" checked={value[side].includes(i.label)} onChange={() => toggle(side, i.label)} />
            {i.label}
          </label>
        ))}
      </div>
    </div>
  );
  return (
    <div className="industry-picker">
      {section("liked", "Ce que j'aime", "Aucune pour l'instant")}
      {section("avoided", "Ce que je préfère éviter", "Aucune pour l'instant")}
    </div>
  );
}
