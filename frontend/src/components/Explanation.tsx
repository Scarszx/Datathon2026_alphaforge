import type { Explanation as Expl, ExplanationCheck } from "../api/types";

const CHECK_LABEL: Record<ExplanationCheck["status"], string> = {
  pass: "Conforme", warn: "Attention", fail: "Non conforme", not_verified: "Non vérifié",
};
const STEP_LABEL = { ok: "ok", error: "erreur", empty: "aucun résultat" } as const;

/** Affiche tel quel le champ explanation renvoyé par le back (contrat : toujours affiché). */
export default function Explanation({ data, defaultOpen = false }: { data: Expl; defaultOpen?: boolean }) {
  const checks = data.checks ?? [];
  return (
    <details className="expl" open={defaultOpen}>
      <summary>
        Explication
        {checks.length > 0 && checks.map((c, i) => <span key={i} className={`badge ${c.status}`} title={c.message}>{CHECK_LABEL[c.status]}</span>)}
      </summary>
      <div className="expl-body">
        {checks.length > 0 && (
          <section>
            <h4>Contrôles de gouvernance</h4>
            <ul>{checks.map((c, i) => <li key={i}><span className={`badge ${c.status}`}>{CHECK_LABEL[c.status]}</span> <code>{c.rule}</code> ({c.agentId}) : {c.message}</li>)}</ul>
          </section>
        )}
        {data.sources.length > 0 && (
          <section>
            <h4>Sources</h4>
            <ul>{data.sources.map((s) => <li key={s.id}><strong>{s.id}</strong>{s.dataset && <> · <code>{s.dataset}</code></>}{s.asOf && <> · au {s.asOf}</>}{s.note && <> · {s.note}</>}</li>)}</ul>
          </section>
        )}
        {data.steps.length > 0 && (
          <section>
            <h4>Étapes exécutées</h4>
            <ul>{data.steps.map((s, i) => (
              <li key={i}><code>{s.agentId}</code> → <code>{s.tool}</code>{s.params && Object.keys(s.params).length > 0 && <> <span className="muted">{JSON.stringify(s.params)}</span></>} · {STEP_LABEL[s.status]}{s.durationMs != null && <> · {s.durationMs} ms</>}</li>
            ))}</ul>
          </section>
        )}
        {!!data.assumptions?.length && (
          <section><h4>Hypothèses</h4><ul>{data.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul></section>
        )}
        {!!data.limitations?.length && (
          <section><h4>Limites</h4><ul>{data.limitations.map((a, i) => <li key={i}>{a}</li>)}</ul></section>
        )}
      </div>
    </details>
  );
}
