/* Panneau de simulation (colonne 3 de /chat) : scénarios 0/1/2 côte à côte, règles R1-R10 avec
 * libellé par motif (lot A), les 4 rubriques du récit, le score du vérificateur, les mentions R9,
 * les citations fixées de R5/R9 (lot E2) et les mentions fixes du lot D.
 * Affichage progressif : tout ce qui existe en status = partial s'affiche déjà ; le reste arrive à done. */
import { useState } from "react";
import type { RuleVerdict, Run, Scenario } from "../../api/types";
import { t, type Lang } from "../../lib/i18n";
import { ruleBadgeClass, ruleLabel, scenarioRuleSummary } from "../../lib/ruleLabels";
import Explanation from "../Explanation";
import EvidenceText, { EvidenceBadge } from "./EvidenceText";
import CompareCategory, { CompareCategoryButton } from "./CompareCategory";

const SCENARIO_LABEL_KEY = ["sim.scenario.current", "sim.scenario.idea", "sim.scenario.alternative"] as const;

/** Une colonne de scénario : label, décompte des règles (calculé ici, plus de pastille), répartition, mesures. */
function ScenarioCard({ run, s, lang }: { run: Run; s: Scenario; lang: Lang }) {
  const metric = (evId?: string) => run.evidence.find((e) => e.id === evId);
  const summary = scenarioRuleSummary(run.verdicts, s.index, lang);
  return (
    <div className="scenario-card">
      <div className="scenario-head">
        <strong>{s.label}</strong>
        <span className="badge">{summary}</span>
      </div>
      <div className="muted small">{t(s.holdings?.length ? "sim.scenario.built" : SCENARIO_LABEL_KEY[s.index], lang)}</div>
      {s.description && <p className="small" style={{ marginTop: 6 }}>{s.description}</p>}
      {s.proxyNote && <p className="muted small" style={{ marginTop: 4 }}>{s.proxyNote}</p>}
      {s.holdings?.length ? <BuiltPortfolio run={run} s={s} lang={lang} /> : null}
      {s.allocation?.length && !s.holdings?.length ? (
        <>
          <div className="section-title" style={{ margin: "10px 0 4px" }}>{t("sim.allocation", lang)}</div>
          {s.allocation.map((a) => (
            <div key={a.label} className="alloc-row">
              <span className="small">{a.label}</span>
              <div className="alloc-bar"><span style={{ width: `${Math.min(100, a.weight)}%` }} /></div>
              <span className="small muted">{a.weight.toFixed(1)} %</span>
            </div>
          ))}
        </>
      ) : null}
      {s.metrics && (
        <table className="tbl" style={{ marginTop: 10 }}>
          <tbody>
            {Object.entries(s.metrics).map(([key, evId]) => {
              const ev = metric(evId);
              return (
                <tr key={key}>
                  <td className="small">{t(`sim.metric.${key}`, lang)}</td>
                  <td className="small" style={{ textAlign: "right" }}>
                    {ev?.formatted ?? <span className="muted small">{t("app.unresolved", lang)}</span>}
                  </td>
                  <td className="small" style={{ width: 56 }}><EvidenceBadge ev={ev} lang={lang} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

/** Règles R1-R10 : libellé par motif (lot A), badge neutre pour « non déclenchée »,
 *  citations seulement pour une règle déclenchée (lot A : les anciens runs en contiennent sur des pass). */
/** Mode build : portefeuille construit en liste à puces (pas de graphique), chaque chiffre relié à sa preuve EV-nn. */
function BuiltPortfolio({ run, s, lang }: { run: Run; s: Scenario; lang: Lang }) {
  const ev = (id?: string) => run.evidence.find((e) => e.id === id);
  const fmt = (template: string, values: Record<string, string | number | undefined>) =>
    Object.entries(values).reduce((text, [k, v]) => text.replace(`{${k}}`, String(v ?? "")), template);
  const paramText = (p: NonNullable<Scenario["parameters"]>[number]) => {
    const value = Array.isArray(p.value)
      ? (p.value as (string | { industry: string; minWeight?: number | null })[])
          .map((x) => (typeof x === "string" ? x : x.minWeight ? `${x.industry} (${t("mandate.minWeight", lang)} ${Math.round(x.minWeight * 100)} %)` : x.industry))
          .join(", ")
      : p.value;
    return fmt(t(`sim.built.${p.key}`, lang), { value, riskProfile: p.riskProfile });
  };
  return (
    <>
      <p className="muted small" style={{ marginTop: 6 }}>{t("sim.built.notice", lang)}</p>
      <div className="section-title" style={{ margin: "10px 0 4px" }}>{t("sim.built.holdings", lang)}</div>
      <ul className="built-holdings small">
        {s.holdings!.map((h) => (
          <li key={h.symbol}>
            <strong>{h.symbol}</strong> — {h.name} ({h.industry}) : {ev(h.evidence.weight)?.formatted ?? `${h.weight.toFixed(1)} %`}{" "}
            <EvidenceBadge ev={ev(h.evidence.weight)} lang={lang} />
            <span className="muted">
              {" · "}{t("sim.built.beta", lang)} {ev(h.evidence.beta)?.formatted}
              {" · "}{t("sim.built.expected", lang)} {ev(h.evidence.expectedReturn)?.formatted}
            </span>{" "}
            <EvidenceBadge ev={ev(h.evidence.expectedReturn)} lang={lang} />
          </li>
        ))}
      </ul>
      {s.parameters?.length ? (
        <>
          <div className="section-title" style={{ margin: "10px 0 4px" }}>{t("sim.built.parameters", lang)}</div>
          <ul className="built-holdings small muted">
            {s.parameters.map((p) => <li key={p.key}>{paramText(p)}{p.evidence ? <> <EvidenceBadge ev={ev(p.evidence)} lang={lang} /></> : null}</li>)}
          </ul>
        </>
      ) : null}
    </>
  );
}

function RuleTable({ run, lang }: { run: Run; lang: Lang }) {
  const byScenario = new Map<number, RuleVerdict[]>();
  for (const v of run.verdicts) {
    const k = v.scenario ?? -1;
    (byScenario.get(k) ?? byScenario.set(k, []).get(k)!).push(v);
  }
  // Les citations sous une règle non déclenchée se liraient comme un accord (GN-3200-26-001, 2.1.1).
  const citationsOf = (v: RuleVerdict): string[] =>
    v.status === "warn" || v.status === "fail" ? (v.citations ?? []) : [];
  return (
    <>
      <h3 className="section-title">{t("sim.rules", lang)}</h3>
      {[...byScenario.entries()].map(([sc, list]) => (
        <div key={sc} style={{ marginBottom: 12 }}>
          {sc >= 0 && <div className="muted small">{t(sc === 1 && run.scenarios.find((x) => x.index === 1)?.holdings?.length ? "sim.scenario.built" : SCENARIO_LABEL_KEY[sc] ?? "", lang)}</div>}
          <table className="tbl">
            <thead><tr><th>{t("sim.rules", lang)}</th><th /></tr></thead>
            <tbody>
              {list.map((v, i) => (
                <tr key={i}>
                  <td className="small">
                    <strong>{v.rule}</strong> <span className={ruleBadgeClass(v.reasonCode, v.status)}>{ruleLabel(v.reasonCode, v.status, lang)}</span>
                    <br />
                    {v.message ?? v.messageEn ?? ""}
                    {v.threshold && (
                      <span className="muted small"> · {t("sim.rule.threshold", lang)} : {v.threshold.value}
                        {v.threshold.nature === "team_assumption" ? ` (${t("app.teamAssumption", lang)})` : ""}
                      </span>
                    )}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {citationsOf(v).map((c) => <EvidenceBadge key={c} ev={run.evidence.find((e) => e.id === c)} lang={lang} />)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}

const SECTION_ORDER = ["data_used", "why", "limits", "what_would_change"] as const;

/** Citations fixées par le code du backend (lot E2) : à côté des mentions, jamais sous une règle. */
function NoticeCitations({ run, lang, rule, titleKey }: { run: Run; lang: Lang; rule: "R5" | "R9"; titleKey: string }) {
  const ids = run.noticeCitations?.[rule];
  if (!ids?.length) return null;
  return (
    <div style={{ marginTop: 6 }}>
      <p className="muted small" style={{ marginBottom: 4 }}>{t(titleKey, lang)}</p>
      <div className="suggest">
        {ids.map((id) => <EvidenceBadge key={id} ev={run.evidence.find((e) => e.id === id)} lang={lang} />)}
      </div>
    </div>
  );
}

/** Mentions fixes du lot D : affichées à chaque affichage de résultats, y compris en partial. */
function FixedNotices({ run, lang }: { run: Run; lang: Lang }) {
  return (
    <div className="notice" role="note">
      <p className="small pre">{t("app.fixedNotice.decisions", lang)}<br />
        {t("app.fixedNotice.simulation", lang)}<br />
        {t("app.fixedNotice.generic", lang)}<br />
        {(t("app.fixedNotice.universe", lang) as string).replace("{datasetVersion}", run.datasetVersion)}</p>
    </div>
  );
}

export default function SimulationPanel({ run, lang, compareCategory, onCompare, onRerun, busy }: {
  run: Run | null;
  lang: Lang;
  /** compareCategory du mandat confirmé actuel (lot B) : sert au bouton « Retirer la comparaison ». */
  compareCategory?: string;
  /** Présent = le bouton de comparaison est actif ; reçoit la nouvelle version du mandat à confirmer. */
  onCompare?: (req: { compareCategory?: import("../../lib/comparisonCategories").ComparisonCategoryId }) => void;
  /** Ancien run (sans rulesVersion) : relance l'analyse sur le même mandat. */
  onRerun?: () => void;
  busy?: boolean;
}) {
  const narrative = run?.narrative;
  const [choosing, setChoosing] = useState(false);
  const hasComparison = !!run?.scenarios.some((s) => s.index === 2);
  return (
    <aside className="sim-panel" aria-label={t("sim.title", lang)}>
      <div className="sim-scroll">
        <div className="banner" style={{ background: "var(--ghost)" }}>
          <p className="small"><strong>{t("app.disclaimer", lang)}</strong></p>
        </div>
        {run?.jurisdictionNotices?.length ? (
          <div className="banner warn">
            <p className="small">{run.jurisdictionNotices.map((n, i) => <span key={i} className="pre">{n}<br /></span>)}</p>
            <NoticeCitations run={run} lang={lang} rule="R9" titleKey="sim.notice.fixedR9" />
          </div>
        ) : null}

        {!run && <p className="muted">{t("sim.empty", lang)}</p>}

        {run?.status === "error" && <div className="banner warn"><p>{t("chat.runError", lang)}</p></div>}

        {run && run.status !== "error" && (
          <>
            {(run.rulesVersion ?? 0) < 2 && (
              <div className="banner warn">
                <p className="small">{t("sim.oldRun", lang)}</p>
                {onRerun && <button type="button" className="btn-ghost" disabled={busy} onClick={onRerun}>{t("sim.rerun", lang)}</button>}
              </div>
            )}
            <h2 className="section-title" style={{ marginTop: 12 }}>{t("sim.scenarios", lang)}</h2>
            <div className={`scenario-grid${run.scenarios.length < 3 ? " two" : ""}`}>
              {run.scenarios.map((s) => <ScenarioCard key={s.index} run={run} s={s} lang={lang} />)}
            </div>
            {run.status === "partial" && <p className="muted small">{t("sim.partialHint", lang)}</p>}
            <FixedNotices run={run} lang={lang} />
            <NoticeCitations run={run} lang={lang} rule="R5" titleKey="sim.notice.fixedR5" />
            {onCompare && (
              <CompareCategoryButton lang={lang} busy={busy} onOpen={() => setChoosing(true)} />
            )}
            {onCompare && choosing && (
              <CompareCategory
                lang={lang}
                currentId={compareCategory as import("../../lib/comparisonCategories").ComparisonCategoryId | undefined}
                onClose={() => setChoosing(false)}
                onChoose={(id) => { setChoosing(false); onCompare({ compareCategory: id }); }}
                onRemove={() => { setChoosing(false); onCompare({}); }}
              />
            )}

            {run.verdicts.length > 0 && <RuleTable run={run} lang={lang} />}

            {narrative && (
              <>
                <h3 className="section-title">{t("sim.narrative", lang)}</h3>
                {narrative.sections
                  .slice()
                  .sort((a, b) => SECTION_ORDER.indexOf(a.key) - SECTION_ORDER.indexOf(b.key))
                  .map((sec) => (
                    <section key={sec.key}>
                      <div className="section-title" style={{ margin: "10px 0 4px" }}>{t(`sim.section.${sec.key}`, lang)}</div>
                      <p className="small pre">
                        <EvidenceText text={sec.text} evidence={run.evidence} lang={lang} />
                      </p>
                    </section>
                  ))}
                {narrative.hiddenSentences?.length ? (
                  <p className="muted small">
                    {narrative.hiddenSentences.length} phrase(s) masquée(s) par le vérificateur
                    {narrative.hiddenSentences.map((h, i) => <span key={i}> · {h.reason}</span>)}
                  </p>
                ) : null}
              </>
            )}

            {run.verifier && (
              <>
                <h3 className="section-title">{t("sim.verifier", lang)}</h3>
                <div className="stats" style={{ padding: 0 }}>
                  <div className="stat"><div className="stat-label">{t("sim.verifier.placeholders", lang)}</div><div className="stat-value filled" style={{ fontSize: 20 }}>{run.verifier.placeholdersResolved}/{run.verifier.placeholdersTotal}</div></div>
                  <div className="stat"><div className="stat-label">{t("sim.verifier.handwritten", lang)}</div><div className="stat-value filled" style={{ fontSize: 20 }}>{run.verifier.handwrittenNumbers}</div></div>
                  <div className="stat"><div className="stat-label">{t("sim.verifier.forbidden", lang)}</div><div className="stat-value filled" style={{ fontSize: 20 }}>{run.verifier.forbiddenPhrases}</div></div>
                  <div className="stat"><div className="stat-label">{t("sim.verifier.match", lang)}</div><div className="stat-value filled" style={{ fontSize: 20 }}>{run.verifier.placeholdersMatch ? "✓" : "✕"}</div></div>
                </div>
              </>
            )}

            {run.explanation && <div style={{ marginTop: 12 }}><Explanation data={run.explanation} /></div>}
          </>
        )}
      </div>
    </aside>
  );
}
