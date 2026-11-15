/* Tests des lots A, B, C, E2 : libellés par motif, vocabulaire sans jugement, échelle de risque 1 à 5,
 * catégories de comparaison identiques au backend, anciens runs. Les fichiers du backend sont lus
 * directement dans le dépôt : le contrat fait foi. */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { FR, EN, t } from "./lib/i18n";
import { ruleFamily, ruleLabel, ruleBadgeClass, scenarioRuleSummary, type RuleStatus } from "./lib/ruleLabels";
import { RISK_BANDS, bandOfVolatility, retainedLevel } from "./lib/riskScale";
import { COMPARISON_CATEGORIES, categoriesByLevel } from "./lib/comparisonCategories";
import type { RuleVerdict } from "./api/types";

const BACKEND_CATEGORIES = JSON.parse(
  readFileSync(resolve(process.cwd(), "../backend/common/comparison_categories.json"), "utf-8"),
) as { categories: { id: string; label: string; level: number }[] };

const RULES_CONFIG = JSON.parse(
  readFileSync(resolve(process.cwd(), "../backend/agents/rules/rules_config.json"), "utf-8"),
) as { riskBandsByVolatility: { maxVolatilityPct?: number; band: number }[] };

describe("ruleLabels (lots A et B)", () => {
  const v = (reasonCode: string, status: RuleStatus, scenario = 1): RuleVerdict =>
    ({ rule: "R?", scenario, status, reasonCode } as RuleVerdict);

  it("chaque reasonCode de backend/agents/rules/rules.py a un libellé explicite fr/en", () => {
    const codes = [
      "RISK_PROFILE_RESPECTED", "IDEA_EXCEEDS_RISK_PROFILE", "PORTFOLIO_EXCEEDS_RISK_PROFILE",
      "DRAWDOWN_NOT_COMPUTED", "MAX_LOSS_WITHIN_LIMIT", "MAX_LOSS_NEAR_LIMIT", "MAX_LOSS_EXCEEDED",
      "EMPTY_PORTFOLIO", "PORTFOLIO_LEVEL_IMPACT", "CONCENTRATION_OK", "CONCENTRATION_ELEVATED",
      "SECTOR_CONCENTRATION_ELEVATED", "CONCENTRATION_HIGH", "NO_CRYPTO_EXPOSURE", "CRYPTO_WITHIN_CAP",
      "CRYPTO_CAP_EXCEEDED", "ESG_NOT_REQUESTED", "ESG_SOURCED", "ESG_NOT_VERIFIED",
      "NO_SECURITY_RECOMMENDED", "SECURITY_NAMED", "PROVINCE_NOTICES_ADDED",
      "MACRO_PUBLICATION_RESPECTED", "MACRO_USED_BEFORE_PUBLICATION",
    ];
    for (const code of codes) {
      expect(ruleLabel(code, "fail", "fr")).not.toBe(code);
      expect(ruleLabel(code, "fail", "en")).not.toBe(code);
    }
  });

  it("R4 est prioritaire sur le repli « tout pass = non déclenchée »", () => {
    expect(ruleLabel("COMPARISON_NOT_REQUESTED", "pass", "fr")).toBe("pas de comparaison demandée");
    expect(ruleLabel("COMPARISON_SHOWN", "pass", "en")).toBe("comparison shown");
    expect(ruleLabel("COMPARISON_UNAVAILABLE", "not_verified", "fr")).toBe("comparaison indisponible");
    expect(ruleFamily("COMPARISON_SHOWN", "pass")).toBe("not_triggered");
  });

  it("motifs inconnus : repli par statut", () => {
    expect(ruleLabel("NOUVEAU_MOTIF", "pass", "fr")).toBe("non déclenchée");
    expect(ruleLabel("NOUVEAU_MOTIF", "warn", "fr")).toBe("à vérifier");
    expect(ruleLabel("NOUVEAU_MOTIF", "fail", "en")).toBe("triggered");
    expect(ruleLabel("NOUVEAU_MOTIF", "not_verified", "fr")).toBe("non vérifiée");
  });

  it("badge neutre pour « non déclenchée », warn pour à vérifier, fail pour déclenchée", () => {
    expect(ruleBadgeClass("RISK_PROFILE_RESPECTED", "pass")).toBe("badge");
    expect(ruleBadgeClass("COMPARISON_SHOWN", "pass")).toBe("badge");
    expect(ruleBadgeClass("MAX_LOSS_NEAR_LIMIT", "warn")).toBe("badge warn");
    expect(ruleBadgeClass("EMPTY_PORTFOLIO", "warn")).toBe("badge warn");
    expect(ruleBadgeClass("MAX_LOSS_EXCEEDED", "fail")).toBe("badge fail");
    expect(ruleBadgeClass("SECURITY_NAMED", "fail")).toBe("badge fail");
  });

  it("décompte de la carte de scénario, calculé côté interface", () => {
    const verdicts = [
      v("IDEA_EXCEEDS_RISK_PROFILE", "fail"), v("MAX_LOSS_NEAR_LIMIT", "warn"), v("PORTFOLIO_LEVEL_IMPACT", "pass"),
    ];
    expect(scenarioRuleSummary(verdicts, 1, "fr")).toBe("1 règle déclenchée, 1 à vérifier");
    expect(scenarioRuleSummary([v("PORTFOLIO_LEVEL_IMPACT", "pass", 0)], 0, "fr")).toBe("aucune règle déclenchée");
    expect(scenarioRuleSummary([], 0, "fr")).toBe("aucune règle applicable");
    expect(scenarioRuleSummary([], 0, "en")).toBe("no rule applies");
  });
});

