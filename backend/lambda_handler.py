"""AWS Lambda entry point (API Gateway HTTP API, payload v2.0, JWT authorizer on Amazon Cognito)."""
import base64
import json
import logging
import os

from alphaforge.api import HttpError, handle, parse_body

logging.getLogger().setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def handler(event, context):
    rc = event.get("requestContext", {})
    rid = rc.get("requestId") or getattr(context, "aws_request_id", "lambda")
    claims = rc.get("authorizer", {}).get("jwt", {}).get("claims", {})
    # Identity comes ONLY from the verified access token (claim sub), never from the request body.
    user = {"sub": claims.get("sub"), "username": claims.get("username") or claims.get("cognito:username")} if claims.get("sub") else None
    raw = event.get("body")
    if raw and event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        body = parse_body(raw)
        status, payload = handle(rc.get("http", {}).get("method", "GET"), event.get("rawPath", "/"), event.get("queryStringParameters") or {},
                                 body, user, rid)
    except HttpError as e:
        status, payload = e.status, {"error": {"code": e.code, "message": e.message, "requestId": rid}}
    return {"statusCode": status, "headers": {"Content-Type": "application/json", "Cache-Control": "no-store", "X-Request-Id": rid},
            "body": "" if payload is None else json.dumps(payload, ensure_ascii=False, default=str)}
