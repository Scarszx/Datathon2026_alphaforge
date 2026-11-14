"""Tests de la route /agents (registre public tiré du contrat)."""

from __future__ import annotations

from backend.api.app import handle_request

from .conftest import body_of, event


def test_get_agents_renvoie_le_registre_public():
    response = handle_request(event("GET /v1/agents"))
    assert response["statusCode"] == 200
    registry = body_of(response)
    assert set(registry) == {"agents", "tools"}
    assert [agent["id"] for agent in registry["agents"]] == [
        "agent-orchestrator",
        "agent-analyst",
        "agent-governance",
    ]
    assert [tool["id"] for tool in registry["tools"]] == [
        "tool-search-assets",
        "tool-get-prices",
        "tool-get-macro",
        "tool-compute-metrics",
        "tool-get-portfolio",
        "tool-get-profile",
    ]


def test_le_registre_respecte_les_limites_du_contrat():
    registry = body_of(handle_request(event("GET /v1/agents")))
    by_id = {agent["id"]: agent for agent in registry["agents"]}
    assert by_id["agent-orchestrator"]["allowedTools"] == []
    assert by_id["agent-orchestrator"]["delegatesTo"] == [
        "agent-analyst",
        "agent-governance",
    ]
    assert by_id["agent-orchestrator"]["limits"] == {
        "max_agent_cycles": 6,
        "timeout_seconds": 25,
    }
    assert by_id["agent-analyst"]["limits"]["max_tool_calls"] == 12
    assert by_id["agent-governance"]["allowedTools"] == [
        "tool-get-profile",
        "tool-get-portfolio",
        "tool-compute-metrics",
    ]
    assert all(tool["description"] and tool["reads"] for tool in registry["tools"])
