"""Amazon Bedrock (Converse API) wrapper used ONLY by the explainability agent to phrase verified facts.

The model never computes numbers and never chooses assets: it receives a JSON fact sheet and must rephrase it.
Its output is then checked by the governance agent (numbers traceable, no advice wording) and discarded if it fails.
Set LLM_MODE=off to run fully deterministic (e.g. no AWS credentials).
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional, Tuple

log = logging.getLogger("alphaforge.llm")
DEFAULT_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
_client = None


def enabled() -> bool:
    return os.environ.get("LLM_MODE", "bedrock").lower() != "off"


def model_id() -> str:
    return os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL)


def _get_client():
    global _client
    if _client is None:
        import boto3
        from botocore.config import Config
        _client = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1")),
                               config=Config(retries={"max_attempts": 3, "mode": "adaptive"}, read_timeout=20, connect_timeout=5))
    return _client


SYSTEM = (
    "Tu es l'agent d'explicabilité d'AlphaForge, un outil de SIMULATION pédagogique (aucune transaction, aucun conseil personnalisé). "
    "Tu reçois une fiche de faits JSON produite par d'autres agents. Règles strictes : "
    "1) utilise UNIQUEMENT les chiffres présents dans la fiche, recopiés tels quels (même arrondi); n'en calcule aucun nouveau; "
    "2) distingue explicitement ce qui est un FAIT historique, une HYPOTHÈSE de l'équipe et un SCÉNARIO fictif; "
    "3) si la fiche signale une incohérence avec le profil, commence par la dire clairement et explique le risque, sans moraliser; "
    "4) ne dis jamais « achetez », « vendez », « garanti », « sans risque »; ne prédis aucun rendement futur; "
    "5) mentionne l'incertitude principale et une limite; "
    "6) cite les sources entre crochets avec leurs identifiants (ex. [prices], [macro]); "
    "7) français clair, 130 à 190 mots, phrases courtes, sans titre ni liste à puces."
)


def narrate(facts: dict, max_tokens: int = 450) -> Tuple[Optional[str], dict]:
    """Returns (text or None, metadata). Never raises."""
    meta = {"model": model_id(), "enabled": enabled()}
    if not enabled():
        return None, meta
    t0 = time.perf_counter()
    try:
        r = _get_client().converse(
            modelId=model_id(),
            system=[{"text": SYSTEM}],
            messages=[{"role": "user", "content": [{"text": "Fiche de faits :\n" + json.dumps(facts, ensure_ascii=False, default=str)}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
        )
        text = "".join(b.get("text", "") for b in r["output"]["message"]["content"]).strip()
        meta.update({"latencyMs": int((time.perf_counter() - t0) * 1000), "inputTokens": r.get("usage", {}).get("inputTokens"),
                     "outputTokens": r.get("usage", {}).get("outputTokens")})
        return text or None, meta
    except Exception as e:  # noqa: BLE001 - degrade gracefully to the deterministic template
        log.warning("bedrock narrate failed: %s", e)
        meta.update({"error": type(e).__name__, "latencyMs": int((time.perf_counter() - t0) * 1000)})
        return None, meta
