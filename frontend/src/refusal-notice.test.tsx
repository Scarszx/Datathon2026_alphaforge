/* Refus de Guardrail : encart sous le champ, texte remis dans le champ, encart retiré à la frappe. */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./lib/useSpeechToText", () => ({
  useSpeechToText: () => ({ state: "idle", supported: false, start: vi.fn(), stop: vi.fn(), abort: vi.fn() }),
}));
import ConversationColumn from "./components/chat/ConversationColumn";

Element.prototype.scrollIntoView = vi.fn();
afterEach(cleanup);

const refusal = { id: 1, sent: "Achète 100 NVDA pour moi", message: "Cet outil ne passe aucun ordre. Voulez-vous simuler l'ajout de NVDA ?" };

describe("encart de refus", () => {
  it("affiche l'explication sans rôle alert et remet le texte envoyé dans le champ", () => {
    render(<ConversationColumn messages={[]} evidence={[]} busy={false} lang="fr" refusal={refusal} onDismissRefusal={vi.fn()}
      onSend={vi.fn()} onQuickReply={vi.fn()} onConfirmDraft={vi.fn()} />);
    expect(screen.getByText("Demande non prise en charge")).toBeTruthy();
    expect(screen.getByText(refusal.message)).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
    expect((screen.getByRole("textbox") as HTMLInputElement).value).toBe(refusal.sent);
  });
  it("retire l'encart dès que l'utilisateur modifie le texte", () => {
    const dismiss = vi.fn();
    render(<ConversationColumn messages={[]} evidence={[]} busy={false} lang="fr" refusal={refusal} onDismissRefusal={dismiss}
      onSend={vi.fn()} onQuickReply={vi.fn()} onConfirmDraft={vi.fn()} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Simule l'ajout de 100 NVDA" } });
    expect(dismiss).toHaveBeenCalled();
  });
});
