// @vitest-environment jsdom
/* Recherche d'industries : bilingue, sans accents, listes facultatives et exclusives, stockage du nom du jeu. */
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import IndustrySearch from "./components/IndustrySearch";
import { EMPTY_INDUSTRIES, industryName, industryPrefs, INDUSTRIES, searchIndustries, splitPreferences, type IndustryChoice } from "./lib/industries";
import { LangProvider } from "./lib/i18n";

afterEach(() => { cleanup(); localStorage.clear(); });

describe("lib/industries", () => {
  it("contient les 101 industries des candidats de l'optimiseur", () => {
    expect(INDUSTRIES).toHaveLength(101);
    expect(new Set(INDUSTRIES.map((i) => i.en)).size).toBe(101);
  });
  it("cherche en français sans accents ni casse, et en anglais", () => {
    expect(searchIndustries("PÉT").map((i) => i.en)).toContain("Oil & Gas E&P");
    expect(searchIndustries("petrole").map((i) => i.en)).toContain("Oil & Gas Midstream");
    expect(searchIndustries("oil and gas").length).toBeGreaterThanOrEqual(5);
    expect(searchIndustries("oil & gas e&p")[0].en).toBe("Oil & Gas E&P");
    expect(searchIndustries("   ")).toEqual([]);
    expect(searchIndustries("zzzz")).toEqual([]);
  });
  it("exclut les industries déjà choisies", () => {
    expect(searchIndustries("tabac", ["Tobacco"])).toEqual([]);
  });
  it("stocke et relit le nom exact du jeu ; un ancien libellé français n'est plus reconnu", () => {
    const prefs = industryPrefs({ liked: ["Biotechnology"], avoided: ["REIT - Retail"] });
    expect(prefs).toEqual(["Industrie : Biotechnology", "Industrie à éviter : REIT - Retail"]);
    expect(splitPreferences(prefs)).toEqual({ liked: ["Biotechnology"], avoided: ["REIT - Retail"], others: [] });
    expect(splitPreferences(["Industrie : Pétrole et gaz", "ESG"]).others).toEqual(["Industrie : Pétrole et gaz", "ESG"]);
  });
  it("affiche le nom français ou anglais selon la langue", () => {
    expect(industryName("Tobacco", "fr")).toBe("Tabac");
    expect(industryName("Tobacco", "en")).toBe("Tobacco");
    expect(industryName("Inconnue", "fr")).toBe("Inconnue");
  });
});

describe("IndustrySearch", () => {
  function Host() {
    const [v, setV] = useState<IndustryChoice>(EMPTY_INDUSTRIES);
    return <><IndustrySearch value={v} onChange={setV} /><output data-testid="v">{JSON.stringify(v)}</output></>;
  }
  const state = () => JSON.parse(screen.getByTestId("v").textContent!) as IndustryChoice;
  const setup = () => { localStorage.setItem("af.lang", "fr"); render(<LangProvider><Host /></LangProvider>); };

  it("démarre vide, sans rien d'obligatoire", () => {
    setup();
    expect(state()).toEqual({ liked: [], avoided: [] });
    expect(screen.queryAllByRole("option")).toHaveLength(0);
  });
  it("ajoute une puce depuis une recherche française, puis la retire", () => {
    setup();
    fireEvent.change(screen.getByLabelText("Industries que j'aime"), { target: { value: "pét" } });
    fireEvent.click(screen.getByText("Pétrole et gaz – exploration et production"));
    expect(state().liked).toEqual(["Oil & Gas E&P"]);
    fireEvent.click(screen.getByLabelText("Retirer Pétrole et gaz – exploration et production"));
    expect(state().liked).toEqual([]);
  });
  it("une industrie ne peut pas être dans les deux listes", () => {
    setup();
    fireEvent.change(screen.getByLabelText("Industries que j'aime"), { target: { value: "tabac" } });
    fireEvent.click(screen.getByText("Tabac"));
    fireEvent.change(screen.getByLabelText("Industries à éviter"), { target: { value: "tobacco" } });
    fireEvent.click(screen.getByRole("option").querySelector("button")!);
    expect(state()).toEqual({ liked: [], avoided: ["Tobacco"] });
  });
  it("choisit avec le clavier", () => {
    setup();
    const input = screen.getByLabelText("Industries à éviter");
    fireEvent.change(input, { target: { value: "banques" } });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(state().avoided).toEqual(["Banks - Regional"]);
  });
});
