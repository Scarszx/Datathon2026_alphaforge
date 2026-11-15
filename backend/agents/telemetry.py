"""Traces OpenTelemetry vers Langfuse (sans SDK Langfuse, fail-open).

Conventions appliquées (contrat section 8 observability, retour d'expérience Strands,
et bonnes pratiques Langfuse v4 `.agents/skills/langfuse/references/instrumentation.md`) :
- Strands émet déjà les spans d'invocation d'agent (`invoke_agent`), de modèle (`chat`,
  avec modèle et tokens) et d'outils (`execute_tool`).
- Ce module configure l'exportateur OTLP/HTTP (`StrandsTelemetry.setup_otlp_exporter`)
  vers `${LANGFUSE_BASE_URL}/api/public/otel/v1/traces` avec l'en-tête Basic Auth
  `base64(publicKey:secretKey)` et `x-langfuse-ingestion-version: 4`.
- La clé publique (`LANGFUSE_PUBLIC_KEY`) et l'URL (`LANGFUSE_BASE_URL`) sont publiques ;
  la clé secrète (`LANGFUSE_SECRET_KEY`) est lue depuis l'environnement / `.env` en local,
  ou depuis AWS SSM Parameter Store (`LANGFUSE_SECRET_PARAM`, `WithDecryption=True`) dans
  Lambda, une seule fois par conteneur.
- Fail-open : aucune erreur d'initialisation, de SSM ou d'export ne remonte à l'appelant.
- Spans typés (`langfuse.observation.type` : `chain`, `agent`, `guardrail`, `retriever`,
  `evaluator`) avec `langfuse.session.id`, `langfuse.user.id`, `langfuse.trace.name`,
  `langfuse.trace.tags`, `langfuse.observation.input` et `langfuse.observation.output`.
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

from opentelemetry import context as otel_context
from opentelemetry import propagate, trace
from strands.telemetry import StrandsTelemetry

from backend.agents.observability import log_event
from backend.common import config

_INITIALIZED = False
_TELEMETRY: StrandsTelemetry | None = None
_SSM_CLIENT = None


def _load_dotenv_if_local() -> None:
    """Charge `.env` à la racine du dépôt en exécution locale (hors pytest)."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


def _is_placeholder(secret: str | None) -> bool:
    if not secret:
        return True
    s = secret.strip()
    return not s or s.endswith("*") or "REPLACE" in s.upper()


def _fetch_secret_from_ssm(param_name: str, ssm_client=None) -> tuple[str | None, str | None]:
    """Lit la clé secrète (ou JSON {publicKey, secretKey}) depuis SSM Parameter Store."""
    global _SSM_CLIENT
    client = ssm_client
    if client is None:
        if _SSM_CLIENT is None:
            import boto3

            _SSM_CLIENT = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        client = _SSM_CLIENT
    response = client.get_parameter(Name=param_name, WithDecryption=True)
    raw = (response.get("Parameter") or {}).get("Value", "").strip()
    if not raw:
        return None, None
    if raw.startswith("{"):
        data = json.loads(raw)
        return data.get("publicKey"), data.get("secretKey")
    return None, raw


def resolve_credentials(*, ssm_client=None) -> tuple[str | None, str | None, str]:
    """Résout (public_key, secret_key, base_url) depuis l'environnement, `.env` ou SSM."""
    _load_dotenv_if_local()
    public_key = (config.langfuse_public_key() or "").strip() or None
    secret_key = (config.langfuse_secret_key() or "").strip() or None
    base_url = config.langfuse_base_url().strip().rstrip("/")

    if _is_placeholder(secret_key):
        secret_key = None
        param_name = (config.langfuse_secret_param() or "").strip()
        if param_name:
            try:
                ssm_pub, ssm_sec = _fetch_secret_from_ssm(param_name, ssm_client=ssm_client)
                if ssm_pub and not public_key:
                    public_key = ssm_pub
                if not _is_placeholder(ssm_sec):
                    secret_key = ssm_sec
            except Exception as exc:
                log_event("telemetry.ssm_error", param=param_name, error=type(exc).__name__)
    return public_key, secret_key, base_url


