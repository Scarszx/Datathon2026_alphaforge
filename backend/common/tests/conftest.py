"""Fixtures partagées des tests de repositories : DynamoDB simulé par moto.

Aucun compte AWS ni appel réseau : moto intercepte boto3 en mémoire.
"""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from backend.common.repositories import _dynamo
from backend.common.repositories.conversations import UPDATED_AT_INDEX

TABLES = {
    "USERS_TABLE": "Users-test",
    "CONVERSATIONS_TABLE": "Conversations-test",
    "MESSAGES_TABLE": "Messages-test",
    "PORTFOLIOS_TABLE": "Portfolios-test",
}


def _create_tables(client) -> None:
    """Crée les 4 tables comme dans la section databases du contrat."""

    def create(name, keys, extra=None):
        attributes = {k: "S" for k, _ in keys}
        params = {
            "TableName": name,
            "KeySchema": [{"AttributeName": k, "KeyType": t} for k, t in keys],
            "BillingMode": "PAY_PER_REQUEST",
        }
        if extra:
            for index in extra:
                for key in index["KeySchema"]:
                    attributes[key["AttributeName"]] = "S"
            params["LocalSecondaryIndexes"] = extra
        params["AttributeDefinitions"] = [
            {"AttributeName": k, "AttributeType": t} for k, t in attributes.items()
        ]
        client.create_table(**params)

    create(TABLES["USERS_TABLE"], [("userId", "HASH")])
    create(
        TABLES["CONVERSATIONS_TABLE"],
        [("userId", "HASH"), ("sessionId", "RANGE")],
        [
            {
                "IndexName": UPDATED_AT_INDEX,
                "KeySchema": [
                    {"AttributeName": "userId", "KeyType": "HASH"},
                    {"AttributeName": "updatedAt", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    create(TABLES["MESSAGES_TABLE"], [("sessionId", "HASH"), ("messageId", "RANGE")])
    create(TABLES["PORTFOLIOS_TABLE"], [("userId", "HASH"), ("portfolioId", "RANGE")])


@pytest.fixture
def dynamo(monkeypatch):
    """DynamoDB simulé avec les 4 tables, et ressource boto3 neuve par test."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ca-central-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    for name, value in TABLES.items():
        monkeypatch.setenv(name, value)
    _dynamo.reset_client()
    with mock_aws():
        _create_tables(boto3.client("dynamodb"))
        yield
    _dynamo.reset_client()
