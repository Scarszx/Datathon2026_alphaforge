/* Choix d'une catégorie d'actifs pour la comparaison (scénario 2, lot B, contrat 0.4.5).
 * Liste triée par niveau, SANS présélection (GN-3200-26-001, 2.1.1 et 3.2) et sans symbole de FNB.
 * Choisir une catégorie crée une NOUVELLE VERSION du mandat avec compareCategory, exactement
 * comme les curseurs « et si » ; « Retirer la comparaison » crée une version sans ce champ. */
import { categoriesByLevel, isCategoryId, type ComparisonCategoryId } from "../../lib/comparisonCategories";
import { t, type Lang } from "../../lib/i18n";

export type CompareRequest = { compareCategory?: ComparisonCategoryId };

export function CompareCategoryButton({ lang, busy, onOpen }: {
  lang: Lang; busy?: boolean; onOpen: () => void;
}) {
  return (
    <button type="button" className="btn-ghost" disabled={busy} onClick={onOpen} style={{ marginTop: 10 }}>
      {t("sim.compare", lang)}
    </button>
  );
}

export default function CompareCategory({ lang, currentId, onChoose, onRemove, onClose }: {
  lang: Lang;
  currentId?: ComparisonCategoryId;
  onChoose: (id: ComparisonCategoryId) => void;
  onRemove?: () => void;
  onClose: () => void;
}) {
  return (
    <div className="expl" style={{ marginTop: 10 }}>
      <div className="expl-body">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
          <h4 style={{ marginBottom: 0 }}>{t("sim.compareTitle", lang)}</h4>
          <button type="button" className="link" onClick={onClose}>✕</button>
        </div>
        <p className="muted small" style={{ margin: 0 }}>{t("sim.compareHint", lang)}</p>
        <ul className="opts" style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {categoriesByLevel().map((c) => (
            <li key={c.id} style={{ marginBottom: 6 }}>
              <button
                type="button"
                className="chip"
                onClick={() => onChoose(c.id)}
                title={currentId === c.id ? undefined : undefined}
              >
                {c.label[lang]} <span className="muted small">· {t("sim.compareLevel", lang)} {c.level}</span>
              </button>
            </li>
          ))}
        </ul>
        {currentId && onRemove && (
          <button type="button" className="btn-ghost" onClick={onRemove}>{t("sim.compareRemove", lang)}</button>
        )}
      </div>
    </div>
  );
}

/* Garde-fou : un identifiant inconnu n'est jamais envoyé au backend (VALIDATION_ERROR). */
export const safeCategoryId = (v: string): ComparisonCategoryId | null => (isCategoryId(v) ? v : null);
