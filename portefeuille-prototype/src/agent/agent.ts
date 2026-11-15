import { cad, money, pct } from "../lib/format";
import { ASSETS, assetOf } from "../lib/market";
import { computePortfolio, riskMetrics, series } from "../lib/portfolio";
import { EQUITY_RANGE } from "../lib/profile";
import type { Prices, UserData } from "../lib/types";

/*
 * AGENT SIMULÉ (local, sans clé d'API).
 * Même structure que prévue pour le service Python : registre d'outils → planification →
 * exécution → interprétation → réponse. Les outils lisent UNIQUEMENT les données de l'utilisateur
 * connecté et ne peuvent créer aucun ordre. Aucune donnée n'est inventée.
 */

type Ctx = { data: UserData; prices: Prices };
type Tool = { name: string; description: string; run: (c: Ctx, args: Record<string, string | number>) => unknown };

const CONCEPTS: Record<string, string> = {
  diversification: "La diversification consiste à répartir ses placements entre plusieurs titres, secteurs et types d'actifs afin de réduire l'effet d'une mauvaise performance isolée.",
  volatilité: "La volatilité mesure l'ampleur des variations de prix d'un placement. Plus elle est élevée, plus la valeur fluctue (à la hausse comme à la baisse).",
  fnb: "Un FNB (fonds négocié en bourse) est un panier de titres qui s'achète et se vend en bourse comme une action, généralement à faibles frais.",
  reer: "Le REER est un compte enregistré de retraite : les cotisations sont déductibles d'impôt et la croissance est à l'abri de l'impôt jusqu'au retrait.",
  celi: "Le CELI est un compte enregistré où la croissance et les retraits sont libres d'impôt; les cotisations ne sont pas déductibles.",
  "cours limité": "Un ordre à cours limité ne s'exécute qu'au prix fixé ou à un meilleur prix. Il peut donc rester en attente si le marché n'atteint pas ce prix.",
  "au marché": "Un ordre au marché s'exécute immédiatement au meilleur prix disponible, sans garantie sur le prix exact.",
  rééquilibrage: "Le rééquilibrage consiste à ajuster périodiquement les placements pour ramener la répartition vers la cible choisie.",
  rendement: "Le rendement exprime le gain (ou la perte) d'un placement en pourcentage de la somme investie, sur une période donnée.",
};

export const TOOLS: Tool[] = [
  { name: "get_user_financial_profile", description: "Profil de risque, objectif, horizon", run: ({ data }) => data.profile },
  { name: "get_portfolio_holdings", description: "Positions du portefeuille", run: ({ data, prices }) => computePortfolio(data, prices).rows },
  { name: "calculate_portfolio_allocation", description: "Répartition par catégorie et secteur", run: ({ data, prices }) => { const p = computePortfolio(data, prices); return { byCategory: p.byCategory, bySector: p.bySector, total: p.total }; } },
  {
    name: "calculate_portfolio_performance", description: "Rendement sur 1 mois, AAJ, 1 an",
    run: ({ data, prices }) => {
      const p = computePortfolio(data, prices);
      const r = (k: "1M" | "AAJ" | "1A") => { const s = series(p.rows, p.cash, k).values; return s.length > 1 && s[0] > 0 ? (s[s.length - 1] / s[0] - 1) * 100 : null; };
      return { day: p.day, dayPct: p.dayPct, unrealized: p.unrealized, m1: r("1M"), ytd: r("AAJ"), y1: r("1A"), total: p.total };
    },
  },
  { name: "calculate_portfolio_risk", description: "Volatilité, baisse maximale, concentration", run: ({ data, prices }) => { const p = computePortfolio(data, prices); return riskMetrics(p.rows, p.cash); } },
  { name: "get_asset_information", description: "Information simulée sur un titre", run: (_c, a) => assetOf(String(a.symbol)) ?? null },
  {
    name: "calculate_investment_scenario", description: "Scénario hypothétique de variation du marché",
    run: ({ data, prices }, a) => {
      const p = computePortfolio(data, prices);
      const move = Number(a.move); // % signé
      const factor = (c: string) => (c === "Revenu fixe" ? move / 4 : move);
      const delta = p.rows.reduce((s, r) => s + (r.value * factor(r.category)) / 100, 0);
      return { move, delta, before: p.total, after: p.total + delta, afterPct: p.total > 0 ? (delta / p.total) * 100 : 0 };
    },
  },
  { name: "get_recent_transactions", description: "Transactions simulées récentes", run: ({ data }) => data.transactions.slice(0, 5) },
  { name: "get_watchlist", description: "Liste de surveillance", run: ({ data, prices }) => data.watchlist.map((s) => ({ symbol: s, name: assetOf(s)?.name, price: prices[s] })) },
  { name: "explain_financial_concept", description: "Explication éducative", run: (_c, a) => CONCEPTS[String(a.concept)] ?? null },
];

