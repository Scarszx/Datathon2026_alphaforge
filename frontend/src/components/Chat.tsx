import { useEffect, useRef, useState, type FormEvent } from "react";
import { SUGGESTIONS } from "../agent/agent";
import { useApp } from "../lib/legacyStore";
import type { Message } from "../lib/types";

const DATE = (ts: number) => new Date(ts).toLocaleDateString("fr-CA", { day: "numeric", month: "short" });

/** Rendu minimal : **gras**, _italique_, retours à la ligne. */
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => (
        <p key={i}>
          {line.split(/(\*\*[^*]+\*\*|_[^_]+_)/g).map((s, j) =>
            s.startsWith("**") ? <strong key={j}>{s.slice(2, -2)}</strong> : s.startsWith("_") && s.endsWith("_") && s.length > 2 ? <em key={j} className="disc">{s.slice(1, -1)}</em> : s,
          )}
        </p>
      ))}
    </>
  );
}

function Bubble({ m }: { m: Message }) {
  const [animate] = useState(() => m.role === "assistant" && Date.now() - m.createdAt < 2000);
  const words = m.content.split(/(\s+)/);
  const [n, setN] = useState(animate ? 0 : words.length);
  useEffect(() => {
    if (n >= words.length) return;
    const t = setTimeout(() => setN((x) => x + 3), 25);
    return () => clearTimeout(t);
  }, [n, words.length]);
  return (
    <div className={`msg ${m.role}`}>
      <div className="bubble"><Rich text={n >= words.length ? m.content : words.slice(0, n).join("")} /></div>
      {m.tools && m.tools.length > 0 && n >= words.length && <div className="tools">{m.tools.map((t, i) => <span key={i}>{t}</span>)}</div>}
    </div>
  );
}

export function Messages({ messages, loading, onPick }: { messages: Message[]; loading: boolean; onPick: (q: string) => void }) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages.length, loading]);
  return (
    <div className="messages" aria-live="polite">
      {messages.length === 0 && (
        <div className="suggest">
          <p className="muted">Posez une question sur votre portefeuille :</p>
          {SUGGESTIONS.map((s) => <button key={s} type="button" className="chip" onClick={() => onPick(s)}>{s}</button>)}
        </div>
      )}
      {messages.map((m) => <Bubble key={m.id} m={m} />)}
      {loading && <div className="msg assistant"><div className="bubble typing"><i /><i /><i /></div></div>}
      <div ref={end} />
    </div>
  );
}

export function Composer({ onSend, disabled }: { onSend: (t: string) => void; disabled: boolean }) {
  const [v, setV] = useState("");
  function submit(e: FormEvent) {
    e.preventDefault();
    if (!v.trim() || disabled) return;
    onSend(v.trim());
    setV("");
  }
  return (
    <form className="composer" onSubmit={submit}>
      <input value={v} onChange={(e) => setV(e.target.value)} placeholder="Votre question…" aria-label="Votre question" maxLength={500} />
      <button type="submit" className="btn" disabled={disabled || !v.trim()}>Envoyer</button>
    </form>
  );
}

const X = <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="m4 4 8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>;

type Props = { activeId: string | null; setActiveId: (id: string | null) => void; mode: "closed" | "widget" | "full"; setMode: (m: "closed" | "widget" | "full") => void };

export default function Chat({ activeId, setActiveId, mode, setMode }: Props) {
  const { data, thinking, sendMessage, newConversation, deleteConversation } = useApp();
  const [q, setQ] = useState("");
  const convs = data?.conversations ?? [];
  const active = convs.find((c) => c.id === activeId) ?? null;
  const loading = thinking !== null && thinking === activeId;

  async function send(text: string) {
    const id = await sendMessage(activeId, text);
    if (!activeId) setActiveId(id);
  }
  // pour une nouvelle conversation, l'id est connu seulement après l'envoi : on le crée d'avance
  function sendNew(text: string) {
    if (activeId) return void send(text);
    const id = newConversation();
    setActiveId(id);
    void sendMessage(id, text);
  }

  return (
    <>
      {mode === "closed" && (
        <button type="button" className="fab" aria-label="Ouvrir l'assistant IA" onClick={() => setMode("widget")}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M4 5h16v11H9l-5 4V5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /><circle cx="9" cy="10.5" r="1" fill="currentColor" /><circle cx="12.5" cy="10.5" r="1" fill="currentColor" /><circle cx="16" cy="10.5" r="1" fill="currentColor" /></svg>
        </button>
      )}

      {mode === "widget" && (
        <section className="widget" aria-label="Assistant IA">
          <div className="panel-head">
            <strong>Assistant</strong>
            <div>
              <button type="button" className="icon" title="Agrandir" aria-label="Agrandir" onClick={() => setMode("full")}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M9.5 2.5h4v4M6.5 13.5h-4v-4M13.5 2.5 9 7M2.5 13.5 7 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </button>
              <button type="button" className="icon" aria-label="Réduire" onClick={() => setMode("closed")}>{X}</button>
            </div>
          </div>
          <Messages messages={active?.messages ?? []} loading={loading} onPick={sendNew} />
          <p className="disclaimer">Analyse éducative sur données simulées.</p>
          <Composer onSend={sendNew} disabled={loading} />
        </section>
      )}

      {mode === "full" && (
        <div className="overlay chat-overlay" onMouseDown={(e) => e.target === e.currentTarget && setMode("widget")}>
          <div className="chat-full" role="dialog" aria-label="Conseiller IA">
            <aside className="chat-side">
              <button type="button" className="btn" onClick={() => setActiveId(newConversation())}>+ Nouvelle conversation</button>
              <input className="input" placeholder="Rechercher…" aria-label="Rechercher une conversation" value={q} onChange={(e) => setQ(e.target.value)} />
              <ul className="convs">
                {convs.filter((c) => c.title.toLowerCase().includes(q.toLowerCase())).map((c) => (
                  <li key={c.id} className={c.id === activeId ? "sel" : undefined}>
                    <button type="button" className="conv" onClick={() => setActiveId(c.id)}>
                      <strong>{c.title}</strong><span>{DATE(c.updatedAt)}</span>
                    </button>
                    <button type="button" className="remove" aria-label="Supprimer la conversation" title="Supprimer" onClick={() => { deleteConversation(c.id); if (c.id === activeId) setActiveId(null); }}>{X}</button>
                  </li>
                ))}
                {convs.length === 0 && <li className="muted small" style={{ padding: 8 }}>Aucune conversation</li>}
              </ul>
            </aside>
            <section className="chat-main">
              <div className="panel-head">
                <strong>{active?.title ?? "Conseiller IA"}</strong>
                <div>
                  <button type="button" className="icon" title="Réduire" aria-label="Réduire" onClick={() => setMode("widget")}>
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M13.5 6.5h-4v-4M2.5 9.5h4v4M9.5 6.5 14 2M6.5 9.5 2 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  </button>
                  <button type="button" className="icon" aria-label="Fermer" onClick={() => setMode("closed")}>{X}</button>
                </div>
              </div>
              <Messages messages={active?.messages ?? []} loading={loading} onPick={sendNew} />
              <p className="disclaimer">Analyse éducative fondée sur des données simulées; ne constitue pas un conseil financier. L'assistant ne passe jamais d'ordre.</p>
              <Composer onSend={sendNew} disabled={loading} />
            </section>
          </div>
        </div>
      )}
    </>
  );
}
