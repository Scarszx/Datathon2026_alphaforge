/* Tests de la saisie vocale (0.4.8) : encodage/décodage du flux Transcribe, rééchantillonnage, assemblage du texte. */
import { EventStreamCodec } from "@smithy/eventstream-codec";
import { fromUtf8, toUtf8 } from "@smithy/util-utf8";
import { describe, expect, it } from "vitest";
import { EN, FR } from "./lib/i18n";
import { PcmResampler, appendSpeech, encodeAudioEvent, parseTranscriptMessage, speechSupported } from "./lib/speech";

const codec = new EventStreamCodec(toUtf8, fromUtf8);
const incoming = (type: string, payload: unknown, extra: Record<string, string> = {}) =>
  codec.encode({
    headers: {
      ":message-type": { type: "string", value: type },
      ...(type === "event" ? { ":event-type": { type: "string", value: "TranscriptEvent" } } : {}),
      ...Object.fromEntries(Object.entries(extra).map(([k, value]) => [k, { type: "string" as const, value }])),
    },
    body: fromUtf8(JSON.stringify(payload)),
  });
const result = (Transcript: string, IsPartial: boolean) => ({ Transcript: { Results: [{ IsPartial, Alternatives: [{ Transcript }] }] } });

describe("encodeAudioEvent", () => {
  it("encadre le PCM en AudioEvent, 16 bits little-endian", () => {
    const msg = codec.decode(encodeAudioEvent(Int16Array.from([1, -2, 0x1234])));
    expect(msg.headers[":message-type"].value).toBe("event");
    expect(msg.headers[":event-type"].value).toBe("AudioEvent");
    expect(msg.headers[":content-type"].value).toBe("application/octet-stream");
    expect(Array.from(msg.body)).toEqual([1, 0, 0xfe, 0xff, 0x34, 0x12]);
  });
  it("un bloc vide signale la fin du flux", () => {
    expect(codec.decode(encodeAudioEvent(new Int16Array(0))).body.length).toBe(0);
  });
});

describe("parseTranscriptMessage", () => {
  it("distingue partiel et final", () => {
    expect(parseTranscriptMessage(incoming("event", result("et si j'ajoutais", true))))
      .toEqual({ kind: "transcript", text: "et si j'ajoutais", isPartial: true });
    expect(parseTranscriptMessage(incoming("event", result("et si j'ajoutais NVDA", false))))
      .toEqual({ kind: "transcript", text: "et si j'ajoutais NVDA", isPartial: false });
  });
  it("ignore un événement sans résultat", () => {
    expect(parseTranscriptMessage(incoming("event", { Transcript: { Results: [] } }))).toEqual({ kind: "ignored" });
  });
  it("remonte une exception du service", () => {
    const m = parseTranscriptMessage(incoming("exception", { Message: "Your request timed out." }, { ":exception-type": "BadRequestException" }));
    expect(m).toEqual({ kind: "error", message: "Your request timed out." });
  });
});

describe("PcmResampler", () => {
  it("48 kHz → 16 kHz : un tiers des échantillons, valeurs Int16", () => {
    const r = new PcmResampler(48000);
    const out = r.process(new Float32Array(4800).fill(0.5));
    expect(Math.abs(out.length - 1600)).toBeLessThanOrEqual(1);
    expect(out.every((x) => Math.abs(x - 16384) <= 1)).toBe(true);
  });
  it("le découpage en blocs ne change pas le résultat", () => {
    const sig = Float32Array.from({ length: 4410 }, (_, i) => Math.sin(i / 20));
    const whole = new PcmResampler(44100).process(sig);
    const r = new PcmResampler(44100);
    const parts = [r.process(sig.slice(0, 1000)), r.process(sig.slice(1000, 1001)), r.process(sig.slice(1001))];
    const joined = Int16Array.from(parts.flatMap((p) => Array.from(p)));
    expect(joined.length).toBe(whole.length);
    expect(Array.from(joined)).toEqual(Array.from(whole));
  });
  it("écrête hors de [-1, 1]", () => {
    const out = new PcmResampler(16000).process(Float32Array.from([2, -2, 2, -2]));
    expect(Array.from(out).slice(0, 2)).toEqual([32767, -32768]);
  });
});

describe("appendSpeech", () => {
  it("sépare par une espace et tronque à la longueur maximale", () => {
    expect(appendSpeech("", " bonjour ", 2000)).toBe("bonjour");
    expect(appendSpeech("et si", "j'ajoutais NVDA", 2000)).toBe("et si j'ajoutais NVDA");
    expect(appendSpeech("abc ", "def", 2000)).toBe("abc def");
    expect(appendSpeech("abcde", "fghij", 7)).toBe("abcde f");
    expect(appendSpeech("abc", "   ", 2000)).toBe("abc");
  });
});

describe("support navigateur et libellés", () => {
  it("le bouton est masqué sans getUserMedia ni AudioWorklet (jsdom)", () => {
    expect(speechSupported()).toBe(false);
  });
  it("les clés du micro existent en fr et en en", () => {
    for (const k of ["chat.mic.start", "chat.mic.stop", "chat.mic.denied", "chat.mic.error"]) {
      expect(FR[k]).toBeTruthy();
      expect(EN[k]).toBeTruthy();
    }
  });
});
