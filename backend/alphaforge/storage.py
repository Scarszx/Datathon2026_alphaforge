"""Persistence: Amazon DynamoDB (single table) in AWS, a local JSON file otherwise.

Single-table layout (PK / SK):
  USER#<sub>   PROFILE              user + investor profile
  USER#<sub>   PORTFOLIO#<id>       fictional portfolio
  USER#<sub>   CONV#<sessionId>     conversation header
  CONV#<id>    MSG#<iso>#<msgId>    message (+ explanation)
Documents are stored as a JSON string attribute `doc` (avoids float/Decimal conversion of nested explanations).
Only fictional data is stored: no real client account, no banking data.
"""
from __future__ import annotations

import base64
import json
import os
import threading
from typing import List, Optional, Tuple


class Store:
    def get(self, pk: str, sk: str) -> Optional[dict]: ...
    def put(self, pk: str, sk: str, doc: dict) -> None: ...
    def delete(self, pk: str, sk: str) -> None: ...
    def query(self, pk: str, prefix: str, limit: int = 50, cursor: Optional[str] = None, newest_first: bool = False) -> Tuple[List[dict], Optional[str]]: ...


class LocalStore(Store):
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.db = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.db = json.load(f)

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.db, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    def get(self, pk, sk):
        return self.db.get(pk, {}).get(sk)

    def put(self, pk, sk, doc):
        with self.lock:
            self.db.setdefault(pk, {})[sk] = doc
            self._save()

    def delete(self, pk, sk):
        with self.lock:
            self.db.get(pk, {}).pop(sk, None)
            self._save()

    def query(self, pk, prefix, limit=50, cursor=None, newest_first=False):
        keys = sorted((k for k in self.db.get(pk, {}) if k.startswith(prefix)), reverse=newest_first)
        start = int(cursor) if cursor else 0
        page = keys[start:start + limit]
        nxt = str(start + limit) if start + limit < len(keys) else None
        return [self.db[pk][k] for k in page], nxt


class DynamoStore(Store):
    def __init__(self, table: str):
        import boto3
        self.t = boto3.resource("dynamodb").Table(table)

    def get(self, pk, sk):
        it = self.t.get_item(Key={"PK": pk, "SK": sk}).get("Item")
        return json.loads(it["doc"]) if it else None

    def put(self, pk, sk, doc):
        self.t.put_item(Item={"PK": pk, "SK": sk, "doc": json.dumps(doc, ensure_ascii=False, default=str)})

    def delete(self, pk, sk):
        self.t.delete_item(Key={"PK": pk, "SK": sk})

    def query(self, pk, prefix, limit=50, cursor=None, newest_first=False):
        from boto3.dynamodb.conditions import Key
        kw = {"KeyConditionExpression": Key("PK").eq(pk) & Key("SK").begins_with(prefix), "Limit": limit, "ScanIndexForward": not newest_first}
        if cursor:
            kw["ExclusiveStartKey"] = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        r = self.t.query(**kw)
        lek = r.get("LastEvaluatedKey")
        nxt = base64.urlsafe_b64encode(json.dumps(lek).encode()).decode() if lek else None
        return [json.loads(i["doc"]) for i in r.get("Items", [])], nxt


_store: Optional[Store] = None


def get_db() -> Store:
    global _store
    if _store is None:
        table = os.environ.get("TABLE_NAME")
        _store = DynamoStore(table) if table else LocalStore(os.environ.get("LOCAL_DB", os.path.join(os.path.dirname(__file__), "..", ".localdb.json")))
    return _store
