import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ApiError, errorText } from "../api/errors";
import {
  createConversation, deleteConversation, listConversations, listMessages, renameConversation, sendMessage,
} from "../api/endpoints";
import type { Conversation, Message } from "../api/types";
import Explanation from "./Explanation";
import { dateTimeFr } from "../lib/format";

const SUGGESTIONS = [
  "Comment se porte mon portefeuille ?",
  "Quelle est mon exposition au risque ?",
  "Mon portefeuille respecte-t-il mon profil investisseur ?",
  "Quels actifs pèsent le plus dans mon portefeuille ?",
  "Compare le rendement et la volatilité de RY.TO et AAPL sur 1 an.",
];
const MAX_LEN = 2000; // schema-message-create-request
const PIN_KEY = "alphaforge.pinned"; // l'API n'a pas de champ « épinglé » : les épingles restent dans ce navigateur
const tmpId = () => `tmp-${Date.now()}`;

const Icon = {
  chat: <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M5 5.5h14a1.5 1.5 0 0 1 1.5 1.5v8.5a1.5 1.5 0 0 1-1.5 1.5h-7l-4.2 3v-3H5A1.5 1.5 0 0 1 3.5 15.5V7A1.5 1.5 0 0 1 5 5.5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" /></svg>,
  close: <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>,
  plus: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg>,
  pin: <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M9.5 2.5 13.5 6.5l-1.6.6-2.3 2.3.3 2.6-.8.8L6.4 9.6 3 13l-.5-.5 3.4-3.4L3.2 6.4l.8-.8 2.6.3 2.3-2.3.6-1.1Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /></svg>,
  edit: <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="m10.5 3 2.5 2.5L5.5 13H3v-2.5L10.5 3Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg>,
  trash: <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.5 8.5h6l.5-8.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  send: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 13V3m0 0L3.5 7.5M8 3l4.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>,
};

function loadPins(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(PIN_KEY) ?? "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch { return []; }
}

function Bubble({ m }: { m: Message }) {
  return (
    <div className={`msg ${m.role}`}>
      <div className={`bubble${m.status === "error" ? " err" : ""}`}>
        {m.status === "pending" ? <span className="muted">Réponse en cours…</span> : <p className="pre">{m.content}</p>}
      </div>
      {m.role === "assistant" && m.explanation && <Explanation data={m.explanation} />}
    </div>
  );
}

function Composer({ onSend, disabled }: { onSend: (t: string) => Promise<boolean>; disabled: boolean }) {
  const [v, setV] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    const t = v.trim();
    if (!t || disabled) return;
    if (await onSend(t)) setV("");
  }
  return (
    <form className="af-composer" onSubmit={submit}>
      <input value={v} onChange={(e) => setV(e.target.value)} placeholder="Posez votre question…" aria-label="Votre question" maxLength={MAX_LEN} />
      <button type="submit" className="af-send" disabled={disabled || !v.trim()} aria-label="Envoyer">{Icon.send}</button>
    </form>
  );
}

type RowProps = {
  c: Conversation; active: boolean; pinned: boolean;
  onOpen(): void; onPin(): void; onRename(title: string): void; onDelete(): void;
};

