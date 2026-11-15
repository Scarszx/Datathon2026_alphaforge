/* Saisie vocale dans le composer (0.4.10) : le texte provisoire s'affiche dans le champ, pas à côté. */
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const hook = vi.hoisted(() => ({
  onFinal: (_: string) => {}, onPartial: (_: string) => {}, state: "listening" as string,
}));
vi.mock("./lib/useSpeechToText", () => ({
  useSpeechToText: (_lang: string, onFinal: (t: string) => void, onPartial: (t: string) => void) => {
    hook.onFinal = onFinal; hook.onPartial = onPartial;
    return { state: hook.state, supported: true, start: vi.fn(), stop: vi.fn(), abort: vi.fn() };
  },
}));
import ConversationColumn from "./components/chat/ConversationColumn";

const renderIt = (onSend = vi.fn()) => render(
  <ConversationColumn messages={[]} evidence={[]} busy={false} lang="fr" refusal={null} onDismissRefusal={vi.fn()} onSend={onSend} onQuickReply={vi.fn()} onConfirmDraft={vi.fn()} />,
);
const input = () => screen.getByRole("textbox") as HTMLInputElement;
Element.prototype.scrollIntoView = vi.fn();
afterEach(() => { cleanup(); hook.state = "listening"; });

describe("composer et dictée", () => {
  it("affiche le texte provisoire dans le champ, à la suite du texte déjà saisi", () => {
    renderIt();
    act(() => hook.onFinal("et si"));
    act(() => hook.onPartial("j'ajoutais"));
    expect(input().value).toBe("et si j'ajoutais");
    expect(input().readOnly).toBe(true);
    expect(input().form?.className).toContain("af-composer-live");
    expect(document.querySelector(".af-mic-note")).toBeNull();
  });
  it("le provisoire se remplace, puis devient définitif sans changer le texte affiché", () => {
    renderIt();
    act(() => hook.onPartial("bon"));
    act(() => hook.onPartial("bonjour"));
    expect(input().value).toBe("bonjour");
    act(() => { hook.onPartial(""); hook.onFinal("bonjour"); });
    expect(input().value).toBe("bonjour");
    expect(input().form?.className).not.toContain("af-composer-live");
  });
  it("le champ redevient modifiable hors dictée", () => {
    hook.state = "idle";
    renderIt();
    expect(input().readOnly).toBe(false);
  });
  it("l'envoi inclut le texte provisoire", () => {
    const onSend = vi.fn();
    renderIt(onSend);
    act(() => hook.onFinal("ajoute"));
    act(() => hook.onPartial("du NVDA"));
    act(() => { (screen.getByText("↑") as HTMLButtonElement).click(); });
    expect(onSend).toHaveBeenCalledWith("ajoute du NVDA");
  });
});
