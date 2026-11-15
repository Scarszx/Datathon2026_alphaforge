"""Lot E1 : construction du corpus par section (backend/agents/scripts/build_kb_corpus.py)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from backend.agents.scripts import build_kb_corpus as build
from backend.agents.tools import kb

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs" / "for_KB"


def _lines(text: str, page: int = 1) -> list[build.Line]:
    return [build.Line(t.strip(), page) for t in text.splitlines()]


# --- unitaires -------------------------------------------------------------------------------------------------


def test_en_tetes_et_pieds_de_page_repetes_sont_retires():
    def filler(n: int) -> str:
        return "\n".join(f"unique filler line {i} of page {n}" for i in range(6))

    pages = [f"Running header\n{filler(n)}\nBody {chr(96 + n) * 5}\n{n}\n" for n in range(1, 8)]
    removed = build.Removed()
    lines = build.clean_lines(pages, {}, removed)
    texts = [line.text for line in lines if line.text]
    assert "Running header" not in texts and not any(t.isdigit() for t in texts)  # en-tête répété et numéro de page disparus
    assert all(f"Body {chr(96 + n) * 5}" in texts for n in range(1, 8))
    # Le numéro de page seul revient sur chaque page : il est retiré comme pied de page ou comme numéro isolé.
    assert removed.counts["en-tête ou pied de page"] + removed.counts["numéro de page isolé"] >= 14


def test_lignes_de_page_web_et_table_des_matieres_retirees():
    cfg = {"drop_line_regex": ["^Source: https?://", "^HOME$"], "preamble_until": "^Executive Summary$"}
    page = "Source: https://www.ciro.ca/x\nHOME\nTitle\nExecutive Summary\nText.\n1. Intro ........ 4\n"
    lines = build.clean_lines([page], cfg, build.Removed())
    assert [line.text for line in lines if line.text] == ["Executive Summary", "Text."]


def test_decoupage_par_section_numerotee_et_doublons_de_table_des_matieres():
    cfg = {"levels": [r"^(?P<num>\d+(?:\.\d+){0,3})\.?\s+(?P<title>[A-Z][A-Za-z\- ]{2,60})$"], "preamble_title": "Executive Summary"}
    # Table des matières : les titres reviennent avec une ligne de texte courte, puis le corps réel.
    text = ("Summary text.\n1. Introduction\np. 1\n2. Framework\np. 2\n2.1 Prohibition\np. 2\n"
            "1. Introduction\nIntro body with real text.\n2. Framework\nFramework body with real text.\n2.1 Prohibition\nThe rule says more.")
    removed = build.Removed()
    sections = build.prune(build.split_numbered(_lines(text), cfg, removed), cfg, removed)
    by_id = {s.section: s for s in sections}
    assert list(by_id) == [None, "1", "2", "2.1"] and by_id[None].title == "Executive Summary"
    assert by_id["1"].body() == "Intro body with real text." and by_id["2.1"].body() == "The rule says more."
    assert removed.counts["doublon de titre (table des matières)"] == 3


def test_parties_en_lettres_et_numeros_composes():
    cfg = {"levels": [r"^(?P<num>[A-D])\.\s+(?P<title>[A-Z][^\n]+)$", r"^(?P<num>\d)\.\s+(?P<title>[A-Z][^\n]+)$"]}
    text = "C. Suitability\nPart text.\n1. Factors\nOne.\n4. Alternatives\nFour.\nD. Compliance\nPart D text.\n1. Policies\nPolicy."
    sections = build.split_numbered(_lines(text), cfg, build.Removed())
    assert [s.section for s in sections] == ["C", "C.1", "C.4", "D", "D.1"]


def test_aucun_numero_invente_sans_numerotation():
    lines = [build.Line(f"text {i}", page) for i, page in enumerate([1, 2, 3, 4, 5, 6, 7])]
    sections = build.split_pages(lines, "Doc")
    assert all(s.section is None for s in sections) and [s.pages() for s in sections] == ["1-3", "4-6", "7"]
    assert build.file_stem("CA_X", sections[1]) == "CA_X__o02"


def test_titre_court_coupe_les_references_reglementaires():
    assert build.short_title("Impact on client's account (Subparagraph 13.3(1)(a)(iii) of NI 31-103,") == "Impact on client's account"
    assert build.short_title("Keeping KYC information current (Subsections 13.2(4) and 13.2(4.1)") == "Keeping KYC information current"
    assert len(build.short_title("word " * 60)) <= build.TITLE_MAX


def test_sujets_par_section_prefixe_le_plus_long_et_heritage():
    proposal = {"documents": {"D": {"default": "inherit", "sections": {"2.1.1": ["aide_decision"], "2.1": ["recommandation"], "3": ["oeo"]}}}}
    assert build.subjects_for("D", "2.1.1", ["oeo"], proposal) == (["aide_decision"], False)
    assert build.subjects_for("D", "2.1.2", ["oeo"], proposal) == (["recommandation"], False)
    assert build.subjects_for("D", "3.1.1", ["oeo"], proposal) == (["oeo"], False)
    assert build.subjects_for("D", "5", ["oeo", "x"], proposal) == (["oeo", "x"], True)  # hérité : listé dans le rapport
    assert build.subjects_for("D", None, ["oeo"], proposal) == (["oeo"], True)


def test_metadonnees_courtes_sujets_connus_et_citable():
    base = {"juridiction": "CA", "regulateur": "FCAA", "sujets": ["titres_proteges"], "langue": "en", "date_version": "2022", "source_url": "u"}
    section = build.Section("3", "Title", order=4)
    meta = build.build_metadata(base, "D", "2026-11-15", section, ["titres_proteges"], True, "4-5")["metadataAttributes"]
    assert meta["citable"] is True and meta["statut"] == "projet" and meta["section"] == "3" and meta["pages"] == "4-5"
    assert meta["corpus_version"] == "2026-11-15" and meta["doc_id"] == "D"
    with pytest.raises(ValueError, match="hors KNOWN_SUBJECTS"):
        build.build_metadata(base, "D", "v", section, ["inconnu"], True)
    with pytest.raises(ValueError, match="octets"):
        build.build_metadata({**base, "source_url": "x" * 2000}, "D", "v", section, ["crypto"], True)


def test_apostrophes_normalisees_pour_les_controles():
    assert build.normalize("a client’s   risk\nprofile") == "a client's risk profile"


# --- intégration sur le corpus actuel ----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext (poppler-utils) requis")
    out = tmp_path_factory.mktemp("kb") / "2026-11-15"
    assert build.main(["--source", str(SOURCE), "--out", str(out), "--version", "2026-11-15"]) == 0  # tous les contrôles passent
    return out


def _metadata(corpus: Path) -> dict[str, dict]:
    return {p.name[: -len(".metadata.json")]: json.loads(p.read_text())["metadataAttributes"] for p in corpus.glob("*.metadata.json")}


def test_phrases_de_controle_presentes_et_residus_absents(corpus):
    text = build.normalize(" ".join(p.read_text() for p in corpus.glob("*_en.txt") if "__notes" not in p.name))
    for phrase in (
        "a client's overall risk profile should reflect the lower of the two",
        "The risk profile for a client should reflect the lower of",
        "takes no position on whether that output is suitable for that client",
        "applies both to each individual support and to their collective output",
        "has not yet been proclaimed into force",
    ):
        assert phrase in text, phrase
    for residue in ("Source: https://www.ciro.ca", "/ NEWSROOM / PUBLICATIONS /", "This Guidance Note replaces", "Table of contents", "toler ance"):
        assert residue not in text, residue


def test_section_2_1_1_est_un_fichier_a_part_avec_ses_metadonnees(corpus):
    name = "CA_CIRO_GN-3200-26-001__s2.1.1_en.txt"
    body = (corpus / name).read_text()
    assert "output is generic to investors who input similar information" in body and "Source:" not in body
    meta = _metadata(corpus)[name]
    assert meta["section"] == "2.1.1" and meta["section_titre"] == "Decision-making supports" and meta["citable"] is True
    assert set(meta["sujets"]) == {"aide_decision", "recommandation", "oeo"} and "pages" not in meta
    assert any(f"GN-3200-26-001__s{s}_en.txt" in name2 for s in ("3.2", "3.3") for name2 in _metadata(corpus))


def test_citable_statut_et_sections_cles(corpus):
    metadata = _metadata(corpus)
    nbdb = [m for n, m in metadata.items() if n.startswith("QC_NBDB")]
    assert nbdb and all(m["citable"] is False for m in nbdb)
    fcaa = [m for n, m in metadata.items() if n.startswith("SK_FCAA")]
    assert fcaa and all(m["statut"] == "projet" and m["citable"] is True for m in fcaa)
    assert all(m["citable"] is True for n, m in metadata.items() if n.startswith(("CA_31-103", "CA_31-368", "CA_CIRO")) and "__notes" not in n)
    for name in ("CA_31-103CP__s13.2_en.txt", "CA_31-103CP__s13.3_en.txt", "CA_31-103__s13.2_en.txt", "CA_31-103__s13.3_en.txt",
                 "CA_31-368__sA.1_en.txt", "CA_31-368__sC.4_en.txt"):
        assert name in metadata, name
    assert "reflect the lower of" in (corpus / "CA_31-103CP__s13.2_en.txt").read_text()


def test_metadonnees_courtes_sujets_connus_et_noms_compatibles_avec_la_kb(corpus):
    for name, meta in _metadata(corpus).items():
        assert len(json.dumps({"metadataAttributes": meta}).encode()) <= build.MAX_METADATA_BYTES, name
        allowed = set(kb.KNOWN_SUBJECTS) | ({build.NOTES_SUBJECT} if name.endswith("__notes_en.txt") else set())
        assert set(meta["sujets"]) <= allowed, name
        assert meta["langue"] == "en" and meta["corpus_version"] == "2026-11-15" and meta["doc_id"]
        assert not kb.document_title(name).endswith("_en.txt"), name  # le préfixe du document est reconnu


def test_manifeste_et_rapport(corpus):
    manifest = json.loads((corpus / "manifest.json").read_text())
    assert manifest["corpus_version"] == "2026-11-15" and manifest["documents"] == 13
    assert {"doc_id", "section", "langue", "file", "titre", "taille"} <= set(manifest["sections"][0])
    assert all((corpus / s["file"]).exists() for s in manifest["sections"])
    report = (corpus / "report.md").read_text()
    for part in ("Blocs retirés", "Sections aux sujets hérités", "Contrôles de phrases", "Alignement anglais-français", "non exécutées"):
        assert part in report
    assert "ÉCHEC" not in report


def test_refuse_un_dossier_de_sortie_non_vide(tmp_path):
    (tmp_path / "x").write_text("déjà là")
    assert build.main(["--source", str(SOURCE), "--out", str(tmp_path), "--version", "v"]) == 2


def test_citations_fixees_embarquees_sont_celles_du_corpus_construit(corpus):
    """Le fichier du zip (backend/agents/data/fixed_citations.json) doit rester celui du script, sinon R5/R9 citeraient un texte périmé."""
    built = json.loads((corpus / "fixed_citations.json").read_text())
    embedded = json.loads((ROOT / "backend" / "agents" / "data" / "fixed_citations.json").read_text())
    assert built == embedded
    assert [c["section"] for c in built["R5"]] == ["s. 2.1.1 Decision-making supports", "s. 3.3 Safeguards for Decision-Making Supports"]
    assert set(built["R9"]) == {"QC", "ON", "SK"} and built["R9"]["SK"][0]["status"] == "projet"
    assert all(len(c["excerpt"]) <= kb.MAX_EXCERPT_CHARS for c in built["R5"] + sum(built["R9"].values(), []))


def test_notes_de_bas_de_page_dans_un_fichier_non_citable_sans_sujet_de_recherche(corpus):
    """Les notes d'une page web (numéro seul, puis texte) vont dans un fichier `notes` : non citable, sujet « notes »."""
    metadata = _metadata(corpus)
    notes = [n for n in metadata if n.endswith("__notes_en.txt")]
    assert "CA_CIRO_GN-3200-26-001__notes_en.txt" in notes
    for name in notes:
        assert metadata[name]["citable"] is False and metadata[name]["sujets"] == ["notes"]
    body = (corpus / "CA_CIRO_GN-3200-26-001__notes_en.txt").read_text()
    assert "In this guidance, all rule references are to the Investment Dealer and Partially Consolidated Rules" in body
    sections = " ".join(p.read_text() for p in corpus.glob("CA_CIRO_GN-3200-26-001__s*_en.txt"))
    assert "all rule references are to the Investment Dealer" not in sections  # plus dans les sections citables


def test_un_chiffre_seul_d_une_page_web_n_est_pas_un_numero_de_page():
    lines = build.clean_lines(["Text.\n1\nA footnote that is clearly longer than thirty characters."], {}, build.Removed(), is_pdf=False)
    assert [ln.text for ln in lines if ln.text] == ["Text.", "1", "A footnote that is clearly longer than thirty characters."]
    lines = build.clean_lines(["Text.\n12\nMore."], {}, build.Removed(), is_pdf=True)
    assert "12" not in [ln.text for ln in lines]
