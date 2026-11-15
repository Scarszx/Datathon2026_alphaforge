/* Tests des composants de la page /chat : emplacements de preuves, affichage progressif, carte de mandat.
 * Les données simulent exactement les schémas du contrat v0.4.0 (types.ts). Aucun appel réseau. */
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
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
    expect(screen.getAllByText("MAX_LOSS_EXCEEDED").length).toBeGreaterThan(0);
    expect(screen.queryByText("Pourquoi ce verdict")).toBeNull();
    expect(screen.queryByText("Vérificateur")).toBeNull();
    expect(screen.getByText(/Scénarios et verdicts affichés dès maintenant/)).toBeTruthy();
  });

  it("en done : rubriques de l'explication et score du vérificateur affichés", () => {
    render(<SimulationPanel run={DONE} lang="fr" />);
    expect(screen.getByText("Pourquoi ce verdict")).toBeTruthy();
    expect(screen.getByText(/Emplacements résolus/)).toBeTruthy();
    expect(screen.getByText("2/2")).toBeTruthy();
    // La mesure du récit vient du registre, pas du texte : le badge EV-02 est rendu, pas le nombre du texte.
    expect(screen.getAllByRole("button", { name: "EV-02" }).length).toBeGreaterThan(0);
  });

  it("sans run : message d'accueil et mention permanente", () => {
    render(<SimulationPanel run={null} lang="fr" />);
    expect(screen.getByText(/Aucune analyse pour l'instant/)).toBeTruthy();
    expect(screen.getByText(/pas un conseil financier/)).toBeTruthy();
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
    expect(container.querySelector("details.expl summary")?.textContent).toContain("Explication");
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
    expect(container.querySelector("details.expl summary")?.textContent).toContain("Explanation");
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
    expect(screen.getByText(/Profil retenu \(R1\) : 3/)).toBeTruthy();
    // Traduit selon le code, avec les paramètres du serveur ; jamais le message anglais quand le code est connu.
    expect(screen.getByText(/La perte maximale acceptée \(30 %\) dépasse le défaut d'équipe \(20 %\)/)).toBeTruthy();
    expect(screen.queryByText(/Maximum acceptable loss/)).toBeNull();
    expect(screen.getByText(/horizonYears/)).toBeTruthy();     // changedFields
  });
});
