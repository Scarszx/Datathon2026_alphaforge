/* Tests des composants de la page /chat : emplacements de preuves, affichage progressif, carte de mandat.
 * Les données simulent exactement les schémas du contrat v0.4.0 (types.ts). Aucun appel réseau. */
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Mandate, MandateCreateRequest, Run } from "../../api/types";
import EvidenceText from "./EvidenceText";
import MandateCard from "./MandateCard";
import SimulationPanel from "./SimulationPanel";
import { LangContext, t as tr, warningText } from "../../lib/i18n";

afterEach(cleanup);

const DRAFT: MandateCreateRequest = {
  portfolioId: "main",
  mode: "add_asset",
  objective: "growth",
  horizonYears: 10,
  riskTolerance: 4,
  riskCapacity: 3,
  maxAcceptableLossPct: 20,
  province: "QC",
  userLanguage: "fr",
  operations: [{ action: "add", ticker: "NVDA", amount: 5000, currency: "CAD" }],
  subjectTicker: "NVDA",
  fieldSources: { riskCapacity: "persona", subjectTicker: "user_answer" },
};

const CONFIRMED: Mandate = {
  sessionId: "s1",
  version: 2,
  mandate: DRAFT,
  riskProfile: 3,
  effectiveMaxLossPct: 20,
  warnings: [{ code: "LOSS_EXCEEDS_DEFAULT", message: "Maximum acceptable loss (30%) exceeds the team assumption default (20%) for this horizon.", params: { maxAcceptableLossPct: 30, defaultLossPct: 20 } }],
  changedFields: ["horizonYears"],
  confirmedAt: "2026-11-14T10:00:00.000Z",
};

const EV = (id: string, label: string, formatted?: string) => ({
  id, kind: "metric" as const, label, formatted, source: "démo",
});

const PARTIAL: Run = {
  runId: "r1", sessionId: "s1", mandateVersion: 2, status: "partial", datasetVersion: "demo", userLanguage: "fr",
  scenarios: [
    { index: 0, label: "Portefeuille actuel", verdict: "pass", metrics: { volatility: "EV-01" } },
    { index: 1, label: "Idée telle quelle", verdict: "fail", metrics: { volatility: "EV-02" } },
    { index: 2, label: "Alternative", verdict: "warn" },
  ],
  verdicts: [{ rule: "R2", scenario: 1, status: "fail", reasonCode: "MAX_LOSS_EXCEEDED", evidence: ["EV-02"], messageEn: "Worst drop 25% versus accepted loss 20%." }],
  evidence: [EV("EV-01", "Volatilité, scénario 0", "12,0 %"), EV("EV-02", "Volatilité, scénario 1", "31,5 %")],
  jurisdictionNotices: ["[démo] Simulation pédagogique."],
  createdAt: "2026-11-14T10:00:00.000Z",
};

const DONE: Run = {
  ...PARTIAL,
  status: "done",
  narrative: {
    language: "fr",
    sections: [
      { key: "why", textEn: "Volatility {EV-02} exceeds the limit.", text: "La volatilité {EV-02} dépasse la limite." },
      { key: "limits", textEn: "Unknown placeholder {EV-77} never shows a number.", text: "Emplacement inconnu {EV-77} : jamais de chiffre." },
    ],
  },
  verifier: { placeholdersResolved: 2, placeholdersTotal: 2, handwrittenNumbers: 0, forbiddenPhrases: 0, placeholdersMatch: true },
  completedAt: "2026-11-14T10:00:05.000Z",
};

describe("EvidenceText (emplacements {EV-nn}/{KB-nn})", () => {
  it("remplace chaque emplacement connu par un badge cliquable qui ouvre la carte de preuve", () => {
    render(<EvidenceText text="La volatilité {EV-01} dépasse {KB-01}." evidence={[EV("EV-01", "Volatilité", "12,0 %")]} lang="fr" />);
    expect(screen.getByText(/^La volatilité/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "EV-01" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "EV-01" }));
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText("Volatilité")).toBeTruthy();
  });

  it("n'affiche JAMAIS de chiffre pour un emplacement inconnu (badge non cliquable, mention explicite)", () => {
    render(<EvidenceText text="Preuve inconnue : {EV-99}." evidence={[EV("EV-01", "Volatilité", "12,0 %")]} lang="fr" />);
    const badge = screen.getByRole("button", { name: /inconnu/i });
    expect(badge.textContent).not.toMatch(/\d/); // aucun chiffre inventé
    fireEvent.click(badge);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("les extraits réglementaires portent la mention « extrait original (anglais) »", () => {
    render(<EvidenceText text="Cadre : {KB-01}." evidence={[{ id: "KB-01", kind: "regulation", label: "Avis 31-368", excerpt: "[simulé]", jurisdiction: "CA", source: "démo" }]} lang="fr" />);
    fireEvent.click(screen.getByRole("button", { name: "KB-01" }));
    expect(screen.getByText("Extrait original (anglais)")).toBeTruthy();
  });
});