def start_telemetry(*, ssm_client=None) -> StrandsTelemetry | None:
    """Initialise une seule fois par conteneur l'export OTLP vers Langfuse (fail-open)."""
    global _INITIALIZED, _TELEMETRY
    if _INITIALIZED:
        return _TELEMETRY
    _INITIALIZED = True

    public_key, secret_key, base_url = resolve_credentials(ssm_client=ssm_client)
    if not public_key or not secret_key:
        return None

    try:
        os.environ.setdefault("OTEL_SERVICE_NAME", "alphaforge-agents")
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN",
            "gen_ai_latest_experimental,gen_ai_tool_definitions",
        )
        token = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("ascii")
        _TELEMETRY = StrandsTelemetry().setup_otlp_exporter(
            endpoint=f"{base_url}/api/public/otel/v1/traces",
            headers={
                "Authorization": f"Basic {token}",
                "x-langfuse-ingestion-version": "4",
            },
            timeout=2,
        )
        log_event("telemetry.started", baseUrl=base_url)
    except Exception as exc:
        log_event("telemetry.init_error", error=type(exc).__name__)
        _TELEMETRY = None
    return _TELEMETRY


def _serialize_io(data: Any) -> str:
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return str(data)


def set_span_output(span: trace.Span | None, output_data: Any) -> None:
    """Enregistre la sortie structurée sur l'observation courante."""
    if span is None or output_data is None or not span.is_recording():
        return
    try:
        span.set_attribute("langfuse.observation.output", _serialize_io(output_data))
    except Exception:
        pass


@contextlib.contextmanager
def trace_span(
    name: str,
    *,
    observation_type: str = "span",
    trace_name: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    input_data: Any = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    parent_carrier: dict[str, str] | None = None,
) -> Iterator[trace.Span]:
    """Ouvre un span OpenTelemetry enrichi des attributs Langfuse v4."""
    st = start_telemetry()
    if st is None:
        yield trace.INVALID_SPAN
        return
    parent_ctx = propagate.extract(parent_carrier) if parent_carrier else None
    tracer = st.tracer_provider.get_tracer("alphaforge.agents")
    with tracer.start_as_current_span(name, context=parent_ctx) as span:
        try:
            if span.is_recording():
                span.set_attribute("langfuse.observation.type", observation_type)
                if trace_name:
                    span.set_attribute("langfuse.trace.name", trace_name)
                if session_id:
                    span.set_attribute("langfuse.session.id", session_id)
                    span.set_attribute("session.id", session_id)
                if user_id:
                    span.set_attribute("langfuse.user.id", user_id)
                    span.set_attribute("user.id", user_id)
                if tags:
                    span.set_attribute("langfuse.trace.tags", list(tags))
                if input_data is not None:
                    span.set_attribute("langfuse.observation.input", _serialize_io(input_data))
                for key, value in (metadata or {}).items():
                    if value is not None:
                        span.set_attribute(
                            f"langfuse.observation.metadata.{key}",
                            value if isinstance(value, (str, bool, int, float)) else _serialize_io(value),
                        )
        except Exception:
            pass
        yield span


def inject_trace_context() -> dict[str, str]:
    """Capture le contexte W3C (`traceparent`) pour relier `POST /runs` et `complete_run`."""
    if _TELEMETRY is None:
        return {}
    carrier: dict[str, str] = {}
    try:
        propagate.inject(carrier, context=otel_context.get_current())
    except Exception:
        pass
    return carrier


def flush_telemetry(timeout_millis: int = 2000) -> None:
    """Vide le BatchSpanProcessor avant que Lambda ne fige l'environnement."""
    if _TELEMETRY is None:
        return
    try:
        _TELEMETRY.tracer_provider.force_flush(timeout_millis=timeout_millis)
    except Exception as exc:
        log_event("telemetry.flush_error", error=type(exc).__name__)


def reset_for_tests(telemetry: StrandsTelemetry | None = None) -> None:
    """Réinitialise l'état du module pour les tests unitaires hors ligne."""
    global _INITIALIZED, _TELEMETRY
    _INITIALIZED = telemetry is not None
    _TELEMETRY = telemetry
