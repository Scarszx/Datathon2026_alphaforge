import { useState } from "react";
import { fullDate } from "../lib/format";

export type Line = { label: string; values: number[]; color: string; dash?: string; width?: number };

/** Graphique multi-courbes (indicateurs superposés). NaN = trou dans la courbe. */
export default function MultiChart({ lines, timestamps, format, axisLabel, guides = [], height = 300 }: {
  lines: Line[]; timestamps: number[]; format: (v: number) => string; axisLabel: (ts: number) => string;
  guides?: number[]; height?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const n = timestamps.length;
  const fin = [...lines.flatMap((l) => l.values), ...guides].filter(Number.isFinite);
  const min = Math.min(...fin), max = Math.max(...fin);
  const pad = (max - min) * 0.08 || 1;
  const lo = min - pad, hi = max + pad;
  const xp = (i: number) => (n > 1 ? (i / (n - 1)) * 100 : 50);
  const yp = (v: number) => 100 - ((v - lo) / (hi - lo)) * 100;
  const path = (vals: number[]) => {
    let d = "", pen = false;
    vals.forEach((v, i) => {
      if (!Number.isFinite(v)) { pen = false; return; }
      d += `${pen ? "L" : "M"}${(xp(i) * 10).toFixed(1)} ${(yp(v) * 3).toFixed(1)}`;
      pen = true;
    });
    return d;
  };
  const labels = [0, 0.33, 0.66, 1].map((f) => timestamps[Math.round(f * (n - 1))]);

  return (
    <>
      <div
        className="plot"
        style={{ height }}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          setHover(Math.max(0, Math.min(n - 1, Math.round(((e.clientX - r.left) / r.width) * (n - 1)))));
        }}
        onMouseLeave={() => setHover(null)}
      >
        <svg viewBox="0 0 1000 300" preserveAspectRatio="none" aria-hidden="true">
          {guides.map((g) => <line key={g} x1="0" x2="1000" y1={yp(g) * 3} y2={yp(g) * 3} stroke="#c4c8cf" strokeDasharray="4 6" vectorEffect="non-scaling-stroke" />)}
          {lines.map((l) => <path key={l.label} d={path(l.values)} fill="none" stroke={l.color} strokeWidth={l.width ?? 1.75} strokeDasharray={l.dash} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />)}
        </svg>
        {hover !== null && (
          <>
            <div className="crosshair" style={{ left: `${xp(hover)}%` }} />
            <div className="tooltip" style={{ left: `${xp(hover)}%`, transform: `translateX(${xp(hover) > 75 ? "-100%" : xp(hover) < 25 ? "0" : "-50%"})` }}>
              {lines.map((l) => <div key={l.label}><span style={{ color: l.color }}>● </span>{l.label} : <strong>{Number.isFinite(l.values[hover]) ? format(l.values[hover]) : "—"}</strong></div>)}
              <span>{fullDate(timestamps[hover])}</span>
            </div>
          </>
        )}
      </div>
      <div className="axis">{labels.map((t, i) => <span key={i}>{axisLabel(t)}</span>)}</div>
      <ul className="legend" style={{ marginTop: 8 }}>{lines.map((l) => <li key={l.label}><span className="dot" style={{ background: l.color }} />{l.label}</li>)}</ul>
    </>
  );
}
