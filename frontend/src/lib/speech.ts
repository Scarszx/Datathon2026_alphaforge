/* Saisie vocale (contrat 0.4.8, api-speech-session) : fonctions pures du flux Amazon Transcribe Streaming.
 * Le navigateur envoie du PCM 16 bits little-endian, mono, à 16 kHz, encadré en « event stream » ;
 * Transcribe répond par des événements du même format. Rien ici n'est journalisé ni stocké. */
import { EventStreamCodec } from "@smithy/eventstream-codec";
import { fromUtf8, toUtf8 } from "@smithy/util-utf8";

export const TARGET_RATE = 16000;
export const MAX_SESSION_MS = 60_000; // arrêt automatique, pour limiter le coût

const codec = new EventStreamCodec(toUtf8, fromUtf8);

/** Rééchantillonnage linéaire en flux (d'une fréquence quelconque vers 16 kHz) puis Float32 → Int16. */
export class PcmResampler {
  private readonly step: number;
  private pos = 0; // position dans le bloc courant ; -1 = entre le dernier échantillon précédent et le premier
  private prev = 0;
  constructor(inRate: number, outRate = TARGET_RATE) { this.step = inRate / outRate; }

  process(chunk: Float32Array): Int16Array {
    const out: number[] = [];
    const at = (k: number) => (k < 0 ? this.prev : chunk[k]);
    while (Math.floor(this.pos) + 1 < chunk.length) {
      const i = Math.floor(this.pos);
      const f = this.pos - i;
      const x = at(i) * (1 - f) + at(i + 1) * f;
      out.push(Math.round(Math.max(-1, Math.min(1, x)) * (x < 0 ? 0x8000 : 0x7fff)));
      this.pos += this.step;
    }
    if (chunk.length) { this.pos -= chunk.length; this.prev = chunk[chunk.length - 1]; }
    return Int16Array.from(out);
  }
}

/** Enveloppe un bloc PCM (Int16 little-endian) dans un AudioEvent ; un bloc vide signale la fin du flux. */
export function encodeAudioEvent(pcm: Int16Array): Uint8Array {
  const body = new Uint8Array(pcm.length * 2);
  const view = new DataView(body.buffer);
  pcm.forEach((s, i) => view.setInt16(i * 2, s, true));
  return codec.encode({
    headers: {
      ":message-type": { type: "string", value: "event" },
      ":event-type": { type: "string", value: "AudioEvent" },
      ":content-type": { type: "string", value: "application/octet-stream" },
    },
    body,
  });
}

export type TranscriptMessage =
  | { kind: "transcript"; text: string; isPartial: boolean }
  | { kind: "error"; message: string }
  | { kind: "ignored" };

/** Décode un message reçu de Transcribe : texte partiel (aperçu), texte final, ou exception du service. */
export function parseTranscriptMessage(data: Uint8Array): TranscriptMessage {
  const msg = codec.decode(data);
  const type = msg.headers[":message-type"]?.value;
  let payload: unknown = {};
  try { payload = JSON.parse(toUtf8(msg.body)); } catch { /* corps vide ou non JSON */ }
  if (type === "exception") {
    const m = (payload as { Message?: string }).Message;
    return { kind: "error", message: m ?? String(msg.headers[":exception-type"]?.value ?? "exception") };
  }
  const r = (payload as { Transcript?: { Results?: { IsPartial: boolean; Alternatives?: { Transcript?: string }[] }[] } })
    .Transcript?.Results?.[0];
  const text = r?.Alternatives?.[0]?.Transcript;
  if (!r || text === undefined) return { kind: "ignored" };
  return { kind: "transcript", text, isPartial: r.IsPartial };
}

/** Le bouton micro n'apparaît que si le navigateur sait capter et traiter le son. */
export function speechSupported(): boolean {
  return typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia
    && typeof AudioWorkletNode !== "undefined" && typeof WebSocket !== "undefined";
}

/** Ajoute un segment reconnu au texte saisi, tronqué à `max` caractères. */
export function appendSpeech(current: string, segment: string, max: number): string {
  const s = segment.trim();
  if (!s) return current;
  return (current && !/\s$/.test(current) ? `${current} ${s}` : `${current}${s}`).slice(0, max);
}