const tool = (n: string) => TOOLS.find((t) => t.name === n)!;
const has = (q: string, ...w: string[]) => w.some((x) => q.includes(x));

type Step = { name: string; args?: Record<string, string | number> };

/** 1) Sélection des outils selon la question. */
function plan(q: string): Step[] {
  const steps: Step[] = [];
  const concept = Object.keys(CONCEPTS).find((c) => q.includes(c)) ?? (has(q, "etf", "fonds négocié") ? "fnb" : has(q, "limite") ? "cours limité" : has(q, "marché") && has(q, "ordre") ? "au marché" : undefined);
  const m = q.match(/(\d+(?:[.,]\d+)?)\s*%/);
  if (concept && has(q, "explique", "qu'est", "c'est quoi", "définition", "signifie", "différence")) return [{ name: "explain_financial_concept", args: { concept } }];
  if (has(q, "baiss", "chute", "hauss", "scénario", "scenario", "et si", "what if", "décline", "declin")) {
    const move = (m ? parseFloat(m[1].replace(",", ".")) : 10) * (has(q, "hauss", "augment", "gain") ? 1 : -1);
    return [{ name: "calculate_investment_scenario", args: { move } }, { name: "get_portfolio_holdings" }];
  }
  if (has(q, "objectif", "aligné", "aligne", "profil", "convient", "correspond", "technolog", "exposé", "exposure", "exposition")) steps.push({ name: "get_user_financial_profile" }, { name: "get_portfolio_holdings" }, { name: "calculate_portfolio_allocation" }, { name: "calculate_portfolio_risk" });
  else if (has(q, "risque", "volatil", "concentr", "diversif")) steps.push({ name: "get_user_financial_profile" }, { name: "calculate_portfolio_risk" }, { name: "calculate_portfolio_allocation" });
  else if (has(q, "performance", "rendement", "performe", "se porte", "comment va", "portefeuille", "gagn", "perdu", "récent", "recent", "évolu", "explique")) steps.push({ name: "calculate_portfolio_performance" }, { name: "get_portfolio_holdings" });
  else if (has(q, "répartition", "allocation", "pourcentage", "plus gros", "plus grand", "secteur", "composition", "détiens", "positions", "titres")) steps.push({ name: "calculate_portfolio_allocation" }, { name: "get_portfolio_holdings" });
  else if (has(q, "transaction", "achat", "vente", "historique")) steps.push({ name: "get_recent_transactions" });
  else if (has(q, "surveill", "watchlist")) steps.push({ name: "get_watchlist" });
  else if (has(q, "acheter", "vendre", "achète", "vends")) return [];
  return steps;
}

export const DISCLAIMER = "\n\n_Analyse éducative fondée sur des données simulées (prix fictifs, non en temps réel). Ce n'est pas un conseil financier._";

export const SUGGESTIONS = [
  "Comment se porte mon portefeuille ?",
  "Quelle est mon exposition au risque ?",
  "Suis-je aligné avec mes objectifs ?",
  "Quels actifs pèsent le plus dans mon portefeuille ?",
  "Que se passerait-il si le marché baissait de 10 % ?",
  "Explique la diversification",
];

