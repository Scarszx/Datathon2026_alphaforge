/* Panneau de simulation (colonne 3 de /chat) : scénarios 0/1/2 côte à côte, verdicts R1-R10 avec badge KB,
 * les 4 rubriques de narrative, le score du vérificateur, les mentions R9 et la mention permanente.
 * Affichage progressif : tout ce qui existe en status = partial s'affiche déjà ; le reste arrive à done. */
import { useState } from "react";
import type { RuleVerdict, Run, Scenario } from "../../api/types";
import { t, type Lang } from "../../lib/i18n";
import EvidenceText, { EvidenceBadge } from "./EvidenceText";

const SCENARIO_LABEL_KEY = ["sim.scenario.current", "sim.scenario.idea", "sim.scenario.alternative"] as const;

function Pill({ status, lang }: { status: string; lang: Lang }) {
  const cls = status === "pass" ? "up" : status === "fail" ? "down" : status === "warn" ? "warn" : "";
  return <span className={`pill ${cls}`}>{t(`sim.verdict.${status}`, lang) ?? status}</span>;
}

/** Une colonne de scénario : label, pastille, répartition, mesures résolues depuis run.evidence. */
function ScenarioCard({ run, s, lang }: { run: Run; s: Scenario; lang: Lang }) {
  const metric = (evId?: string) => run.evidence.find((e) => e.id === evId);
  return (
    <div className="scenario-card">
      <div className="scenario-head">
        <strong>{s.label}</strong>
        <Pill status={s.verdict} lang={lang} />
      </div>
      <div className="muted small">{t(SCENARIO_LABEL_KEY[s.index], lang)}</div>
      {s.description && <p className="small" style={{ marginTop: 6 }}>{s.description}</p>}
      {s.proxyNote && <p className="muted small" style={{ marginTop: 4 }}>{s.proxyNote}</p>}
      {s.allocation?.length ? (
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

/** Verdicts R1-R10, avec badge KB quand la citation est là (status done). */
function RuleTable({ run, lang }: { run: Run; lang: Lang }) {
  const byScenario = new Map<number, RuleVerdict[]>();
  for (const v of run.verdicts) {
    const k = v.scenario ?? -1;
    (byScenario.get(k) ?? byScenario.set(k, []).get(k)!).push(v);
  }
  return (
    <>
      <h3 className="section-title">{t("sim.rules", lang)}</h3>
      {[...byScenario.entries()].map(([sc, list]) => (
        <div key={sc} style={{ marginBottom: 12 }}>
          {sc >= 0 && <div className="muted small">{t(SCENARIO_LABEL_KEY[sc] ?? "", lang)}</div>}
          <table className="tbl">
            <thead><tr><th>{t("sim.rule.reasonCode", lang)}</th><th>{t("sim.rules", lang)}</th><th style={{ textAlign: "right" }} /></tr></thead>
            <tbody>
              {list.map((v, i) => (
                <tr key={i}>
                  <td className="small"><strong>{v.rule}</strong><br /><span className="muted small">{v.reasonCode}</span></td>
                  <td className="small">
                    {v.message ?? v.messageEn ?? ""}
                    {v.threshold && (
                      <span className="muted small"> · {t("sim.rule.threshold", lang)} : {v.threshold.value}
                        {v.threshold.nature === "team_assumption" ? ` (${t("app.teamAssumption", lang)})` : ""}
                      </span>
                    )}
                    {v.citations?.length ? <span> {v.citations.map((c) => <EvidenceBadge key={c} ev={run.evidence.find((e) => e.id === c)} lang={lang} />)}</span> : null}
                  </td>
                  <td style={{ textAlign: "right" }}><Pill status={v.status} lang={lang} /></td>
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

export default function SimulationPanel({ run, lang }: { run: Run | null; lang: Lang }) {
  const narrative = run?.narrative;
  return (
    <aside className="sim-panel" aria-label={t("sim.title", lang)}>
      <div className="sim-scroll">
        <div className="banner" style={{ background: "var(--ghost)" }}>
          <p className="small"><strong>{t("app.disclaimer", lang)}</strong></p>
        </div>
        {run?.jurisdictionNotices?.length ? (
          <div className="banner warn">
            <p className="small">{run.jurisdictionNotices.map((n, i) => <span key={i} className="pre">{n}<br /></span>)}</p>
          </div>
        ) : null}

        {!run && <p className="muted">{t("sim.empty", lang)}</p>}

        {run?.status === "error" && <div className="banner warn"><p>{t("chat.runError", lang)}</p></div>}

        {run && run.status !== "error" && (
          <>
            <h2 className="section-title" style={{ marginTop: 12 }}>{t("sim.scenarios", lang)}</h2>
            <div className="scenario-grid">
              {run.scenarios.map((s) => <ScenarioCard key={s.index} run={run} s={s} lang={lang} />)}
            </div>
            {run.status === "partial" && <p className="muted small">{t("sim.partialHint", lang)}</p>}

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
          </>
        )}
      </div>
    </aside>
  );
}
