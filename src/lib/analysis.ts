/* Indicateurs d'analyse technique et séries dérivées (macro). Tableaux alignés : NaN = indisponible. */
import type { Series, SeriesPoint } from "./csv";

export const sma = (v: number[], n: number) =>
  v.map((_, i) => (i + 1 < n ? NaN : v.slice(i + 1 - n, i + 1).reduce((a, b) => a + b, 0) / n));

export function ema(v: number[], n: number) {
  const k = 2 / (n + 1);
  const out: number[] = [];
  v.forEach((x, i) => out.push(i === 0 ? x : x * k + out[i - 1] * (1 - k)));
  return out.map((x, i) => (i + 1 < n ? NaN : x));
}

/** RSI de Wilder */
export function rsi(v: number[], n = 14) {
  const out = v.map(() => NaN);
  if (v.length <= n) return out;
  let g = 0, l = 0;
  for (let i = 1; i <= n; i++) { const d = v[i] - v[i - 1]; if (d >= 0) g += d; else l -= d; }
  g /= n; l /= n;
  out[n] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
  for (let i = n + 1; i < v.length; i++) {
    const d = v[i] - v[i - 1];
    g = (g * (n - 1) + Math.max(d, 0)) / n;
    l = (l * (n - 1) + Math.max(-d, 0)) / n;
    out[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
  }
  return out;
}

export function bollinger(v: number[], n = 20, k = 2) {
  const mid = sma(v, n);
  const sd = v.map((_, i) => {
    if (i + 1 < n) return NaN;
    const w = v.slice(i + 1 - n, i + 1), m = mid[i];
    return Math.sqrt(w.reduce((a, b) => a + (b - m) ** 2, 0) / n);
  });
  return { mid, upper: mid.map((m, i) => m + k * sd[i]), lower: mid.map((m, i) => m - k * sd[i]) };
}

export function macd(v: number[], fast = 12, slow = 26, sig = 9) {
  const f = ema(v, fast), s = ema(v, slow);
  const line = v.map((_, i) => f[i] - s[i]);
  const valid = line.map((x) => (Number.isFinite(x) ? x : 0));
  const signal = ema(valid, sig).map((x, i) => (Number.isFinite(line[i]) ? x : NaN));
  return { line, signal, hist: line.map((x, i) => x - signal[i]) };
}

/** Volatilité glissante annualisée des variations en % (252 jours) */
export function rollingVol(v: number[], n = 20) {
  const r = v.map((x, i) => (i && v[i - 1] ? Math.log(x / v[i - 1]) : NaN));
  return r.map((_, i) => {
    if (i < n) return NaN;
    const w = r.slice(i + 1 - n, i + 1);
    const m = w.reduce((a, b) => a + b, 0) / n;
    return Math.sqrt(w.reduce((a, b) => a + (b - m) ** 2, 0) / (n - 1)) * Math.sqrt(252) * 100;
  });
}

export function drawdown(v: number[]) {
  let peak = -Infinity;
  return v.map((x) => { peak = Math.max(peak, x); return peak ? ((x - peak) / peak) * 100 : 0; });
}

/* ---------- Séries dérivées ---------- */

const mk = (id: string, label: string, points: SeriesPoint[]): Series => ({ id, label, unit: "percent", frequency: "dérivée", source: "Calcul à partir des séries sources", points });

/** a − b, sur les dates de a, avec report de la dernière valeur connue de b (séries mensuelles). */
export function diff(a: Series, b: Series, id: string, label: string): Series {
  const pts: SeriesPoint[] = [];
  let j = -1;
  for (const p of a.points) {
    while (j + 1 < b.points.length && b.points[j + 1].date <= p.date) j++;
    if (j >= 0) pts.push({ date: p.date, value: Math.round((p.value - b.points[j].value) * 1e6) / 1e6 });
  }
  return mk(id, label, pts);
}

/** Variation sur 12 mois d'un indice mensuel (%). Exige des mois consécutifs. */
export function yoy(s: Series, id: string, label: string): Series {
  const key = (d: string) => d.slice(0, 7);
  const byMonth = new Map(s.points.map((p) => [key(p.date), p.value]));
  const pts: SeriesPoint[] = [];
  for (const p of s.points) {
    const d = new Date(`${p.date}T12:00:00Z`);
    d.setUTCFullYear(d.getUTCFullYear() - 1);
    const prev = byMonth.get(d.toISOString().slice(0, 7));
    if (prev) pts.push({ date: p.date, value: Math.round(((p.value / prev - 1) * 100) * 1e4) / 1e4 });
  }
  return mk(id, label, pts);
}

export function withDerived(list: Series[]): Series[] {
  const g = (id: string) => list.find((s) => s.id === id);
  const out: Series[] = [];
  const us10 = g("DGS10"), us2 = g("DGS2"), ca10 = g("BD.CDN.10YR.DQ.YLD"), ca2 = g("BD.CDN.2YR.DQ.YLD");
  const bocr = g("V39079"), ff = g("DFF"), caCpi = g("STATIC_TOTALCPICHANGE"), usCpi = g("CPIAUCSL");
  if (us10 && us2) out.push(diff(us10, us2, "US_10Y_2Y", "Courbe des taux É.-U. (10 ans − 2 ans)"));
  if (ca10 && ca2) out.push(diff(ca10, ca2, "CA_10Y_2Y", "Courbe des taux Canada (10 ans − 2 ans)"));
  if (ca10 && us10) out.push(diff(ca10, us10, "CA_US_10Y", "Écart Canada − É.-U., obligations 10 ans"));
  if (ca2 && us2) out.push(diff(ca2, us2, "CA_US_2Y", "Écart Canada − É.-U., obligations 2 ans"));
  if (bocr && ff) out.push(diff(bocr, ff, "POLICY_SPREAD", "Écart taux directeur Canada − É.-U."));
  if (bocr && caCpi) out.push(diff(bocr, caCpi, "CA_REAL_POLICY", "Taux directeur réel Canada (taux − IPC a/a)"));
  if (usCpi) {
    const y = yoy(usCpi, "US_CPI_YOY", "IPC É.-U., variation sur 12 mois (%)");
    out.push(y);
    if (ff) out.push(diff(ff, y, "US_REAL_POLICY", "Taux directeur réel É.-U. (taux − IPC a/a)"));
  }
  return [...list, ...out];
}
