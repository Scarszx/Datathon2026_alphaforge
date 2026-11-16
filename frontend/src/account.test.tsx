/* « Explorer sans compte » (questionnaire puis résultat) et suppression du compte simulé (mode démo). */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { demoDeleteUser, demoSignIn, demoSignUp } from "./api/demo";
import { loadPersonalAnswers } from "./lib/personalDraft";
import { QUESTIONS } from "./lib/risk";
import { AppProvider } from "./lib/store";
import Explore from "./pages/Explore";
afterEach(() => { cleanup(); sessionStorage.clear(); localStorage.clear(); });
describe("Explorer sans compte", () => {
  it("mène au questionnaire puis affiche le résultat, gardé dans l'onglet", () => {
    render(<MemoryRouter><AppProvider><Explore /></AppProvider></MemoryRouter>);
    expect(screen.getAllByRole("radio").length).toBeGreaterThan(0);
    // Dernière option de chaque question : tolérance et capacité à 5.
    for (const q of QUESTIONS) {
      const radios = document.querySelectorAll<HTMLInputElement>(`input[name="perso-${q.id}"]`);
      fireEvent.click(radios[radios.length - 1]);
    }
    fireEvent.click(screen.getByRole("button", { name: /Voir mon profil|See my profile/ }));
    expect(screen.getByRole("link", { name: /Créer un compte avec ce profil|Create an account with this profile/ })).toBeTruthy();
    expect(loadPersonalAnswers()).not.toBeNull();
  });
});
describe("suppression du compte simulé", () => {
  it("retire l'utilisateur : il ne peut plus se connecter", () => {
    demoSignUp("marie", "motdepasse1", "marie@example.com", "Marie Test");
    const token = demoSignIn("marie", "motdepasse1");
    demoDeleteUser(token);
    expect(() => demoSignIn("marie", "motdepasse1")).toThrow();
  });
});
