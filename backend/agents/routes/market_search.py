"""Route GET /v1/market/search (api-market-search) : autocomplétion de ticker, sans modèle."""

from __future__ import annotations

from typing import Any

from backend.agents.data.store import DataStore
from backend.agents.tools.catalog import search_assets
from backend.agents.tools.context import RequestContext
from backend.common.http import ApiError, json_response


def market_search(event: dict[str, Any], user_id: str, store: DataStore) -> dict[str, Any]:
    query = event.get("queryStringParameters") or {}
    q = query.get("q")
    if not isinstance(q, str) or not q.strip():
        raise ApiError("VALIDATION_ERROR", "Paramètre requis : q.")
    ctx = RequestContext(user_id=user_id, session_id="-", store=store)
    result = search_assets(ctx, q, query.get("assetClass"))
    if "error" in result:
        raise ApiError("VALIDATION_ERROR", result["error"])
    return json_response(200, {"items": [
        {"ticker": i["ticker"], "name": i["name"], "assetClass": i["assetClass"],
         "market": store.asset(i["ticker"]).get("market"), "currency": i["currency"], "sector": i["sector"]}
        for i in result["items"]
    ]})
