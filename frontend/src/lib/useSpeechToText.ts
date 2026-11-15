/* Hook de saisie vocale : demande l'URL signée à api-speech-session, ouvre le WebSocket vers Transcribe,
 * capte le micro (AudioWorklet), envoie le PCM 16 kHz et remonte le texte reconnu. L'envoi du message
 * reste toujours manuel. */
import { useCallback, useEffect, useRef, useState } from "react";
import { DEMO } from "../api/demo";
import { startSpeechSession } from "../api/endpoints";
import type { Lang } from "./i18n";
import { MAX_SESSION_MS, PcmResampler, encodeAudioEvent, parseTranscriptMessage, speechSupported } from "./speech";

export type SpeechState = "idle" | "connecting" | "listening" | "denied" | "error";

export function useSpeechToText(lang: Lang, onFinal: (text: string) => void, onPartial: (text: string) => void) {
  const [state, setState] = useState<SpeechState>("idle");
  const cleanup = useRef<(() => void) | null>(null);
  const cb = useRef({ onFinal, onPartial });
  cb.current = { onFinal, onPartial };
  const supported = !DEMO && speechSupported();

  const stop = useCallback(() => {
    cleanup.current?.();
    cleanup.current = null;
    cb.current.onPartial("");
    setState((s) => (s === "denied" || s === "error" ? s : "idle"));
  }, []);

  const start = useCallback(async () => {
    if (!supported || cleanup.current) return;
    setState("connecting");
    const undo: (() => void)[] = [];
    let closed = false;
    const close = () => {
      if (closed) return;
      closed = true;
      undo.reverse().forEach((f) => { try { f(); } catch { /* déjà fermé */ } });
    };
    cleanup.current = close;
    const fail = (s: SpeechState) => { close(); cleanup.current = null; cb.current.onPartial(""); setState(s); };
    try {
      const session = await startSpeechSession(lang);
      if (closed) return;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true } });
      undo.push(() => stream.getTracks().forEach((t) => t.stop()));
      if (closed) { close(); return; }
      const ctx = new AudioContext();
      undo.push(() => { void ctx.close(); });
      await ctx.audioWorklet.addModule(`${import.meta.env.BASE_URL}pcm-worklet.js`);
      if (closed) { close(); return; }
      const ws = new WebSocket(session.url);
      ws.binaryType = "arraybuffer";
      undo.push(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send(encodeAudioEvent(new Int16Array(0))); // fin du flux
        ws.close();
      });
      const node = new AudioWorkletNode(ctx, "pcm-worklet");
      const resampler = new PcmResampler(ctx.sampleRate, session.sampleRate);
      node.port.onmessage = (e: MessageEvent<Float32Array>) => {
        if (ws.readyState !== WebSocket.OPEN) return;
        const pcm = resampler.process(e.data);
        if (pcm.length) ws.send(encodeAudioEvent(pcm));
      };
      const src = ctx.createMediaStreamSource(stream);
      src.connect(node);
      undo.push(() => { src.disconnect(); node.disconnect(); node.port.onmessage = null; });
      ws.onopen = () => setState("listening");
      ws.onmessage = (e) => {
        const m = parseTranscriptMessage(new Uint8Array(e.data as ArrayBuffer));
        if (m.kind === "error") { fail("error"); return; }
        if (m.kind !== "transcript") return;
        if (m.isPartial) cb.current.onPartial(m.text); else { cb.current.onPartial(""); cb.current.onFinal(m.text); }
      };
      ws.onerror = () => fail("error");
      ws.onclose = () => { if (!closed) { close(); cleanup.current = null; cb.current.onPartial(""); setState((s) => (s === "error" ? s : "idle")); } };
      const timer = window.setTimeout(stop, MAX_SESSION_MS);
      undo.push(() => window.clearTimeout(timer));
    } catch (e) {
      const name = (e as { name?: string }).name;
      fail(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "error");
    }
  }, [lang, stop, supported]);

  useEffect(() => () => { cleanup.current?.(); cleanup.current = null; }, []);
  return { state, supported, start, stop };
}
