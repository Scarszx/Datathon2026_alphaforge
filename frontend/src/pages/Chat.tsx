/* Page /chat : session en 3 colonnes du contrat (srv-frontend) :
 *   1. portefeuille + mandat avec curseurs « et si »
 *   2. conversation (quickReplies, carte de mandat proposé)
 *   3. panneau de simulation (scénarios, verdicts, citations, explication)
 * plus le menu latéral d'historique. Le front ne calcule rien : chiffres de /summary et du registre du run. */
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, errorText } from "../api/errors";
import {
  createConversation, createMandate, createRun, getRun, listConversations, listMandates,
  listMessages, listPortfolios, getSummary, sendMessage,
} from "../api/endpoints";
import type { Conversation, Evidence, Mandate, MandateCreateRequest, Message, PortfolioSummary, Run } from "../api/types";
import AppHeader from "./../components/AppHeader";
import ConversationColumn from "./../components/chat/ConversationColumn";
import MandateColumn from "./../components/chat/MandateColumn";
import SimulationPanel from "./../components/chat/SimulationPanel";
import { LangContext, langOf, t, type Lang } from "./../lib/i18n";

const POLL_MS = 2000;
const tmpId = () => `tmp-${Date.now()}`;

export default function Chat() {
  /* --- historique (menu latéral) --- */
  const [sessions, setSessions] = useState<Conversation[]>([]);
  const [q, setQ] = useState("");
  const [activeId, setActiveId] = useState<string | null>(null);
  const activeRef = useRef<string | null>(null);
  activeRef.current = activeId;

  /* --- données de la session --- */
  const [messages, setMessages] = useState<Message[]>([]);
  const [mandate, setMandate] = useState<Mandate | null>(null);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [lang, setLang] = useState<Lang>(langOf(navigator.language));

  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  /* --- historique : liste des sessions --- */
  useEffect(() => {
    listConversations().then((p) => setSessions(p.items)).catch(() => { /* le rail reste vide */ });
  }, []);

  const refreshMandate = useCallback(async (sessionId: string) => {
    try {
      const { items } = await listMandates(sessionId); // plus récent d'abord
      setMandate(items[0] ?? null);
      return items[0] ?? null;
    } catch { setMandate(null); return null; }
  }, []);

  /* --- ouverture d'une session : messages, mandat, portefeuille, dernier run --- */
  const openSession = useCallback(async (sessionId: string | null) => {
    setActiveId(sessionId); activeRef.current = sessionId;
    setMessages([]); setMandate(null); setRun(null); setRunId(null); setError("");
    if (!sessionId) return;
    setLoading(true);
    try {
      const all: Message[] = [];
      let cursor: string | undefined;
      for (let i = 0; i < 20; i++) { // ordre chronologique : toutes les pages
        const p = await listMessages(sessionId, cursor);
        all.push(...p.items);
        if (!p.nextCursor) break;
        cursor = p.nextCursor;
      }
      if (activeRef.current !== sessionId) return;
      setMessages(all);
      const conv = sessions.find((c) => c.sessionId === sessionId);
      if (conv?.userLanguage) setLang(langOf(conv.userLanguage));

      await refreshMandate(sessionId);

      try {
        const { items } = await listPortfolios();
        const main = items.find((p) => p.portfolioId === "main") ?? items[0];
        if (main) getSummary(main.portfolioId, "1y").then(setSummary).catch(() => setSummary(null));
      } catch { /* portefeuille indisponible : la colonne reste vide */ }

      const lastRunId = [...all].reverse().find((m) => m.role === "assistant" && m.runId)?.runId;
      if (lastRunId) {
        const r = await getRun(sessionId, lastRunId).catch(() => null);
        if (r && activeRef.current === sessionId) { setRun(r); setRunId(r.runId); }
      }
      await refreshMandate(sessionId);
    } catch (e) {
      if (activeRef.current === sessionId) setError(errorText(e));
      if (e instanceof ApiError && e.code === "CONVERSATION_NOT_FOUND") {
        setSessions((s) => s.filter((x) => x.sessionId !== sessionId));
      }
    } finally {
      if (activeRef.current === sessionId) setLoading(false);
    }
  }, [refreshMandate, sessions]);

  /* --- envoi d'un message (cadrage, suivi, « et si » en texte libre) --- */
  const send = useCallback(async (text: string) => {
    if (!text.trim() || busy) return;
    setError(""); setBusy(true);
    let sid = activeRef.current;
    const optimistic: Message = { messageId: tmpId(), sessionId: sid ?? "", role: "user", content: text, status: "done", createdAt: new Date().toISOString() };
    try {
      if (!sid) {
        const c = await createConversation(text.slice(0, 40));
        sid = c.sessionId;
        activeRef.current = sid;
        setActiveId(sid);
        setSessions((l) => [c, ...l]);
        setMessages([]);
      }
      setMessages((m) => [...m, optimistic]);
      const r = await sendMessage(sid, text);
      if (activeRef.current !== sid) return;
      setMessages((m) => [...m.filter((x) => x.messageId !== optimistic.messageId), r.userMessage, r.assistantMessage]);
      if (r.assistantMessage.runId) setRunId(r.assistantMessage.runId);
      // L'orchestrateur fixe userLanguage à la première réponse : la colonne suit.
      setSessions((l) => l.map((c) => (c.sessionId === sid ? { ...c, updatedAt: r.assistantMessage.createdAt } : c)));
    } catch (e) {
      if (activeRef.current === sid) setMessages((m) => m.filter((x) => x.messageId !== optimistic.messageId));
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }, [busy]);

  /* --- confirmation d'un mandat (brouillon modifié ou curseurs) : POST mandates puis POST runs --- */
  const confirmMandate = useCallback(async (m: MandateCreateRequest) => {
    const sid = activeRef.current;
    if (!sid || busy) return;
    setError(""); setBusy(true);
    try {
      const full: MandateCreateRequest = {
        ...m,
        portfolioId: m.portfolioId || "main",
        userLanguage: m.userLanguage || (lang === "en" ? "en" : "fr"),
      };
      const created = await createMandate(sid, full);
      if (activeRef.current !== sid) return;
      setMandate(created);
      const r = await createRun(sid, created.version);
      if (activeRef.current !== sid) return;
      setRun(r); setRunId(r.runId);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }, [busy, lang]);

  /* --- relecture du run : partial → done (affichage progressif) --- */
  useEffect(() => {
    const sid = activeRef.current;
    if (!runId || !sid || run?.status !== "partial") return;
    const timer = setTimeout(async () => {
      try {
        const r = await getRun(sid, runId);
        if (activeRef.current !== sid) return;
        setRun(r);
        if (r.status === "done") {
          // Le message de l'assistant qui porte le run affiche ses emplacements : preuves à jour.
          setMessages((ms) => ms.map((m) => (m.runId === runId ? { ...m } : m)));
        }
      } catch { /* nouvelle tentative au prochain cycle */ }
    }, POLL_MS);
    return () => clearTimeout(timer);
  }, [run, runId]);

  /* --- langue d'affichage : userLanguage de la conversation active --- */
  useEffect(() => {
    const conv = sessions.find((c) => c.sessionId === activeId);
    if (conv?.userLanguage) setLang(langOf(conv.userLanguage));
  }, [sessions, activeId]);

  const evidence: Evidence[] = run?.evidence ?? [];
  const filtered = sessions.filter((c) => (c.title ?? "").toLowerCase().includes(q.trim().toLowerCase()));

  return (
    <LangContext.Provider value={lang}>
      <AppHeader />
      <main className="chat-page">
        <aside className="af-side chat-rail">
          <button type="button" className="af-new" onClick={() => void openSession(null)}>+ {t("chat.new", lang)}</button>
          <input className="af-search" placeholder={t("chat.search", lang)} aria-label={t("chat.search", lang)} value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="af-lists">
            <h3 className="af-label">{t("chat.history", lang)}</h3>
            <ul className="af-list">
              {filtered.map((c) => (
                <li key={c.sessionId} className={`af-row${c.sessionId === activeId ? " sel" : ""}`}>
                  <button type="button" className="af-conv" onClick={() => void openSession(c.sessionId)}>
                    <strong>{c.title || t("chat.untitled", lang)}</strong>
                    <span>{new Date(c.updatedAt).toLocaleDateString()}</span>
                  </button>
                </li>
              ))}
              {!filtered.length && <li className="af-empty">{q ? "—" : t("chat.history", lang)}</li>}
            </ul>
          </div>
        </aside>

        <div className="chat-grid">
          <MandateColumn summary={summary} mandate={mandate} busy={busy} lang={lang}
            onWhatIf={(m) => void confirmMandate(m)} />
          <ConversationColumn messages={messages} evidence={evidence} busy={busy} lang={lang}
            onSend={(text) => void send(text)} onQuickReply={(text) => void send(text)}
            onConfirmDraft={(m) => void confirmMandate(m)} />
          <SimulationPanel run={run} lang={lang} />
        </div>
        {loading && <p className="muted small chat-loading">Chargement…</p>}
        {error && <div className="chat-error" role="alert"><p className="error">{error}</p></div>}
      </main>
    </LangContext.Provider>
  );
}