export function ask(question: string, ctx: Ctx): { content: string; tools: string[] } {
  const q = question.toLowerCase().trim();
  const steps = plan(q);

  if (steps.length === 0) {
    if (has(q, "acheter", "vendre", "achète", "vends"))
      return { content: "Je ne peux pas passer d'ordre à votre place. Utilisez les boutons **Acheter** ou **Vendre** du tableau de bord : vous pourrez vérifier puis confirmer l'ordre simulé vous-même." + DISCLAIMER, tools: [] };
    return { content: "Je peux analyser votre portefeuille simulé (performance, répartition, risque, alignement avec votre profil), simuler un scénario de marché ou expliquer un concept financier. Essayez l'une des questions suggérées." + DISCLAIMER, tools: [] };
  }

  // 2) Exécution
  const out: Record<string, any> = {};
  steps.forEach((s) => { out[s.name] = tool(s.name).run(ctx, s.args ?? {}); });
  const used = steps.map((s) => s.name);
  const rows = computePortfolio(ctx.data, ctx.prices);
  if (rows.rows.length === 0 && !out.explain_financial_concept && !out.get_watchlist && !out.get_recent_transactions)
    return { content: "Votre portefeuille ne contient aucune position pour le moment : je n'ai donc rien à analyser. Achetez un titre simulé pour commencer." + DISCLAIMER, tools: used };

  // 3) Interprétation + 4) réponse
  let t = "";
  if (out.explain_financial_concept) t = out.explain_financial_concept;
  else if (out.calculate_investment_scenario) {
    const s = out.calculate_investment_scenario;
    t = `**Scénario hypothétique (pas une prévision)** : si les actions et FNB variaient de ${pct(s.move)} et les obligations d'environ le quart, la valeur passerait d'environ ${cad(s.before, 0)} à ${cad(s.after, 0)}, soit ${cad(s.delta, 0)} (${pct(s.afterPct)}). Les liquidités sont supposées inchangées.`;
  } else if (out.get_user_financial_profile || out.calculate_portfolio_risk) {
    const risk = out.calculate_portfolio_risk, alloc = out.calculate_portfolio_allocation, pr = out.get_user_financial_profile;
    const parts: string[] = [];
    if (pr) parts.push(`Votre profil est **${pr.label}** (score ${pr.score}/100), objectif : ${pr.objective.toLowerCase()}, horizon : ${pr.horizon.toLowerCase()}.`);
    if (risk) {
      parts.push(`Exposition aux actions et FNB : **${money(risk.equityPct, 1)} %**. Volatilité annualisée estimée (1 an simulé) : ${money(risk.volatilityPct, 1)} %. Baisse maximale historique simulée : ${money(risk.maxDrawdownPct, 1)} %. ${risk.topHolding ? `Plus grosse position : ${risk.topHolding.symbol} (${money(risk.topHolding.pct, 1)} %).` : ""}`);
      if (pr) {
        const [lo, hi] = EQUITY_RANGE[pr.label as keyof typeof EQUITY_RANGE];
        const verdict = risk.equityPct > hi ? `au-dessus de la plage habituellement associée à un profil ${pr.label.toLowerCase()} (${lo}–${hi} %)` : risk.equityPct < lo ? `en dessous de la plage habituellement associée à un profil ${pr.label.toLowerCase()} (${lo}–${hi} %)` : `dans la plage habituellement associée à un profil ${pr.label.toLowerCase()} (${lo}–${hi} %)`;
        parts.push(`Votre exposition est ${verdict}. Note : tous les FNB sont comptés comme des actions, ce qui est une approximation.`);
      }
    }
    if (alloc) {
      const tech = alloc.bySector.find((s: any) => s.name === "Technologie");
      parts.push(`Secteurs : ${alloc.bySector.slice(0, 3).map((s: any) => `${s.name} ${money(s.pct, 1)} %`).join(", ")}${has(q, "technolog") ? `. Technologie : ${tech ? money(tech.pct, 1) + " %" : "aucune exposition"}.` : "."}`);
    }
    t = parts.join("\n\n");
  } else if (out.calculate_portfolio_performance) {
    const p = out.calculate_portfolio_performance;
    const f = (v: number | null) => (v == null ? "indisponible" : pct(v));
    const best = [...rows.rows].sort((a, b) => b.gainPct - a.gainPct);
    t = `Valeur actuelle : **${cad(p.total, 0)}**. Aujourd'hui : ${cad(p.day)} (${pct(p.dayPct)}). Gain non réalisé : ${cad(p.unrealized, 0)}.\n\nRendement simulé : 1 mois ${f(p.m1)}, depuis le début de l'année ${f(p.ytd)}, 1 an ${f(p.y1)}.${best.length ? `\n\nMeilleure position : ${best[0].symbol} (${pct(best[0].gainPct)}); moins bonne : ${best[best.length - 1].symbol} (${pct(best[best.length - 1].gainPct)}).` : ""}`;
  } else if (out.calculate_portfolio_allocation) {
    const a = out.calculate_portfolio_allocation;
    t = `Les plus grosses positions : ${rows.rows.slice(0, 3).map((r) => `${r.symbol} (${money((r.value / a.total) * 100, 1)} %)`).join(", ")}.\n\nPar catégorie : ${a.byCategory.map((c: any) => `${c.name} ${money(c.pct, 1)} %`).join(", ")}.\n\nPar secteur : ${a.bySector.map((c: any) => `${c.name} ${money(c.pct, 1)} %`).join(", ")}.`;
  } else if (out.get_recent_transactions) {
    const tx = out.get_recent_transactions as UserData["transactions"];
    t = tx.length ? "Dernières transactions simulées :\n" + tx.map((x) => `• ${x.side === "buy" ? "Achat" : "Vente"} de ${x.quantity} ${x.symbol} à ${money(x.price)} ${x.currency}`).join("\n") : "Aucune transaction pour le moment.";
  } else if (out.get_watchlist) {
    const w = out.get_watchlist as { symbol: string; price: number }[];
    t = w.length ? "Votre liste de surveillance : " + w.map((x) => `${x.symbol} (${money(x.price)})`).join(", ") + "." : "Votre liste de surveillance est vide.";
  }
  return { content: t + DISCLAIMER, tools: used };
}

export const KNOWN_SYMBOLS = ASSETS.map((a) => a.symbol);
