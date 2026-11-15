import type { Explanation as Expl } from "../api/types";
import { useT } from "../lib/i18n";
import { ruleBadgeClass, ruleLabel } from "../lib/ruleLabels";

/** Affiche tel quel le champ explanation renvoyé par le back (contrat : toujours affiché).
 *  Libellés fixes traduits ; sources, étapes, hypothèses et limites viennent du back.
 *  0.4.4 : les contrôles portent reasonCode et scenario ; l'agentId reste dans « Étapes exécutées ». */
export default function Explanation({ data, defaultOpen = false }: { data: Expl; defaultOpen?: boolean }) {
  const { t, lang } = useT();
  const checks = data.checks ?? [];
  return (
    <details className="expl" open={defaultOpen}>
      <summary>
        {t("expl.title")}
        {checks.length > 0 && checks.map((c, i) => {
          const status = c.status;
          return <span key={i} className={ruleBadgeClass(c.reasonCode ?? "", status)} title={c.message}>{ruleLabel(c.reasonCode ?? "", status, lang)}</span>;
        })}
      </summary>
      <div className="expl-body">
        {checks.length > 0 && (
          <section>
            <h4>{t("expl.checks")}</h4>
            <ul>{checks.map((c, i) => (
              <li key={i}>
                <span className={ruleBadgeClass(c.reasonCode ?? "", c.status)}>{ruleLabel(c.reasonCode ?? "", c.status, lang)}</span>{" "}
                <code>{c.rule}</code>{c.scenario !== undefined ? ` · ${t("proof.scenario")} ${c.scenario}` : ""} : {c.message}
              </li>
            ))}</ul>
          </section>
        )}
        {data.sources.length > 0 && (
          <section>
            <h4>{t("expl.sources")}</h4>
            <ul>{data.sources.map((s) => <li key={s.id}><strong>{s.id}</strong>{s.dataset && <> · <code>{s.dataset}</code></>}{s.asOf && <> · {t("expl.asOf")} {s.asOf}</>}{s.note && <> · {s.note}</>}</li>)}</ul>
          </section>
        )}
        {data.steps.length > 0 && (
          <section>
            <h4>{t("expl.steps")}</h4>
            <ul>{data.steps.map((s, i) => (
              <li key={i}><code>{s.agentId}</code> → <code>{s.tool}</code>{s.params && Object.keys(s.params).length > 0 && <> <span className="muted">{JSON.stringify(s.params)}</span></>} · {t(`expl.step.${s.status}`)}{s.durationMs != null && <> · {s.durationMs} ms</>}</li>
            ))}</ul>
          </section>
        )}
        {!!data.assumptions?.length && (
          <section><h4>{t("expl.assumptions")}</h4><ul>{data.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul></section>
        )}
        {!!data.limitations?.length && (
          <section><h4>{t("expl.limitations")}</h4><ul>{data.limitations.map((a, i) => <li key={i}>{a}</li>)}</ul></section>
        )}
      </div>
    </details>
  );
}
