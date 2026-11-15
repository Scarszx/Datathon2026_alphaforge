import { INDUSTRIES } from "../lib/industries";
/* Choix multiple d'industries (facultatif). */
export default function IndustryPicker({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const toggle = (l: string) => onChange(value.includes(l) ? value.filter((x) => x !== l) : [...value, l]);
  return (
    <div className="opts">
      {INDUSTRIES.map((i) => (
        <label key={i.label} className={`opt${value.includes(i.label) ? " on" : ""}`} title={i.covers}>
          <input type="checkbox" checked={value.includes(i.label)} onChange={() => toggle(i.label)} />
          {i.label}
        </label>
      ))}
    </div>
  );
}
