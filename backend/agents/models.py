"""Un modèle par agent (contrat : agents.model, max_tokens, limits), lu dans la config.

Le même identifiant d'agent sert de clé ici, pour la toolbox, pour name= de
l'Agent Strands et pour agentId des journaux. max_tokens est TOUJOURS fixé :
sans lui, Bedrock réserve le maximum du modèle contre le quota du compte.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from backend.common import config

REGION = "us-east-1"  # contrat : conventions.region


@dataclass(frozen=True)
class AgentSpec:
    model_id: Callable[[], str | None]
    max_tokens: int
    timeout_seconds: int
    max_turns: int


MODELS: dict[str, AgentSpec] = {
    "agent-orchestrator": AgentSpec(config.model_orchestrator, 1024, 25, 6),
    "agent-auditor": AgentSpec(config.model_auditor, 1024, 20, 10),
    "agent-writer": AgentSpec(config.model_writer, 2048, 25, 5),
}

_CACHE: dict[str, object] = {}


def model_id(agent_id: str) -> str:
    value = MODELS[agent_id].model_id()
    if not value:
        raise RuntimeError(f"No Bedrock model configured for {agent_id}")
    return value


def create_model(agent_id: str):
    """BedrockModel de l'agent, réutilisé entre invocations chaudes (l'Agent, lui, est recréé)."""
    if agent_id not in _CACHE:
        from botocore.config import Config
        from strands.models.bedrock import BedrockModel

        spec = MODELS[agent_id]
        _CACHE[agent_id] = BedrockModel(
            model_id=model_id(agent_id),
            max_tokens=spec.max_tokens,
            region_name=REGION,  # explicite : sinon Strands retombe sur us-west-2
            boto_client_config=Config(read_timeout=spec.timeout_seconds + 5, retries={"max_attempts": 2, "mode": "standard"}),
        )
    return _CACHE[agent_id]
