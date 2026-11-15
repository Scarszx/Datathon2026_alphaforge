import { useEffect, useId, useRef, useState } from "react";
import { useT } from "../lib/i18n";

/** Petite bulle « ? » qui explique en une ou deux phrases comment un chiffre est calculé.
 *  Ouverture au clic (et au clavier), fermeture avec Échap ou un clic à l'extérieur. */
export default function InfoTip({ text }: { text: string }) {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const id = useId();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    const onDown = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDown);
    return () => { document.removeEventListener("keydown", onKey); document.removeEventListener("mousedown", onDown); };
  }, [open]);
  return (
    <span className="infotip" ref={ref}>
      <button type="button" className="infotip-btn" aria-label={t("info.label")} aria-expanded={open} aria-controls={id} onClick={() => setOpen((v) => !v)}>?</button>
      {open && <span id={id} role="note" className="infotip-bubble">{text}</span>}
    </span>
  );
}
