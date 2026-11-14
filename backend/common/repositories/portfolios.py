"""Accès à la table Portfolios (contrat : db-portfolios).

Clé : partition userId, tri portfolioId ('main' par défaut). holdings est une
liste de { ticker, quantity, avgCost } ; aucun prix ni nom n'est stocké.
"""

from __future__ import annotations

from typing import Any

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from backend.common import config
from backend.common.http import ApiError
from backend.common.repositories import _dynamo

MAIN_PORTFOLIO_ID = "main"
MAIN_PORTFOLIO_NAME = "Principal"


def _to_portfolio(item: dict[str, Any]) -> dict[str, Any]:
    """Item DynamoDB -> schema-portfolio (userId n'est pas exposé)."""
    item = _dynamo.from_dynamo(item)
    return {
        "portfolioId": item["portfolioId"],
        "name": item["name"],
        "baseCurrency": item["baseCurrency"],
        "holdings": [
            {"ticker": h["ticker"], "quantity": h["quantity"], "avgCost": h["avgCost"]}
            for h in item.get("holdings", [])
        ],
        "updatedAt": item["updatedAt"],
    }


def list_portfolios(user_id: str) -> list[dict[str, Any]]:
    """Retourne tous les portefeuilles de l'utilisateur (schema-portfolio-list)."""
    table = _dynamo.table(config.portfolios_table())
    params: dict[str, Any] = {"KeyConditionExpression": Key("userId").eq(user_id)}
    items: list[dict[str, Any]] = []
    while True:
        response = table.query(**params)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return [_to_portfolio(item) for item in items]
        params["ExclusiveStartKey"] = last_key


def get_portfolio(user_id: str, portfolio_id: str) -> dict[str, Any] | None:
    """Retourne le portefeuille s'il appartient à user_id, sinon None.

    Un portefeuille d'un autre utilisateur est invisible (comme inexistant).
    """
    item = (
        _dynamo.table(config.portfolios_table())
        .get_item(Key={"userId": user_id, "portfolioId": portfolio_id})
        .get("Item")
    )
    return _to_portfolio(item) if item else None


def ensure_main_portfolio(user_id: str, base_currency: str = "CAD") -> dict[str, Any]:
    """Crée le portefeuille 'main' vide s'il n'existe pas (contrat :
    api-portfolios-list le crée au premier GET) et le retourne.

    Écriture conditionnelle, donc idempotent : un 'main' existant n'est jamais
    écrasé (ni ses positions, ni sa devise).
    """
    item = {
        "userId": user_id,
        "portfolioId": MAIN_PORTFOLIO_ID,
        "name": MAIN_PORTFOLIO_NAME,
        "baseCurrency": base_currency,
        "holdings": [],
        "updatedAt": _dynamo.now_iso(),
    }
    try:
        _dynamo.table(config.portfolios_table()).put_item(
            Item=item, ConditionExpression="attribute_not_exists(portfolioId)"
        )
    except ClientError as exc:
        if not _dynamo.is_conditional_failure(exc):
            raise
        existing = get_portfolio(user_id, MAIN_PORTFOLIO_ID)
        if existing is not None:
            return existing
        raise
    return _to_portfolio(item)


def replace_holdings(
    user_id: str, portfolio_id: str, holdings: list[dict[str, Any]]
) -> dict[str, Any]:
    """Remplace toute la liste des positions (contrat : api-portfolio-holdings-put,
    le front envoie l'état complet de sa table), met à jour updatedAt et retourne
    le portefeuille.

    Lève ApiError('PORTFOLIO_NOT_FOUND') si absent ou non possédé.
    holdings : liste de { ticker, quantity, avgCost }, validée par la Lambda API.
    """
    stored = [
        {"ticker": h["ticker"], "quantity": h["quantity"], "avgCost": h["avgCost"]}
        for h in holdings
    ]
    try:
        response = _dynamo.table(config.portfolios_table()).update_item(
            Key={"userId": user_id, "portfolioId": portfolio_id},
            UpdateExpression="SET holdings = :h, updatedAt = :now",
            ConditionExpression="attribute_exists(portfolioId)",
            ExpressionAttributeValues={
                ":h": _dynamo.to_dynamo(stored),
                ":now": _dynamo.now_iso(),
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if _dynamo.is_conditional_failure(exc):
            raise ApiError("PORTFOLIO_NOT_FOUND", "Portefeuille inconnu.") from exc
        raise
    return _to_portfolio(response["Attributes"])
