import { useT } from "../lib/i18n";

/** Bouton FR | EN : change la langue de toute l'interface (pas celle du chatbot, qui suit l'utilisateur). */
export default function LangSwitch() {
  const { lang, setLang } = useT();
  return (
    <div className="lang-switch" role="group" aria-label={lang === "en" ? "Interface language" : "Langue de l'interface"}>
      {(["fr", "en"] as const).map((l) => (
        <button key={l} type="button" className={l === lang ? "on" : undefined} aria-pressed={l === lang} onClick={() => setLang(l)}>{l.toUpperCase()}</button>
      ))}
    </div>
  );
}
