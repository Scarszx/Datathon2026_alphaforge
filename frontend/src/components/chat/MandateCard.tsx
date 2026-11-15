/* Carte de mandat : affiche les champs d'un MandateCreateRequest (brouillon proposé par l'orchestrateur
 * ou mandat confirmé), avec la source de chaque ligne quand elle est connue (fieldSources du contrat). */
import type { Mandate, MandateCreateRequest } from "../../api/types";
import { t, warningText, type Lang } from "../../lib/i18n";
import { categoryOf } from "../../lib/comparisonCategories";
import { PROVINCE_LABELS } from "../../lib/risk";

export function FieldSourceTag({ field, mandate, lang }: { field: string; mandate: MandateCreateRequest; lang: Lang }) {
  const src = mandate.fieldSources?.[field];
  if (!src) return null;
  return <span className="tag">{t(`col.source.${src}`, lang)}</span>;
}

export default function MandateCard({ mandate, confirmed, lang }: { mandate: MandateCreateRequest; confirmed?: Mandate; lang: Lang }) {
  const op = (action: string) => t(`mandate.operation.${action}`, lang);
  return (
    <div className="profile-card mandate-card">
      <div className="eyebrow">{t("col.mandate", lang)}{confirmed ? ` · ${t("col.mandateVersion", lang)} ${confirmed.version}` : ""}</div>
      <table className="tbl">
        <tbody>
          <tr><td>{t("mandate.mode", lang)}</td><td>{t(`mandate.mode.${mandate.mode}`, lang)} <FieldSourceTag field="mode" mandate={mandate} lang={lang} /></td></tr>
          <tr><td>{t("mandate.objective", lang)}</td><td>{t(`mandate.objective.${mandate.objective}`, lang)}{mandate.objectiveDetail ? ` — ${mandate.objectiveDetail}` : ""} <FieldSourceTag field="objective" mandate={mandate} lang={lang} /></td></tr>
          <tr><td>{t("mandate.horizon", lang)}</td><td>{mandate.horizonYears} {t("mandate.years", lang)} <FieldSourceTag field="horizonYears" mandate={mandate} lang={lang} /></td></tr>
          <tr><td>{t("mandate.riskTolerance", lang)}</td><td>{mandate.riskTolerance} / 5 <FieldSourceTag field="riskTolerance" mandate={mandate} lang={lang} /></td></tr>
          <tr><td>{t("mandate.riskCapacity", lang)}</td><td>{mandate.riskCapacity} / 5 <FieldSourceTag field="riskCapacity" mandate={mandate} lang={lang} /></td></tr>
          <tr><td>{t("mandate.maxLoss", lang)}</td><td>
            {confirmed
              ? `${confirmed.effectiveMaxLossPct} %`
              : mandate.maxAcceptableLossPct !== undefined ? `${mandate.maxAcceptableLossPct} %` : "—"}
            {" "}<FieldSourceTag field="maxAcceptableLossPct" mandate={mandate} lang={lang} />
            {confirmed && <span className="muted small"> · {t("mandate.riskProfile", lang)} : {confirmed.riskProfile}</span>}
          </td></tr>
          {mandate.compareCategory && (
            <tr><td>{t("sim.scenario.alternative", lang)}</td><td>{categoryOf(mandate.compareCategory)?.label[lang] ?? mandate.compareCategory} <FieldSourceTag field="compareCategory" mandate={mandate} lang={lang} /></td></tr>
          )}
          {mandate.subjectTicker && <tr><td>{t("mandate.subject", lang)}</td><td><strong>{mandate.subjectTicker}</strong> <FieldSourceTag field="subjectTicker" mandate={mandate} lang={lang} /></td></tr>}
          {mandate.operations?.length ? (
            <tr><td>{t("mandate.operations", lang)}</td><td>
              <ul className="mandate-ops">
                {mandate.operations.map((o, i) => (
                  <li key={i}>
                    {op(o.action)} {o.ticker}
                    {o.amount !== undefined ? ` · ${o.amount} ${o.currency ?? ""}` : ""}
                    {o.weight !== undefined ? ` · ${o.weight} %` : ""}
                  </li>
                ))}
              </ul>
            </td></tr>
          ) : null}
          {mandate.constraints?.length ? <tr><td>{t("mandate.constraints", lang)}</td><td>{mandate.constraints.join(", ")}</td></tr> : null}
          {mandate.preferences?.esg ? <tr><td>{t("mandate.preferences.esg", lang)}</td><td>✓</td></tr> : null}
          <tr><td>{t("mandate.province", lang)}</td><td>{PROVINCE_LABELS[mandate.province]} ({mandate.province})</td></tr>
        </tbody>
      </table>
      {confirmed?.warnings?.length ? (
        <div className="banner warn" style={{ marginTop: 10 }}>
          <p className="small">
            <strong>{t("mandate.warnings", lang)}</strong> · <span className="muted">{t("mandate.warningsAssumption", lang)}</span>
            <br />{confirmed.warnings.map((w, i) => <span key={i} className="pre">{warningText(w, lang)}<br /></span>)}
          </p>
        </div>
      ) : null}
      {confirmed?.changedFields?.length ? (
        <p className="muted small" style={{ marginTop: 8 }}>
          {t("mandate.changed", lang)} : {confirmed.changedFields.join(", ")}
        </p>
      ) : null}
      {confirmed && <p className="muted small" style={{ marginTop: 8 }}>{t("mandate.confirmedAt", lang)} {new Date(confirmed.confirmedAt).toLocaleString()}</p>}
    </div>
  );
}
