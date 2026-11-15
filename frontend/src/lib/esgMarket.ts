/*
 * Questions « Critères ESG » et « Marché géographique » du questionnaire de création du portefeuille,
 * reprises dans « Modifier mon profil ». Elles ne comptent pas dans le score de risque (lib/risk.ts).
 * Stockage : comme les industries (lib/industries.ts), dans `preferences` du profil investisseur
 * (liste de textes du contrat), sans nouveau champ de contrat :
 * - « ESG » (exemple du contrat) si la personne veut que ses simulations en tiennent compte, rien sinon.
 *   L'orchestrateur la lit dans le profil pour remplir preferences.esg du mandat (règle R8, avis 81-334).
 * - « Marché géographique : Canada », « Marché géographique : États-Unis » (un ou les deux).
 *   Aucun champ du mandat ni aucune règle ne lit encore le marché : il reste une préférence du profil.
 */
export const ESG_PREF = "ESG";
const MARKET = "Marché géographique : ";
export const MARKETS = ["Canada", "États-Unis"] as const;
export type Market = (typeof MARKETS)[number];
export type EsgMarketChoice = { esg: boolean; markets: Market[] };
export const EMPTY_ESG_MARKET: EsgMarketChoice = { esg: false, markets: [] };

/** Réponses à la question ESG : oui ajoute l'entrée « ESG » aux préférences. */
export const ESG_ANSWERS: { value: boolean; label: string }[] = [
  { value: true, label: "Oui" },
  { value: false, label: "Non" },
];

const isMarket = (s: string): s is Market => (MARKETS as readonly string[]).includes(s);

/** Ajoute ou retire un marché (cases à cocher). */
export const toggleMarket = (markets: Market[], m: Market): Market[] =>
  markets.includes(m) ? markets.filter((x) => x !== m) : [...markets, m];

/** Choix ESG et marchés → entrées de `preferences` (« ESG », « Marché géographique : X »). */
export const esgMarketPrefs = ({ esg, markets }: EsgMarketChoice): string[] => [
  ...(esg ? [ESG_PREF] : []),
  ...MARKETS.filter((m) => markets.includes(m)).map((m) => MARKET + m),
];

/** Sépare `preferences` en choix ESG, marchés connus et autres préférences (« ESG » saisi à la main compte aussi). */
export function splitEsgMarket(prefs: string[] = []): EsgMarketChoice & { others: string[] } {
  let esg = false;
  const markets: Market[] = [], others: string[] = [];
  for (const p of prefs) {
    const market = p.startsWith(MARKET) ? p.slice(MARKET.length) : "";
    if (p.trim().toUpperCase() === ESG_PREF) esg = true;
    else if (isMarket(market)) { if (!markets.includes(market)) markets.push(market); }
    else others.push(p);
  }
  return { esg, markets, others };
}