function Row({ c, active, pinned, onOpen, onPin, onRename, onDelete }: RowProps) {
  const [mode, setMode] = useState<"view" | "edit" | "confirm">("view");
  const [draft, setDraft] = useState("");

  function startEdit() { setDraft(c.title ?? ""); setMode("edit"); }
  function commit() {
    const t = draft.trim();
    setMode("view");
    if (t && t !== c.title) onRename(t);
  }
  function key(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") commit();
    if (e.key === "Escape") { e.stopPropagation(); setMode("view"); }
  }

  if (mode === "edit") {
    return (
      <li className="af-row editing">
        <input className="af-rename" autoFocus value={draft} maxLength={120} aria-label="Nouveau titre"
          onChange={(e) => setDraft(e.target.value)} onKeyDown={key} onBlur={commit} />
      </li>
    );
  }
  if (mode === "confirm") {
    return (
      <li className="af-row confirm">
        <span>Supprimer cette conversation ?</span>
        <button type="button" className="af-danger" onClick={onDelete}>Supprimer</button>
        <button type="button" className="af-ghost" onClick={() => setMode("view")}>Annuler</button>
      </li>
    );
  }
  return (
    <li className={`af-row${active ? " sel" : ""}`}>
      <button type="button" className="af-conv" onClick={onOpen}>
        <strong>{c.title || "Sans titre"}</strong>
        <span>{dateTimeFr(c.updatedAt)}</span>
      </button>
      <div className="af-acts">
        <button type="button" className={`af-act${pinned ? " on" : ""}`} aria-pressed={pinned} aria-label={pinned ? "Désépingler" : "Épingler"} title={pinned ? "Désépingler" : "Épingler"} onClick={onPin}>{Icon.pin}</button>
        <button type="button" className="af-act" aria-label="Renommer" title="Renommer" onClick={startEdit}>{Icon.edit}</button>
        <button type="button" className="af-act" aria-label="Supprimer" title="Supprimer" onClick={() => setMode("confirm")}>{Icon.trash}</button>
      </div>
    </li>
  );
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [convs, setConvs] = useState<Conversation[]>([]);
  const [convCursor, setConvCursor] = useState<string | null>(null);
  const [convLoading, setConvLoading] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [msgLoading, setMsgLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [pins, setPins] = useState<string[]>(loadPins);
  const end = useRef<HTMLDivElement>(null);
  const activeRef = useRef<string | null>(null);
  activeRef.current = activeId;

  // Chargement à la première ouverture seulement.
  useEffect(() => {
    if (!open || loaded) return;
    setLoaded(true); setConvLoading(true);
    listConversations()
      .then((p) => { setConvs(p.items); setConvCursor(p.nextCursor ?? null); })
      .catch((e) => setError(errorText(e)))
      .finally(() => setConvLoading(false));
  }, [open, loaded]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: globalThis.KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [open]);

  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages.length, sending, open]);

  const savePins = (next: string[]) => {
    setPins(next);
    try { localStorage.setItem(PIN_KEY, JSON.stringify(next)); } catch { /* stockage indisponible : épingles pour la session */ }
  };
  const togglePin = (id: string) => savePins(pins.includes(id) ? pins.filter((x) => x !== id) : [id, ...pins]);

  const openConv = useCallback(async (id: string | null) => {
    setActiveId(id); activeRef.current = id; setMessages([]); setError("");
    if (!id) return;
    setMsgLoading(true);
    try {
      const all: Message[] = [];
      let cursor: string | undefined;
      for (let i = 0; i < 20; i++) { // ordre chronologique : on lit toutes les pages
        const p = await listMessages(id, cursor);
        all.push(...p.items);
        if (!p.nextCursor) break;
        cursor = p.nextCursor;
      }
      if (activeRef.current === id) setMessages(all);
    } catch (e) {
      if (activeRef.current === id) setError(errorText(e));
      if (e instanceof ApiError && e.code === "CONVERSATION_NOT_FOUND") setConvs((c) => c.filter((x) => x.sessionId !== id));
    } finally {
      if (activeRef.current === id) setMsgLoading(false);
    }
  }, []);

  async function moreConvs() {
    if (!convCursor) return;
    try {
      const p = await listConversations(convCursor);
      setConvs((c) => [...c, ...p.items]);
      setConvCursor(p.nextCursor ?? null);
    } catch (e) { setError(errorText(e)); }
  }

  async function send(text: string): Promise<boolean> {
    setError(""); setSending(true);
    let id = activeId;
    const optimistic: Message = { messageId: tmpId(), sessionId: id ?? "", role: "user", content: text, status: "done", createdAt: new Date().toISOString() };
    try {
      if (!id) {
        const c = await createConversation(text.slice(0, 40));
        id = c.sessionId;
        setConvs((l) => [c, ...l]);
        setActiveId(id); activeRef.current = id;
        setMessages([]);
      }
      setMessages((m) => [...m, optimistic]);
      const r = await sendMessage(id, text);
      if (activeRef.current === id) setMessages((m) => [...m.filter((x) => x.messageId !== optimistic.messageId), r.userMessage, r.assistantMessage]);
      setConvs((l) => {
        const cur = l.find((c) => c.sessionId === id);
        return cur ? [{ ...cur, updatedAt: r.assistantMessage.createdAt }, ...l.filter((c) => c.sessionId !== id)] : l;
      });
      return true;
    } catch (e) {
      if (activeRef.current === id) setMessages((m) => m.filter((x) => x.messageId !== optimistic.messageId));
      setError(errorText(e));
      return false;
    } finally {
      setSending(false);
    }
  }

  async function rename(c: Conversation, title: string) {
    try {
      const u = await renameConversation(c.sessionId, title);
      setConvs((l) => l.map((x) => (x.sessionId === u.sessionId ? u : x)));
    } catch (e) { setError(errorText(e)); }
  }

  async function remove(c: Conversation) {
    try {
      await deleteConversation(c.sessionId);
    } catch (e) {
      if (!(e instanceof ApiError && e.code === "CONVERSATION_NOT_FOUND")) return setError(errorText(e));
    }
    setConvs((l) => l.filter((x) => x.sessionId !== c.sessionId));
    if (pins.includes(c.sessionId)) savePins(pins.filter((x) => x !== c.sessionId));
    if (c.sessionId === activeId) void openConv(null);
  }

  const active = convs.find((c) => c.sessionId === activeId);
  const { pinned, recent } = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const shown = convs.filter((c) => (c.title ?? "").toLowerCase().includes(needle));
    return { pinned: shown.filter((c) => pins.includes(c.sessionId)), recent: shown.filter((c) => !pins.includes(c.sessionId)) };
  }, [convs, pins, q]);

  const row = (c: Conversation) => (
    <Row key={c.sessionId} c={c} active={c.sessionId === activeId} pinned={pins.includes(c.sessionId)}
      onOpen={() => void openConv(c.sessionId)} onPin={() => togglePin(c.sessionId)}
      onRename={(t) => void rename(c, t)} onDelete={() => void remove(c)} />
  );

  return (
    <>
      <section className={`af-overlay${open ? " open" : ""}`} role="dialog" aria-modal="true" aria-label="Assistant AlphaForge" aria-hidden={!open}>
        <div className="af-shell">
          <aside className="af-side">
            <div className="af-brand"><span className="logo-mark" aria-hidden="true" /><span>AlphaForge</span></div>
            <button type="button" className="af-new" onClick={() => void openConv(null)}>{Icon.plus}Nouvelle conversation</button>
            <input className="af-search" placeholder="Rechercher" aria-label="Rechercher une conversation" value={q} onChange={(e) => setQ(e.target.value)} />
            <div className="af-lists">
              {pinned.length > 0 && (<><h3 className="af-label">Épinglées</h3><ul className="af-list">{pinned.map(row)}</ul></>)}
              <h3 className="af-label">Historique</h3>
              <ul className="af-list">
                {recent.map(row)}
                {convLoading && <li className="af-empty">Chargement…</li>}
                {!convLoading && recent.length === 0 && <li className="af-empty">{q ? "Aucun résultat" : "Aucune conversation"}</li>}
              </ul>
              {convCursor && !q && <button type="button" className="af-more" onClick={() => void moreConvs()}>Voir plus</button>}
            </div>
          </aside>

          <main className="af-main">
            <header className="af-head"><strong>{active?.title || "Nouvelle conversation"}</strong></header>
            <div className="af-messages" aria-live="polite">
              <div className="af-thread">
                {msgLoading && <p className="muted small">Chargement…</p>}
                {!msgLoading && messages.length === 0 && (
                  <div className="af-welcome">
                    <h2>Comment puis-je vous aider ?</h2>
                    <p>Posez une question sur votre portefeuille.</p>
                    <div className="suggest">
                      {SUGGESTIONS.map((s) => <button key={s} type="button" className="chip" disabled={sending} onClick={() => void send(s)}>{s}</button>)}
                    </div>
                  </div>
                )}
                {messages.map((m) => <Bubble key={m.messageId} m={m} />)}
                {sending && <div className="msg assistant"><div className="bubble typing"><i /><i /><i /></div></div>}
                <div ref={end} />
              </div>
            </div>
            <div className="af-foot">
              {error && <p className="error" role="alert">{error}</p>}
              <Composer onSend={send} disabled={sending} />
              <p className="af-disclaimer">Simulation seulement : aucune transaction n'est exécutée et les réponses ne constituent pas un conseil financier personnalisé.</p>
            </div>
          </main>
        </div>
      </section>

      <button type="button" className={`af-fab${open ? " open" : ""}`} onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Réduire l'assistant" : "Ouvrir l'assistant"} aria-expanded={open}>
        {open ? Icon.close : Icon.chat}
      </button>
    </>
  );
}
