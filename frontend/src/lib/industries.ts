/*
 * Industries d'intérêt (choix multiple) à l'inscription et dans le profil.
 * Regroupe les industries Yahoo Finance du jeu de données en catégories plus larges.
 * Deux listes : ce que le client aime et ce qu'il préfère éviter (une industrie ne peut pas être dans les deux).
 * Stockage : dans `preferences` du profil investisseur (liste de textes du contrat), sous la forme
 * « Industrie : <libellé> » ou « Industrie à éviter : <libellé> », sans nouveau champ de contrat.
 */
export const INDUSTRIES: { label: string; en: string; covers: string }[] = [
  { label: "Semi-conducteurs et équipements", en: "Semiconductors and equipment", covers: "Semiconductors, Semiconductor Equipment & Materials" },
  { label: "Logiciels et infonuagique", en: "Software and cloud", covers: "Software - Application, Software - Infrastructure" },
  { label: "Matériel informatique et équipements de communication", en: "Computer hardware and communication equipment", covers: "Computer Hardware, Communication Equipment" },
  { label: "Télécommunications et contenu Internet", en: "Telecommunications and Internet content", covers: "Telecom Services, Internet Content & Information" },
  { label: "Pharmaceutique et biotechnologie", en: "Pharmaceuticals and biotechnology", covers: "Drug Manufacturers - General, Biotechnology" },
  { label: "Dispositifs médicaux, diagnostics et distribution médicale", en: "Medical devices, diagnostics and medical distribution", covers: "Medical Devices, Diagnostics & Research, Medical Distribution" },
  { label: "Banques et crédit", en: "Banks and credit", covers: "Banks - Diversified, Credit Services" },
  { label: "Gestion d'actifs et marchés financiers", en: "Asset management and capital markets", covers: "Asset Management, Capital Markets, Financial Data & Stock Exchanges" },
  { label: "Assurance et régimes de santé", en: "Insurance and health plans", covers: "Insurance - Property & Casualty, Insurance Brokers, Healthcare Plans" },
  { label: "Aérospatiale et défense", en: "Aerospace and defence", covers: "Aerospace & Defense" },
  { label: "Machinerie et équipement industriel", en: "Industrial machinery and equipment", covers: "Specialty Industrial Machinery, Farm & Heavy Construction Machinery" },
  { label: "Transport ferroviaire et logistique", en: "Rail transport and logistics", covers: "Railroads, Integrated Freight & Logistics" },
  { label: "Services publics (électricité)", en: "Utilities (electricity)", covers: "Utilities - Regulated Electric" },
  { label: "Produits chimiques de spécialité", en: "Specialty chemicals", covers: "Specialty Chemicals" },
  { label: "Pétrole et gaz", en: "Oil and gas", covers: "Oil & Gas Refining & Marketing, Oil & Gas Midstream, Oil & Gas Integrated" },
  { label: "Immobilier (FPI)", en: "Real estate (REITs)", covers: "REIT - Specialty" },
  { label: "Biens de consommation courante", en: "Consumer staples", covers: "Beverages - Non-Alcoholic, Tobacco, Household & Personal Products" },
  { label: "Commerce de détail et en ligne", en: "Retail and e-commerce", covers: "Discount Stores, Internet Retail, Home Improvement Retail" },
  { label: "Automobile", en: "Automotive", covers: "Auto Manufacturers" },
  { label: "Voyages et services de voyage", en: "Travel and travel services", covers: "Travel Services" },
  { label: "Conglomérats", en: "Conglomerates", covers: "Conglomerates" },
];
const LIKED = "Industrie : ";
const AVOIDED = "Industrie à éviter : ";
export type IndustryChoice = { liked: string[]; avoided: string[] };
export const EMPTY_INDUSTRIES: IndustryChoice = { liked: [], avoided: [] };
/** Industries choisies → entrées de `preferences` (« Industrie : X », « Industrie à éviter : X »). */
export const industryPrefs = ({ liked, avoided }: IndustryChoice) => [
  ...liked.map((l) => LIKED + l),
  ...avoided.map((l) => AVOIDED + l),
];
/** Sépare `preferences` en industries aimées, industries à éviter (libellés connus) et autres préférences. */
export function splitPreferences(prefs: string[] = []): IndustryChoice & { others: string[] } {
  const known = new Set(INDUSTRIES.map((i) => i.label));
  const liked: string[] = [], avoided: string[] = [], others: string[] = [];
  for (const p of prefs) {
    // AVOIDED d'abord : « Industrie à éviter : » commence aussi par « Industrie ».
    if (p.startsWith(AVOIDED) && known.has(p.slice(AVOIDED.length))) avoided.push(p.slice(AVOIDED.length));
    else if (p.startsWith(LIKED) && known.has(p.slice(LIKED.length))) liked.push(p.slice(LIKED.length));
    else others.push(p);
  }
  return { liked, avoided, others };
}

/** Libellé d'une industrie dans la langue d'affichage (la valeur stockée reste le libellé français). */
export const industryName = (label: string, lang: "fr" | "en") => (lang === "en" ? INDUSTRIES.find((i) => i.label === label)?.en ?? label : label);
