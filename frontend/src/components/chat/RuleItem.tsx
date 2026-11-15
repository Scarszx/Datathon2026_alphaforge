/* Règle R1 à R10 repliée sur une ligne : identifiant, nom court et libellé du motif.
 * « Voir plus » déroule le reste (motif, seuil, citations), pour ne pas tout afficher d'un coup.
 * Le libellé du motif reste visible replié : un verdict n'est jamais caché, seul son détail l'est. */
import { useId, useState, type ReactNode } from "react";
import { ruleName, t, type Lang } from "../../lib/i18n";
import { ruleBadgeClass, ruleLabel, type RuleStatus } from "../../lib/ruleLabels";

/** Bouton « Voir plus » / « Voir moins » (motif disclosure : aria-expanded, aria-controls). */
export function MoreToggle({ open, onToggle, controls, lang }: { open: boolean; onToggle: () => void; controls: string; lang: Lang }) {
  return (
    <button type="button" className="more-toggle" aria-expanded={open} aria-controls={controls} onClick={onToggle}>
      {t(open ? "app.showLess" : "app.showMore", lang)}
    </button>
  );
}

export default function RuleItem({ rule, reasonCode, status, lang, context, children }: {
  rule: string;
  reasonCode: string;
  status: RuleStatus;
  lang: Lang;
  /** Précision affichée après le nom, par exemple « Scénario 1 » dans la trace technique. */
  context?: string;
  /** Détail déroulé par « Voir plus ». Absent : pas de bouton. */
  children?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const name = ruleName(rule, lang);
  return (
    <li className={`rule-item${open ? " open" : ""}`}>
      <div className="rule-head">
        <strong className="rule-id">{rule}</strong>
        <span className="rule-main">
          {name && <span className="rule-name">{name}</span>}
          {context && <span className="rule-context">{context}</span>}
          <span className={ruleBadgeClass(reasonCode, status)}>{ruleLabel(reasonCode, status, lang)}</span>
        </span>
        {children ? <MoreToggle open={open} onToggle={() => setOpen((o) => !o)} controls={id} lang={lang} /> : null}
      </div>
      {children ? <div className="rule-more" id={id} hidden={!open}>{children}</div> : null}
    </li>
  );
}
