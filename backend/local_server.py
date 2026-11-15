#!/usr/bin/env python3
"""Local dev server: same router as Lambda, local JSON store, local dataset.

Auth in local mode: the front sends `Authorization: Bearer local:<username>` (no password).
Log in as amira, mateo or robert to get the persona profile and a demo portfolio.
NEVER expose this server publicly: it trusts the username in the header.

  python3 backend/local_server.py            # http://localhost:8787, Bedrock on if AWS credentials work
  LLM_MODE=off python3 backend/local_server.py   # fully deterministic, no AWS needed
"""
import json
import logging
import os
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alphaforge.api import HttpError, handle, parse_body  # noqa: E402
from alphaforge.data import get_store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:5173")


class H(BaseHTTPRequestHandler):
    def _send(self, status, payload, rid):
        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Expose-Headers", "X-Request-Id")
        self.send_header("X-Request-Id", rid)
        if payload is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, None, "preflight")

    def _any(self):
        rid = uuid.uuid4().hex[:12]
        u = urlparse(self.path)
        auth = self.headers.get("Authorization", "")
        user = None
        if auth.startswith("Bearer local:"):
            name = auth[len("Bearer local:"):].strip().lower()[:40]
            if name.replace("-", "").replace("_", "").isalnum():
                user = {"sub": f"local-{name}", "username": name}
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8") if n else None
        try:
            status, payload = handle(self.command, u.path, dict(parse_qsl(u.query)), parse_body(raw), user, rid)
        except HttpError as e:
            status, payload = e.status, {"error": {"code": e.code, "message": e.message, "requestId": rid}}
        self._send(status, payload, rid)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _any


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8787"))
    s = get_store()
    print(f"AlphaForge local API on http://localhost:{port}  data={s.origin} asOf={s.as_of}  LLM_MODE={os.environ.get('LLM_MODE', 'bedrock')}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