describe("SimulationPanel (affichage progressif partial → done)", () => {
  it("en partial : scénarios et verdicts visibles, explication et vérificateur absents", () => {
    render(<SimulationPanel run={PARTIAL} lang="fr" />);
    expect(screen.getByText("Idée telle quelle")).toBeTruthy();
    expect(screen.getAllByText("seuil dépassé").length).toBeGreaterThan(0); // libellé du motif, plus le code brut
    expect(screen.queryByText("Ce qui a déclenché les règles")).toBeNull();
    expect(screen.queryByText("Vérificateur")).toBeNull();
    expect(screen.getByText(/Scénarios et verdicts affichés dès maintenant/)).toBeTruthy();
  });

  it("en done : rubriques de l'explication et score du vérificateur affichés", () => {
    render(<SimulationPanel run={DONE} lang="fr" />);
    expect(screen.getByText("Ce qui a déclenché les règles")).toBeTruthy();
    expect(screen.getByText(/Emplacements résolus/)).toBeTruthy();
    expect(screen.getByText("2/2")).toBeTruthy();
    // La mesure du récit vient du registre, pas du texte : le badge EV-02 est rendu, pas le nombre du texte.
    expect(screen.getAllByRole("button", { name: "EV-02" }).length).toBeGreaterThan(0);
  });

  it("aucune citation sous une règle non déclenchée, même si citations est non vide", () => {
    const oldRun: Run = {
      ...PARTIAL,
      rulesVersion: 1, // run d'avant le lot A : citations possibles sous un pass
      evidence: [...PARTIAL.evidence, { id: "KB-01", kind: "regulation", label: "Avis 31-368", excerpt: "[simulé]", jurisdiction: "CA", source: "démo" }],
      verdicts: [
        { rule: "R2", scenario: 1, status: "fail", reasonCode: "MAX_LOSS_EXCEEDED", evidence: ["EV-02"], citations: ["KB-01"], messageEn: "Triggered." },
        { rule: "R3", scenario: 0, status: "pass", reasonCode: "PORTFOLIO_LEVEL_IMPACT", evidence: ["EV-01"], citations: ["KB-01"], messageEn: "Not triggered." },
      ],
    };
    render(<SimulationPanel run={oldRun} lang="fr" />);
    expect(screen.getAllByRole("button", { name: "KB-01" }).length).toBe(1); // seulement sous la règle déclenchée
  });

  it("ancien run sans rulesVersion : bandeau « version précédente »", () => {
    const legacy: Run = { ...PARTIAL, rulesVersion: undefined };
    render(<SimulationPanel run={legacy} lang="fr" />);
    expect(screen.getByText(/version précédente/)).toBeTruthy();
  });

  it("sans run : message d'accueil et mention permanente", () => {
    render(<SimulationPanel run={null} lang="fr" />);
    expect(screen.getByText(/Aucune analyse pour l'instant/)).toBeTruthy();
    expect(screen.getByText(/pas un conseil financier/)).toBeTruthy();
  });

  it("mentions fixes du lot D affichées en partial, avec la version du jeu et la phrase fixe", () => {
    render(<SimulationPanel run={PARTIAL} lang="fr" />);
    expect(screen.getByText(/Vous prenez seul vos décisions/)).toBeTruthy();
    expect(screen.getByText(/AlphaForge ne se prononce pas sur ce qui vous convient\./)).toBeTruthy();
    expect(screen.getByText(/jeu de données demo/)).toBeTruthy();
  });

  it("décompte des règles par scénario calculé côté interface, plus de pastille", () => {
    const run: Run = {
      ...PARTIAL,
      verdicts: [
        { rule: "R1", scenario: 1, status: "fail", reasonCode: "IDEA_EXCEEDS_RISK_PROFILE", evidence: [], citations: [], messageEn: "" },
        { rule: "R2", scenario: 1, status: "warn", reasonCode: "MAX_LOSS_NEAR_LIMIT", evidence: [], citations: [], messageEn: "" },
        { rule: "R3", scenario: 1, status: "pass", reasonCode: "PORTFOLIO_LEVEL_IMPACT", evidence: [], citations: [], messageEn: "" },
        { rule: "R6", scenario: 0, status: "pass", reasonCode: "CONCENTRATION_OK", evidence: [], citations: [], messageEn: "" },
      ],
    };
    render(<SimulationPanel run={run} lang="fr" />);
    expect(screen.getAllByText(/1 règle déclenchée, 1 à vérifier/).length).toBeGreaterThan(0);
    expect(screen.getByText("aucune règle déclenchée")).toBeTruthy();
  });
});

describe("Explication et libellés des métriques (contrat : explanation toujours affichée)", () => {
  const EXPLANATION = {
    sources: [{ id: "prices_daily", dataset: "prices/RY.TO.parquet@2026-11-14", asOf: "2026-11-14" }],
    steps: [{ agentId: "agent-orchestrator", tool: "get_portfolio", status: "ok" as const, durationMs: 12 }],
    assumptions: ["Volatilité annualisée sur 252 jours."],
    limitations: ["Le rendement passé ne prédit pas le futur."],
  };

  it("affiche l'explication du run (sources, étapes, hypothèses, limites) dans le panneau", () => {
    const { container } = render(<SimulationPanel run={{ ...DONE, explanation: EXPLANATION }} lang="fr" />);
    expect(container.querySelector("details.expl:not(.provenance) summary")?.textContent).toContain("Explication");
    expect(screen.getByText("prices_daily")).toBeTruthy();
    expect(screen.getByText("get_portfolio")).toBeTruthy();
    expect(screen.getByText("Volatilité annualisée sur 252 jours.")).toBeTruthy();
    expect(screen.getByText("Le rendement passé ne prédit pas le futur.")).toBeTruthy();
  });

  it("traduit les libellés fixes de l'explication en anglais", () => {
    const { container } = render(
      <LangContext.Provider value="en">
        <SimulationPanel run={{ ...DONE, userLanguage: "en", explanation: EXPLANATION }} lang="en" />
      </LangContext.Provider>,
    );
    expect(container.querySelector("details.expl:not(.provenance) summary")?.textContent).toContain("Explanation");
    expect(screen.getByText("Assumptions")).toBeTruthy();
    expect(screen.getByText("Limitations")).toBeTruthy();
  });

  it("connaît les métriques émises par le back (totalReturn, stressCovid2020, cryptoWeight)", () => {
    for (const lang of ["fr", "en"] as const) {
      for (const key of ["totalReturn", "stressCovid2020", "cryptoWeight", "volatility", "maxDrawdown", "stress2022", "stressRates", "stressCrypto", "topSingleWeight", "techWeightLookThrough"]) {
        expect(tr(`sim.metric.${key}`, lang)).not.toBe(`sim.metric.${key}`);
      }
    }
  });
});

describe("warningText (avertissements du mandat { code, message })", () => {
  it("traduit un code connu en fr et en en, avec ses paramètres", () => {
    const w = { code: "HORIZON_EXCEEDS_PROJECT", message: "Horizon (10 years) exceeds the project timeline (3 years).", params: { horizonYears: 10, projectYears: 3 } };
    expect(warningText(w, "fr")).toBe("L'horizon (10 ans) dépasse l'échéance du projet (3 ans).");
    expect(warningText(w, "en")).toBe("The horizon (10 years) exceeds the project timeline (3 years).");
  });
  it("code inconnu ou ancienne chaîne : message du serveur, jamais un texte inventé", () => {
    expect(warningText({ code: "NOUVEAU_CODE", message: "Server text." }, "fr")).toBe("Server text.");
    expect(warningText("Ancienne chaîne.", "fr")).toBe("Ancienne chaîne.");
  });
});

describe("MandateCard (carte de mandat)", () => {
  it("affiche les champs du brouillon avec la source connue de chaque ligne", () => {
    render(<MandateCard mandate={DRAFT} lang="fr" />);
    expect(screen.getByText("Ajouter un titre")).toBeTruthy();
    expect(screen.getByText("NVDA")).toBeTruthy();
    expect(screen.getByText("persona")).toBeTruthy();          // riskCapacity
    expect(screen.getByText("votre réponse")).toBeTruthy();    // subjectTicker
    expect(screen.queryByText(/Confirmé le/)).toBeNull();
  });

  it("affiche le mandat confirmé : version, profil retenu, perte retenue, avertissements", () => {
    render(<MandateCard mandate={DRAFT} confirmed={CONFIRMED} lang="fr" />);
    expect(screen.getByText(/Version 2/)).toBeTruthy();
    expect(screen.getAllByText(/20 %/).length).toBeGreaterThan(0);             // effectiveMaxLossPct
    expect(screen.getByText(/Profil retenu \(R1\) : Équilibré/)).toBeTruthy();
    // Traduit selon le code, avec les paramètres du serveur ; jamais le message anglais quand le code est connu.
    expect(screen.getByText(/La perte maximale acceptée \(30 %\) dépasse le défaut d'équipe \(20 %\)/)).toBeTruthy();
    expect(screen.queryByText(/Maximum acceptable loss/)).toBeNull();
    expect(screen.getByText(/horizonYears/)).toBeTruthy();     // changedFields
  });
});

/* Mode build (0.4.12) : le portefeuille construit est une liste à puces, sans graphique. */
describe("Portefeuille construit (mode build)", () => {
  const BUILT: Run = {
    ...PARTIAL,
    status: "done",
    scenarios: [
      { index: 0, label: "Portefeuille actuel", verdict: "pass", metrics: {} },
      {
        index: 1, label: "Constructed portfolio", verdict: "pass",
        description: "Simulation built from your parameters.",
        metrics: { expectedReturn: "EV-10", beta: "EV-11" },
        allocation: [{ label: "ne doit pas s'afficher", weight: 100 }],
        holdings: [
          { symbol: "AAA", name: "Alpha Corp", industry: "Tobacco", weight: 10, evidence: { weight: "EV-03", beta: "EV-04", expectedReturn: "EV-05" } },
          { symbol: "BBB", name: "Beta Inc", industry: "Software", weight: 8, evidence: { weight: "EV-06", beta: "EV-07", expectedReturn: "EV-08" } },
        ],
        parameters: [
          { key: "riskAversion", value: 4, riskProfile: 3, evidence: "EV-09" },
          { key: "excludedIndustries", value: ["Medical Devices"] },
        ],
      },
    ],
    evidence: [
      EV("EV-03", "Holding AAA: weight", "10,0 %"), EV("EV-04", "Holding AAA: beta", "1,21"), EV("EV-05", "Holding AAA: expected", "9,8 %"),
      EV("EV-06", "Holding BBB: weight", "8,0 %"), EV("EV-07", "Holding BBB: beta", "0,95"), EV("EV-08", "Holding BBB: expected", "7,1 %"),
      EV("EV-09", "Risk aversion", "4,00"), EV("EV-10", "Expected return", "8,4 %"), EV("EV-11", "Beta", "1,05"),
    ],
  };

  it("liste les titres avec poids, bêta et rendement espéré, et les paramètres, sans barres", () => {
    const { container } = render(<SimulationPanel run={BUILT} lang="fr" />);
    expect(screen.getByText(/ni quoi acheter ni quoi détenir/i)).toBeTruthy();
    const items = container.querySelectorAll("ul.built-holdings li");
    expect(items.length).toBe(4); // 2 titres + 2 paramètres
    expect(items[0].textContent).toContain("AAA");
    expect(items[0].textContent).toContain("10,0 %");
    expect(items[0].textContent).toContain("1,21");
    expect(items[0].textContent).toContain("9,8 %");
    expect(items[2].textContent).toContain("A = 4");
    expect(items[2].textContent).toContain("votre profil : Équilibré");
    expect(items[3].textContent).toContain("Medical Devices");
    expect(container.querySelector(".alloc-row")).toBeNull();
    expect(screen.getAllByText("Portefeuille construit").length).toBeGreaterThan(0);
  });

  it("Adopter : bouton seulement si le moteur a fourni quantité et prix pour chaque titre", () => {
    const sized = (extra: boolean): Run => ({
      ...BUILT,
      scenarios: BUILT.scenarios.map((sc) => sc.index !== 1 ? sc : {
        ...sc, holdings: sc.holdings!.map((h, i) => (extra || i === 0 ? { ...h, quantity: 12.5, price: 80 + i, currency: "USD" } : h)),
      }),
    });
    const onAdopt = vi.fn();
    const { rerender } = render(<SimulationPanel run={BUILT} lang="fr" onAdopt={onAdopt} />);
    expect(screen.queryByText("Adopter comme mon portefeuille fictif")).toBeNull(); // pas de quantités : ancien run
    rerender(<SimulationPanel run={sized(false)} lang="fr" onAdopt={onAdopt} />);
    expect(screen.queryByText("Adopter comme mon portefeuille fictif")).toBeNull(); // un titre sans quantité
    rerender(<SimulationPanel run={sized(true)} lang="fr" onAdopt={onAdopt} />);
    fireEvent.click(screen.getByText("Adopter comme mon portefeuille fictif"));
    expect(onAdopt).toHaveBeenCalledTimes(1);
    expect(onAdopt.mock.calls[0][0].holdings[0]).toMatchObject({ symbol: "AAA", quantity: 12.5, price: 80 });
    rerender(<SimulationPanel run={sized(true)} lang="fr" />);
    expect(screen.queryByText("Adopter comme mon portefeuille fictif")).toBeNull(); // sans onAdopt : pas de bouton
  });

  it("la carte de mandat affiche le mode et les industries, seulement si elles existent", () => {
    const build: MandateCreateRequest = {
      ...DRAFT, mode: "build", operations: undefined, subjectTicker: undefined,
      preferences: { excludedIndustries: ["Medical Devices"], preferredIndustries: [{ industry: "Tobacco", minWeight: 15 }, { industry: "Banks - Diversified", minWeight: null }] },
    };
    const { container, rerender } = render(<MandateCard mandate={build} lang="fr" />);
    expect(container.textContent).toContain("Construire un portefeuille");
    expect(container.textContent).toContain("Medical Devices");
    expect(container.textContent).toContain("Tobacco (min. 15 %)");
    expect(container.textContent).toContain("Banks - Diversified");
    rerender(<MandateCard mandate={{ ...build, preferences: undefined }} lang="fr" />);
    expect(container.textContent).not.toContain("Industries exclues");
  });
});

describe("Cartes de synthèse et provenance (idées 1 et 6)", () => {
  const RUN: Run = {
    ...DONE,
    scenarios: [
      { index: 0, label: "Portefeuille actuel", metrics: { topSingleWeight: "EV-10", maxDrawdownRange: "EV-11" } },
    ],
    evidence: [
      { id: "EV-10", kind: "metric", label: "Top weight, scenario 0", formatted: "12,0 %", source: "dataset" },
      { id: "EV-11", kind: "metric", label: "Maximum drawdown, 90% resampling range, scenario 0", formatted: "18,0 % à 31,0 %", source: "dataset", window: "2021/2026", asOf: "2026-11-12", method: "Bootstrap." },
      { id: "KB-01", kind: "regulation", label: "Avis 31-368", source: "kb", document: "Avis 31-368", regulator: "ACVM" },
    ],
    verdicts: [
      { rule: "R6", scenario: 0, status: "warn", reasonCode: "CONCENTRATION_ELEVATED", threshold: { value: 10, nature: "team_assumption" } },
      { rule: "R2", scenario: 0, status: "pass", reasonCode: "MAX_LOSS_WITHIN_LIMIT", threshold: { value: 20, nature: "team_assumption" } },
    ],
  };

  it("affiche le fait chiffré, la fourchette et le seuil, sans jugement", () => {
    const { container } = render(<SimulationPanel run={RUN} lang="fr" horizonYears={3} />);
    expect(container.textContent).toContain("Premier titre : 12,0 % du portefeuille.");
    expect(container.textContent).toContain("entre 18,0 % à 31,0 %");
    expect(container.textContent).toContain("Ce n'est pas une prévision");
    expect(container.textContent).toContain("Horizon indiqué dans le mandat : 3 an(s).");
    expect(container.textContent).not.toMatch(/\bsain\b|concentration forte|à surveiller/i);
  });

  it("le panneau de provenance sépare moteur de calcul et rédaction par l'IA", () => {
    const { container } = render(<SimulationPanel run={RUN} lang="fr" />);
    const prov = container.querySelector("details.provenance")!;
    expect(prov.querySelector("summary")?.textContent).toBe("Comment AlphaForge arrive à cette conclusion");
    expect(prov.textContent).toContain("Calculé par le moteur");
    expect(prov.textContent).toContain("Rédigé par l'IA");
    expect(prov.textContent).toContain("Avis 31-368");
  });
});