describe("i18n : vocabulaire sans jugement (lot A)", () => {
  const FORBIDDEN = /conforme|compliant|approuv|adapté|convient|compatible|recommand|\bPASS\b|\bWARN\b|\bFAIL\b/i;

  it("aucune valeur de i18n (fr et en) ne contient les mots interdits", () => {
    for (const dict of [FR, EN]) {
      for (const [key, value] of Object.entries(dict)) {
        // La phrase fixe du lot D est l'exception explicite (elle dit que l'outil ne juge pas).
        if (key === "app.fixedNotice.generic") continue;
        expect(`${key}: ${value}`).not.toMatch(FORBIDDEN);
      }
    }
  });

  it("la phrase fixe exacte existe en fr et en", () => {
    expect(FR["app.fixedNotice.generic"]).toContain("Grow ne se prononce pas sur ce qui vous convient.");
    expect(EN["app.fixedNotice.generic"]).toContain("Grow takes no position on what is suitable for you.");
  });

  it("les anciennes clés de conformité ont disparu", () => {
    for (const dict of [FR, EN]) {
      expect(Object.keys(dict).filter((k) => k.startsWith("expl.status."))).toEqual([]);
      expect(Object.keys(dict).filter((k) => k.startsWith("sim.verdict."))).toEqual([]);
    }
  });
});

describe("catégories de comparaison (lot B)", () => {
  it("ids et niveaux identiques à backend/common/comparison_categories.json", () => {
    const backend = BACKEND_CATEGORIES.categories.map(({ id, level }) => ({ id, level })).sort((a, b) => a.id.localeCompare(b.id));
    const front = COMPARISON_CATEGORIES.map(({ id, level }) => ({ id, level })).sort((a, b) => a.id.localeCompare(b.id));
    expect(front).toEqual(backend);
  });

  it("liste triée par niveau, sans symbole de FNB ni présélection", () => {
    const sorted = categoriesByLevel();
    for (let i = 1; i < sorted.length; i++) expect(sorted[i].level).toBeGreaterThanOrEqual(sorted[i - 1].level);
    expect(JSON.stringify(sorted)).not.toMatch(/\.TO|SPY|QQQ|AGG|TLT|GLD|VFV|XEQT|VEQT|XIC|XIU|XBB|ZAG|ZST|XBAL|VBAL|XSP|XEF/);
  });
});

describe("échelle de risque 1 à 5 (lot C)", () => {
  it("bandes identiques à rules_config.json (riskBandsByVolatility)", () => {
    expect(RISK_BANDS).toEqual(RULES_CONFIG.riskBandsByVolatility);
  });

  it("bornes et niveau retenu = le plus bas des deux (R1)", () => {
    expect(bandOfVolatility(10)).toBe(1);
    expect(bandOfVolatility(10.1)).toBe(2);
    expect(bandOfVolatility(14)).toBe(2);
    expect(bandOfVolatility(18)).toBe(3);
    expect(bandOfVolatility(25)).toBe(4);
    expect(bandOfVolatility(25.1)).toBe(5);
    expect(retainedLevel(4, 2)).toBe(2);
    expect(retainedLevel(1, 5)).toBe(1);
  });
});
