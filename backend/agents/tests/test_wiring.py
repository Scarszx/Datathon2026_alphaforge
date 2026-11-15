"""Câblage : toolbox conforme au contrat, descriptions non vides, prompts en anglais, noms d'agents."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from backend.agents import models
from backend.agents.llm.auditor import prompts as auditor_prompts
from backend.agents.llm.orchestrator import prompts as orchestrator_prompts
from backend.agents.llm.writer import prompts as writer_prompts
from backend.agents.toolbox import GRANTS, MAX_TOOL_CALLS, TOOLBOX, Toolbox, ToolboxError
from backend.agents.tools.agent_tools import AGENT_TOOLS, tools_for
from backend.agents.tools.catalog import TOOL_FUNCTIONS

CONTRACT = yaml.safe_load((Path(__file__).resolve().parents[3] / "contract" / "knowledge-graph.yaml").read_text(encoding="utf-8"))
TOOL_NAME_BY_ID = {t["id"]: t["name"] for t in CONTRACT["tools"]}


def test_les_13_outils_du_contrat_sont_enregistres():
    assert set(TOOLBOX.tool_names()) == set(TOOL_NAME_BY_ID.values()) and len(TOOL_FUNCTIONS) == 13


@pytest.mark.parametrize("component", [a for a in CONTRACT["agents"] if a.get("status") == "retenu"] + CONTRACT["modules"], ids=lambda c: c["id"])
def test_droits_conformes_au_contrat(component):
    declared = component.get("allowed_tools", component.get("uses_tools", []))
    assert sorted(GRANTS[component["id"]]) == sorted(TOOL_NAME_BY_ID[t] for t in declared)


def test_limites_et_modeles_conformes_au_contrat():
    for agent in (a for a in CONTRACT["agents"] if a.get("status") == "retenu"):
        spec = models.MODELS[agent["id"]]
        assert spec.max_tokens == agent["max_tokens"]
        assert spec.timeout_seconds == agent["limits"]["timeout_seconds"]
        if "translation_max_tokens" in agent:
            assert models.TRANSLATION_SPEC.max_tokens == agent["translation_max_tokens"]
        if "max_tool_calls" in agent["limits"]:
            assert MAX_TOOL_CALLS[agent["id"]] == agent["limits"]["max_tool_calls"]
        if "max_agent_cycles" in agent["limits"]:
            assert spec.max_turns == agent["limits"]["max_agent_cycles"]


def test_toolbox_echoue_au_demarrage():
    with pytest.raises(ToolboxError):
        Toolbox().register({"a": lambda ctx: {}}).register({"a": lambda ctx: {}})
    with pytest.raises(ToolboxError):
        Toolbox().register({"a": lambda ctx: {}}).grant("agent-x", ["b"])
    with pytest.raises(ToolboxError):
        TOOLBOX.granted("agent-inconnu")
    with pytest.raises(ToolboxError):
        TOOLBOX.call("agent-writer", "search_regulation", None)


def test_outils_strands_par_agent():
    assert [t.tool_name for t in tools_for("agent-orchestrator")] == GRANTS["agent-orchestrator"]
    assert [t.tool_name for t in tools_for("agent-writer")] == ["read_evidence"]


@pytest.mark.parametrize("name", list(AGENT_TOOLS))
def test_description_non_vide_pour_chaque_outil_et_parametre(name):
    spec = AGENT_TOOLS[name].tool_spec
    assert spec["description"].strip()
    for param, schema in spec["inputSchema"]["json"].get("properties", {}).items():
        assert schema.get("description", "").strip(), f"{name}.{param}"
    assert "tool_context" not in spec["inputSchema"]["json"].get("properties", {})


FRENCH = re.compile(r"\b(le|la|les|des|une|est|pour|avec|vous|nous|dans|sur|et|ou|pas|portefeuille|règle|mandat)\b|[éèêàùç]", re.IGNORECASE)
PROMPTS = {
    "orchestrator": orchestrator_prompts.SYSTEM_PROMPT, "translate": orchestrator_prompts.TRANSLATE_PROMPT,
    "auditor": auditor_prompts.SYSTEM_PROMPT, "writer": writer_prompts.SYSTEM_PROMPT,
    **{f"tool:{n}": t.tool_spec["description"] for n, t in AGENT_TOOLS.items()},
}


@pytest.mark.parametrize("name", list(PROMPTS))
def test_prompts_et_descriptions_sans_francais(name):
    # « Quebec » s'écrit sans accent dans les prompts : seul l'affichage est localisé.
    assert not FRENCH.search(PROMPTS[name].replace("profil_risque", "").replace("titres_proteges", "")
                             .replace("aide_decision", "").replace("relation_client", "").replace("questions_investisseur", "")
                             .replace("reglement", "").replace("recommandation", "")), name


def test_phrase_de_langue_exigee_par_le_contrat():
    agent = next(a for a in CONTRACT["agents"] if a["id"] == "agent-orchestrator")
    assert agent["system_prompt_must_include"].strip() in orchestrator_prompts.SYSTEM_PROMPT
