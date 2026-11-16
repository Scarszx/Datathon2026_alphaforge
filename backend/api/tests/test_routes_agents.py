"""Tests de la route /agents (registre public tiré du contrat v0.4.0)."""

from __future__ import annotations

from backend.api.app import handle_request

from .conftest import body_of, event


def test_get_agents_renvoie_le_registre_public_v04():
    response = handle_request(event("GET /v1/agents"))
    assert response["statusCode"] == 200
    registry = body_of(response)
    assert set(registry) == {"agents", "modules", "tools"}
    assert [agent["id"] for agent in registry["agents"]] == [
        "agent-orchestrator",
        "agent-auditor",
        "agent-writer",
    ]
    assert [module["id"] for module in registry["modules"]] == [
        "module-engine",
        "module-rules",
        "module-verifier",
    ]
    modules_by_id = {module["id"]: module for module in registry["modules"]}
    assert "COVID 2020" in modules_by_id["module-engine"]["role"]
    tools_by_id = {tool["id"]: tool for tool in registry["tools"]}
    assert "covid_2020" in tools_by_id["tool-stress-test"]["description"]
    assert [tool["id"] for tool in registry["tools"]] == [
        "tool-search-assets",
        "tool-get-prices",
        "tool-get-macro",
        "tool-compute-metrics",
        "tool-get-portfolio",
        "tool-get-profile",
        "tool-propose-mandate",
        "tool-read-evidence",
        "tool-portfolio-impact",
        "tool-stress-test",
        "tool-concentration",
        "tool-check-rules",
        "tool-search-regulation",
    ]


def test_le_registre_respecte_les_droits_et_limites_du_contrat():
    registry = body_of(handle_request(event("GET /v1/agents")))
    by_id = {agent["id"]: agent for agent in registry["agents"]}
    assert by_id["agent-orchestrator"]["allowedTools"] == [
        "tool-get-portfolio",
        "tool-get-profile",
        "tool-search-assets",
        "tool-propose-mandate",
        "tool-read-evidence",
    ]
    assert by_id["agent-orchestrator"]["delegatesTo"] == []
    assert by_id["agent-orchestrator"]["limits"] == {
        "max_agent_cycles": 8,
        "timeout_seconds": 30,
    }
    assert by_id["agent-auditor"]["allowedTools"] == []  # 0.4.3 : le code de l'auditeur lance les recherches
    assert by_id["agent-auditor"]["limits"] == {
        "max_tool_calls": 16,
        "timeout_seconds": 60,
    }
    assert by_id["agent-writer"]["allowedTools"] == ["tool-read-evidence"]
    assert by_id["agent-writer"]["limits"] == {
        "max_tool_calls": 4,
        "timeout_seconds": 60,
    }
    assert all(
        module["id"] and module["name"] and module["role"]
        for module in registry["modules"]
    )
    assert all(tool["description"] and tool["reads"] for tool in registry["tools"])
