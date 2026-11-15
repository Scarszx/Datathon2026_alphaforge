import type { Explanation as Expl } from "../api/types";
import { useT } from "../lib/i18n";

/** Affiche tel quel le champ explanation renvoyé par le back (contrat : toujours affiché).
 *  Libellés fixes traduits ; sources, étapes, hypothèses et limites viennent du back. */
export default function Explanation({ data, defaultOpen = false }: { data: Expl; defaultOpen?: boolean }) {
  const { t } = useT();
  const checks = data.checks ?? [];
  return (
    <details className="expl" open={defaultOpen}>
      <summary>
        {t("expl.title")}
        {checks.length > 0 && checks.map((c, i) => <span key={i} className={`badge ${c.status}`} title={c.message}>{t(`expl.status.${c.status}`)}</span>)}
      </summary>
      <div className="expl-body">
        {checks.length > 0 && (
          <section>
            <h4>{t("expl.checks")}</h4>
            <ul>{checks.map((c, i) => <li key={i}><span className={`badge ${c.status}`}>{t(`expl.status.${c.status}`)}</span> <code>{c.rule}</code> ({c.agentId}) : {c.message}</li>)}</ul>
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
