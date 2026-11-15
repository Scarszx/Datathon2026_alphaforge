/* Formatage fr-CA maison (stable entre serveur et navigateur). */

const NBSP = " ";
const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

export function money(n: number, decimals = 2) {
  const [int, dec] = Math.abs(n).toFixed(decimals).split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
  return (n < 0 ? "−" : "") + grouped + (dec ? "," + dec : "");
}

export function cad(n: number, decimals = 2) {
  return money(n, decimals) + NBSP + "$";
}

export function pct(n: number) {
  return (n >= 0 ? "+" : "−") + Math.abs(n).toFixed(2).replace(".", ",") + NBSP + "%";
}

export function signedCad(n: number) {
  return (n >= 0 ? "+" : "−") + cad(Math.abs(n));
}

export function shortDate(ts: number, withYear = false) {
  const d = new Date(ts * 1000);
  return withYear ? `${MONTHS[d.getMonth()]} ${d.getFullYear()}` : `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

export function fullDate(ts: number) {
  const d = new Date(ts * 1000);
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function clock(ts: number) {
  return time(new Date(ts * 1000));
}

export function fullDateTime(ts: number) {
  return `${fullDate(ts)}, ${clock(ts)}`;
}

/** Grands nombres : 82,47 G, 1,54 M, 867 k */
export function compact(n: number) {
  const a = Math.abs(n);
  const [v, s] = a >= 1e12 ? [n / 1e12, "T"] : a >= 1e9 ? [n / 1e9, "G"] : a >= 1e6 ? [n / 1e6, "M"] : a >= 1e3 ? [n / 1e3, "k"] : [n, ""];
  return money(v, s ? 2 : 0) + (s ? NBSP + s : "");
}

export function time(d: Date) {
  return `${d.getHours()} h ${String(d.getMinutes()).padStart(2, "0")}`;
}

/** Montant avec code de devise : 1 234,50 CAD */
export function amount(n: number, currency: string, decimals = 2) {
  return money(n, decimals) + NBSP + currency;
}

export function signedAmount(n: number, currency: string) {
  return (n >= 0 ? "+" : "−") + amount(Math.abs(n), currency);
}

/** Pourcentage sans signe (le contrat donne des pourcentages : 9.07 = 9,07 %) */
export function plainPct(n: number, decimals = 1) {
  return money(n, decimals) + NBSP + "%";
}

/** Date ISO (YYYY-MM-DD ou ISO 8601) → secondes Unix, pour Chart */
export function toSeconds(iso: string) {
  return Math.floor(new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso).getTime() / 1000);
}

export function dateTimeFr(iso: string) {
  return new Date(iso).toLocaleDateString("fr-CA", { day: "numeric", month: "short" });
}
