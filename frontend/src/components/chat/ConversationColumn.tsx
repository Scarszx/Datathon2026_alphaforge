/* Colonne 2 de /chat : conversation. Messages, boutons quickReplies de l'orchestrateur, carte « mandat
 * proposé » (mandateDraft) avec Confirmer (POST mandates puis POST runs) et Modifier (édition des
 * champs clés avant confirmation). */
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import type { MandateCreateRequest, Message } from "../../api/types";
import { t, type Lang } from "../../lib/i18n";
import { PROVINCES } from "../../lib/risk";
import Explanation from "../Explanation";
import EvidenceText from "./EvidenceText";
import MandateCard from "./MandateCard";

const MAX_LEN = 2000; // schema-message-create-request

const MODES = ["add_asset", "rebalance", "diagnose"] as const;
const OBJECTIVES = ["growth", "income", "preservation", "project", "retirement"] as const;

function DraftEditor({ draft, lang, onConfirm }: { draft: MandateCreateRequest; lang: Lang; onConfirm: (m: MandateCreateRequest) => void }) {
  const [m, setM] = useState<MandateCreateRequest>(draft);
  const set = (patch: Partial<MandateCreateRequest>) => setM({ ...m, ...patch });
  const num = (v: string) => (v === "" ? undefined : Number(v));
  return (
    <div className="stack">
      <div className="row2">
        <div className="field"><label htmlFor="d-mode">{t("mandate.mode", lang)}</label>
          <select id="d-mode" className="input" value={m.mode} onChange={(e) => set({ mode: e.target.value as MandateCreateRequest["mode"] })}>
            {MODES.map((x) => <option key={x} value={x}>{t(`mandate.mode.${x}`, lang)}</option>)}
          </select></div>
        <div className="field"><label htmlFor="d-obj">{t("mandate.objective", lang)}</label>
          <select id="d-obj" className="input" value={m.objective} onChange={(e) => set({ objective: e.target.value as MandateCreateRequest["objective"] })}>
            {OBJECTIVES.map((x) => <option key={x} value={x}>{t(`mandate.objective.${x}`, lang)}</option>)}
          </select></div>
      </div>
      <div className="row2">
        <div className="field"><label htmlFor="d-hor">{t("mandate.horizon", lang)} ({t("mandate.years", lang)})</label>
          <input id="d-hor" className="input" inputMode="numeric" value={m.horizonYears} onChange={(e) => set({ horizonYears: num(e.target.value) ?? 0 })} /></div>
        <div className="field"><label htmlFor="d-sub">{t("mandate.subject", lang)}</label>
          <input id="d-sub" className="input" value={m.subjectTicker ?? ""} onChange={(e) => set({ subjectTicker: e.target.value.toUpperCase() || undefined })} /></div>
      </div>
      <div className="row2">
        <div className="field"><label htmlFor="d-tol">{t("mandate.riskTolerance", lang)} (1-5)</label>
          <input id="d-tol" className="input" inputMode="numeric" value={m.riskTolerance} onChange={(e) => set({ riskTolerance: num(e.target.value) ?? 1 })} /></div>
        <div className="field"><label htmlFor="d-cap">{t("mandate.riskCapacity", lang)} (1-5)</label>
          <input id="d-cap" className="input" inputMode="numeric" value={m.riskCapacity} onChange={(e) => set({ riskCapacity: num(e.target.value) ?? 1 })} /></div>
      </div>
      <div className="row2">
        <div className="field"><label htmlFor="d-loss">{t("col.sliderLoss", lang)}</label>
          <input id="d-loss" className="input" inputMode="numeric" value={m.maxAcceptableLossPct ?? ""} onChange={(e) => set({ maxAcceptableLossPct: num(e.target.value) })} /></div>
        <div className="field"><label htmlFor="d-prov">{t("mandate.province", lang)}</label>
          <select id="d-prov" className="input" value={m.province} onChange={(e) => set({ province: e.target.value as MandateCreateRequest["province"] })}>
            {PROVINCES.map((p) => <option key={p.code} value={p.code}>{p.label} ({p.code})</option>)}
          </select></div>
      </div>
      <div><button type="button" className="btn" onClick={() => onConfirm(m)}>{t("mandate.confirm", lang)}</button></div>
    </div>
  );
}

