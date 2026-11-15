/* Lecture CSV minimale (guillemets, virgules internes) et séries temporelles. */

export type SeriesPoint = { date: string; value: number };
export type Series = { id: string; label: string; unit: string; frequency: string; source: string; points: SeriesPoint[] };

function splitLine(line: string): string[] {
  const out: string[] = [];
  let cur = "", q = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (q) {
      if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (c === '"') q = false;
      else cur += c;
    } else if (c === '"') q = true;
    else if (c === ",") { out.push(cur); cur = ""; }
    else cur += c;
  }
  out.push(cur);
  return out;
}

export function parseCsv(text: string): Record<string, string>[] {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) return [];
  const head = splitLine(lines[0]).map((h) => h.trim());
  return lines.slice(1).map((l) => {
    const c = splitLine(l);
    return Object.fromEntries(head.map((h, i) => [h, (c[i] ?? "").trim()]));
  });
}

/** Accepte le format long (date,series_id,value,...) ou le format FX (date,usdcad,cadusd). */
export function toSeries(rows: Record<string, string>[]): Series[] {
  const map = new Map<string, Series>();
  const add = (id: string, meta: Omit<Series, "id" | "points">, date: string, v: number) => {
    if (!date || !Number.isFinite(v)) return;
    let s = map.get(id);
    if (!s) map.set(id, (s = { id, ...meta, points: [] }));
    s.points.push({ date, value: v });
  };
  for (const r of rows) {
    if ("series_id" in r) {
      add(r.series_id, { label: r.label || r.series_id, unit: r.unit, frequency: r.frequency, source: r.source }, r.date, Number(r.value));
    } else {
      for (const k of Object.keys(r)) {
        if (k === "date") continue;
        add(k.toUpperCase(), { label: `Taux de change ${k.toUpperCase()}`, unit: "taux", frequency: "daily", source: "" }, r.date, Number(r[k]));
      }
    }
  }
  const all = [...map.values()];
  for (const s of all) s.points.sort((a, b) => (a.date < b.date ? -1 : 1));
  return all;
}

export function toCsv(s: Series, pts: SeriesPoint[]): string {
  return ["date,series_id,value,unit", ...pts.map((p) => `${p.date},${s.id},${p.value},${s.unit}`)].join("\n");
}
