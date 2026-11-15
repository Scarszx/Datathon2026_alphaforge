// @vitest-environment jsdom
/* Correctifs d'interface : langue unique FR/EN, bulle « ? », classes d'actifs à choix multiple, libellés de risque. */
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import AssetClassPicker from "./components/AssetClassPicker";
import InfoTip from "./components/InfoTip";
import LangSwitch from "./components/LangSwitch";
import { RiskResult } from "./components/RiskForm";
import { EN, FR, LangProvider, useT } from "./lib/i18n";
import { cad, plainPct, setFormatLang } from "./lib/format";
import { levelName, levelText } from "./lib/riskScale";

afterEach(() => { cleanup(); localStorage.clear(); setFormatLang("fr"); });

describe("dictionnaires", () => {
  it("FR et EN ont exactement les mêmes clés", () => {
    expect(Object.keys(EN).filter((k) => !(k in FR))).toEqual([]);
    expect(Object.keys(FR).filter((k) => !(k in EN))).toEqual([]);
  });
});

describe("langue de l'interface", () => {
  const Probe = () => { const { L } = useT(); return <p>{L("Bonjour", "Hello")}</p>; };
  it("le bouton change toute l'interface, et le choix est mémorisé", () => {
    localStorage.setItem("af.lang", "fr");
    render(<LangProvider><LangSwitch /><Probe /></LangProvider>);
    expect(screen.getByText("Bonjour")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    expect(screen.getByText("Hello")).toBeTruthy();
    expect(localStorage.getItem("af.lang")).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });
  it("les montants suivent la langue (1 234,50 $ / $1,234.50)", () => {
    setFormatLang("fr");
    expect(cad(1234.5)).toBe("1\u00a0234,50\u00a0$");
    expect(plainPct(9.07)).toBe("9,1\u00a0%");
    setFormatLang("en");
    expect(cad(1234.5)).toBe("$1,234.50");
    expect(plainPct(9.07)).toBe("9.1%");
  });
});

describe("classes d'actifs exclues", () => {
  function Host({ start = [] as string[] }) {
    const [v, setV] = useState(start);
    return <><AssetClassPicker value={v} onChange={setV} /><output data-testid="v">{v.join(",")}</output></>;
  }
  it("permet de cocher plusieurs classes à la fois", () => {
    localStorage.setItem("af.lang", "fr");
    render(<LangProvider><Host /></LangProvider>);
    fireEvent.click(screen.getByLabelText("Crypto-actifs"));
    fireEvent.click(screen.getByLabelText("FNB d'obligations"));
    fireEvent.click(screen.getByLabelText("Actions"));
    expect(screen.getByTestId("v").textContent).toBe("crypto,etf_bond,equity");
    fireEvent.click(screen.getByLabelText("Crypto-actifs"));
    expect(screen.getByTestId("v").textContent).toBe("etf_bond,equity");
  });
  it("garde une ancienne valeur libre visible et décochable", () => {
    render(<LangProvider><Host start={["obligations d'État"]} /></LangProvider>);
    fireEvent.click(screen.getByLabelText("obligations d'État"));
    expect(screen.getByTestId("v").textContent).toBe("");
  });
});

describe("bulle d'aide « ? »", () => {
  it("s'ouvre au clic et se ferme avec Échap", () => {
    render(<LangProvider><InfoTip text="Explication courte." /></LangProvider>);
    expect(screen.queryByText("Explication courte.")).toBeNull();
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("note").textContent).toBe("Explication courte.");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("note")).toBeNull();
  });
});

describe("niveau de risque en mots", () => {
  it("traduit le niveau 1 à 5 sans afficher de score brut", () => {
    expect(levelName(2, "fr")).toBe("Prudent");
    expect(levelName(1, "en")).toBe("Very cautious");
    expect(levelText(3, "fr")).toMatch(/modérés/);
    localStorage.setItem("af.lang", "fr");
    // maxLoss = 20 % (index 2 → 3), capacité = 4 → niveau retenu 3
    const { container } = render(<LangProvider><RiskResult answers={{ horizon: 3, maxLoss: 2, reaction: 2, goal: 3, capacity: 3 }} /></LangProvider>);
    expect(container.textContent).toContain("Équilibré");
    expect(container.textContent).not.toMatch(/\/ ?25/);
  });
});