function Bubble({
  m, lang, evidence, onQuickReply, onConfirmDraft, busy,
}: {
  m: Message; lang: Lang; evidence: import("../../api/types").Evidence[]; busy: boolean;
  onQuickReply: (text: string) => void;
  onConfirmDraft: (m: MandateCreateRequest) => void;
}) {
  const [editing, setEditing] = useState(false);
  const draft = m.mandateDraft;
  return (
    <div className={`msg ${m.role}`}>
      <div className={`bubble${m.status === "error" ? " err" : ""}`}>
        {m.status === "pending" ? <span className="muted">{t("chat.thinking", lang)}</span> : (
          <>
            <p className="pre">{m.runId ? <EvidenceText text={m.content} evidence={evidence} lang={lang} /> : m.content}</p>
            {m.role === "assistant" && m.explanation && <Explanation data={m.explanation} />}
            {m.quickReplies?.length ? (
              <div className="suggest" style={{ marginTop: 10 }}>
                {m.quickReplies.map((qr) => (
                  <button key={qr} type="button" className="chip" disabled={busy} onClick={() => onQuickReply(qr)}>{qr}</button>
                ))}
              </div>
            ) : null}
            {draft && !editing && (
              <div style={{ marginTop: 10 }}>
                <div className="eyebrow">{t("mandate.draftCard", lang)}</div>
                <p className="muted small">{t("mandate.draftHint", lang)}</p>
                <MandateCard mandate={draft} lang={lang} />
                <div className="row2" style={{ marginTop: 8 }}>
                  <button type="button" className="btn" disabled={busy} onClick={() => onConfirmDraft(draft)}>{t("mandate.confirm", lang)}</button>
                  <button type="button" className="btn-ghost" disabled={busy} onClick={() => setEditing(true)}>{t("mandate.edit", lang)}</button>
                </div>
              </div>
            )}
            {draft && editing && (
              <div style={{ marginTop: 10 }}>
                <div className="eyebrow">{t("mandate.edit", lang)}</div>
                <DraftEditor draft={draft} lang={lang} onConfirm={(x) => { setEditing(false); if (x) onConfirmDraft(x); }} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function ConversationColumn({
  messages, evidence, busy, lang, onSend, onQuickReply, onConfirmDraft,
}: {
  messages: Message[];
  evidence: import("../../api/types").Evidence[];
  busy: boolean;
  lang: Lang;
  onSend: (text: string) => void;
  onQuickReply: (text: string) => void;
  onConfirmDraft: (m: MandateCreateRequest) => void;
}) {
  const [v, setV] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages.length, busy]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const text = v.trim();
    if (!text || busy) return;
    setV("");
    onSend(text);
  }
  const key = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void submit(e as unknown as FormEvent); }
  };

  return (
    <main className="chat-col chat-col-mid">
      <div className="chat-col-scroll">
        {messages.length === 0 && !busy && <p className="muted">{t("chat.empty", lang)}</p>}
        {messages.map((m) => (
          <Bubble key={m.messageId} m={m} lang={lang} evidence={evidence} busy={busy} onQuickReply={onQuickReply} onConfirmDraft={onConfirmDraft} />
        ))}
        {busy && <div className="msg assistant"><div className="bubble typing"><i /><i /><i /></div></div>}
        <div ref={end} />
      </div>
      <div className="chat-col-foot">
        <form className="af-composer" onSubmit={submit}>
          <input value={v} onChange={(e) => setV(e.target.value)} onKeyDown={key}
            placeholder={t("chat.placeholder", lang)} aria-label={t("chat.send", lang)} maxLength={MAX_LEN} />
          <button type="submit" className="af-send" disabled={busy || !v.trim()} aria-label={t("chat.send", lang)}>↑</button>
        </form>
        <p className="af-disclaimer">{t("app.disclaimer", lang)}</p>
      </div>
    </main>
  );
}
