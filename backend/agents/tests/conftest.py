"""Fixtures de la Lambda agents : DynamoDB simulé (moto), jeu synthétique, faux modèles.

Aucun compte AWS, aucun appel réseau, aucun appel de modèle : Bedrock, la KB et
le Guardrail sont remplacés (faux modèle Strands scripté, clients simulés).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import boto3
import pytest
from moto import mock_aws

from backend.agents.data.store import DataStore, set_default_store
from backend.agents.llm import base
from backend.agents.tests.fake_model import ScriptedModel
from backend.common.repositories import _dynamo
from backend.common.repositories.conversations import UPDATED_AT_INDEX

FIXTURES = Path(__file__).with_name("fixtures") / "dataset"
USER = "user-robert"
CLAIMS = {"sub": USER, "username": "robert"}

TABLES = {
    "USERS_TABLE": "Users-test",
    "CONVERSATIONS_TABLE": "Conversations-test",
    "MESSAGES_TABLE": "Messages-test",
    "PORTFOLIOS_TABLE": "Portfolios-test",
    "ANALYSES_TABLE": "Analyses-test",
}

ROBERT_AMOUNTS = {"XIU.TO": 30000, "RY.TO": 8000, "TD.TO": 9000, "XBB.TO": 30000, "ZST.TO": 15000}


def _create_tables(client) -> None:
    def create(name, keys, lsi=None):
        attributes = {k: "S" for k, _ in keys}
        params: dict[str, Any] = {
            "TableName": name, "BillingMode": "PAY_PER_REQUEST",
            "KeySchema": [{"AttributeName": k, "KeyType": t} for k, t in keys],
        }
        if lsi:
            attributes["updatedAt"] = "S"
            params["LocalSecondaryIndexes"] = lsi
        params["AttributeDefinitions"] = [{"AttributeName": k, "AttributeType": t} for k, t in attributes.items()]
        client.create_table(**params)

    create(TABLES["USERS_TABLE"], [("userId", "HASH")])
    create(TABLES["CONVERSATIONS_TABLE"], [("userId", "HASH"), ("sessionId", "RANGE")], [{
        "IndexName": UPDATED_AT_INDEX,
        "KeySchema": [{"AttributeName": "userId", "KeyType": "HASH"}, {"AttributeName": "updatedAt", "KeyType": "RANGE"}],
        "Projection": {"ProjectionType": "ALL"},
    }])
    create(TABLES["MESSAGES_TABLE"], [("sessionId", "HASH"), ("messageId", "RANGE")])
    create(TABLES["PORTFOLIOS_TABLE"], [("userId", "HASH"), ("portfolioId", "RANGE")])
    create(TABLES["ANALYSES_TABLE"], [("sessionId", "HASH"), ("itemKey", "RANGE")])


@pytest.fixture
def store() -> DataStore:
    data = DataStore(str(FIXTURES), "fixture-synthetic")
    set_default_store(data)
    yield data
    set_default_store(None)


@pytest.fixture
def aws(monkeypatch):
    """DynamoDB simulé et configuration du contrat (noms de variables de backend/common/config.py)."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(key, "testing")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.delenv("RULES_CONFIG_PATH", raising=False)
    for name, value in TABLES.items():
        monkeypatch.setenv(name, value)
    for name in ("MODEL_ORCHESTRATOR", "MODEL_AUDITOR", "MODEL_WRITER"):
        monkeypatch.setenv(name, "test-model")
    monkeypatch.setenv("KB_ID", "KBTEST")
    monkeypatch.delenv("GUARDRAIL_ID", raising=False)
    monkeypatch.delenv("GUARDRAIL_VERSION", raising=False)
    _dynamo.reset_client()
    with mock_aws():
        _create_tables(boto3.client("dynamodb"))
        yield
    _dynamo.reset_client()


class ModelScripts:
    """Scripts de faux modèle par agent ; chaque construction d'Agent consomme un script."""

    def __init__(self) -> None:
        self.scripts: dict[str, list[list[Any]]] = {}
        self.models: dict[str, list[ScriptedModel]] = {}

    def add(self, agent_id: str, *responses: Any) -> None:
        self.scripts.setdefault(agent_id, []).append(list(responses))

    def factory(self, agent_id: str) -> ScriptedModel:
        queue = self.scripts.get(agent_id) or []
        script = queue.pop(0) if queue else []
        # Un script peut être un modèle prêt à l'emploi (ex. EchoTranslator).
        model = script[0] if len(script) == 1 and isinstance(script[0], ScriptedModel) else ScriptedModel(script)
        self.models.setdefault(agent_id, []).append(model)
        return model


@pytest.fixture
def scripts(monkeypatch) -> ModelScripts:
    holder = ModelScripts()
    monkeypatch.setattr(base, "MODEL_FACTORY", holder.factory)
    return holder


def event(route_key: str, *, path: dict[str, str] | None = None, query: dict[str, str] | None = None,
          body: Any = None, claims: dict[str, Any] | None = CLAIMS) -> dict[str, Any]:
    return {
        "version": "2.0", "routeKey": route_key, "rawPath": route_key.split(" ", 1)[1],
        "requestContext": {"requestId": "req-1", "authorizer": {"jwt": {"claims": claims or {}}}},
        "pathParameters": path, "queryStringParameters": query,
        "body": None if body is None else json.dumps(body, ensure_ascii=False), "isBase64Encoded": False,
    }


def body_of(response: dict[str, Any]) -> Any:
    return json.loads(response["body"])


def robert_holdings(store: DataStore) -> list[dict[str, Any]]:
    """Portefeuille vedette (SOLUTION.md section 6), converti en quantités au dernier cours."""
    return [
        {"ticker": t, "quantity": round(a / float(store.prices(t)["close"].iloc[-1]), 6), "avgCost": round(float(store.prices(t)["close"].iloc[0]), 4)}
        for t, a in ROBERT_AMOUNTS.items()
    ]


def robert_mandate(**overrides: Any) -> dict[str, Any]:
    mandate = {
        "portfolioId": "main", "mode": "add_asset", "objective": "project", "objectiveDetail": "condo purchase in 3 years",
        "horizonYears": 3, "riskTolerance": 3, "riskCapacity": 1, "province": "QC", "userLanguage": "fr",
        "operations": [{"action": "add", "ticker": "NVDA", "amount": 15000, "currency": "CAD"}],
        "fieldSources": {"horizonYears": "user_answer", "riskTolerance": "persona", "maxAcceptableLossPct": "team_assumption"},
    }
    mandate.update(overrides)
    return mandate


@pytest.fixture
def robert_session(aws, store):
    """Conversation, portefeuille et mandat v1 confirmé de Robert (comme POST /mandates)."""
    from backend.common.mandates import evaluate_mandate
    from backend.common.repositories import analyses, conversations, portfolios, users

    users.put_user_if_absent(USER, "robert", "Robert")
    conversation = conversations.create_conversation(USER, "Condo")
    portfolios.ensure_main_portfolio(USER)
    portfolios.replace_holdings(USER, "main", robert_holdings(store))
    mandate = robert_mandate()
    analyses.put_mandate(conversation["sessionId"], USER, {
        "mandate": mandate, **evaluate_mandate(mandate), "changedFields": [], "confirmedAt": "2026-11-15T14:02:00Z",
    })
    return conversation["sessionId"]
