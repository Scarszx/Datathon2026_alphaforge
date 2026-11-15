// @vitest-environment jsdom
/* Garde des pages privées : sans session, retour à l'accueil (/). */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

let status: "loading" | "anon" | "authed" = "anon";
vi.mock("./lib/store", () => ({ useApp: () => ({ status }) }));
vi.mock("./pages/Landing", () => ({ default: () => <p>PAGE-ACCUEIL</p> }));
vi.mock("./pages/Login", () => ({ default: () => <p>PAGE-LOGIN</p> }));
vi.mock("./pages/Register", () => ({ default: () => <p>PAGE-INSCRIPTION</p> }));
vi.mock("./pages/Chat", () => ({ default: () => <p>PAGE-CHAT</p> }));
vi.mock("./pages/Dashboard", () => ({ default: () => <p>PAGE-DASH</p> }));
vi.mock("./pages/Portfolio", () => ({ default: () => <p>PAGE-PORTEFEUILLE</p> }));
vi.mock("./pages/Markets", () => ({ default: () => <p>PAGE-MARCHES</p> }));
vi.mock("./pages/AssetPage", () => ({ default: () => <p>PAGE-ACTIF</p> }));
vi.mock("./pages/Profile", () => ({ default: () => <p>PAGE-PROFIL</p> }));
import App from "./App";

afterEach(cleanup);
const at = (path: string) => render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);

describe("pages privées", () => {
  it.each(["/accueil", "/chat", "/portefeuille", "/marches", "/marches/RY.TO", "/profil"])("%s sans session renvoie à /", (path) => {
    status = "anon";
    at(path);
    expect(screen.getByText("PAGE-ACCUEIL")).toBeTruthy();
  });
  it("connecté, la page s'affiche", () => {
    status = "authed";
    at("/chat");
    expect(screen.getByText("PAGE-CHAT")).toBeTruthy();
  });
  it("pendant le chargement de la session, pas de redirection", () => {
    status = "loading";
    at("/chat");
    expect(screen.getByText("Chargement…")).toBeTruthy();
  });
  it("/login et /inscription restent publics", () => {
    status = "anon";
    at("/login");
    expect(screen.getByText("PAGE-LOGIN")).toBeTruthy();
    cleanup();
    at("/inscription");
    expect(screen.getByText("PAGE-INSCRIPTION")).toBeTruthy();
  });
});
