"""Recherche dans la Knowledge Base réglementaire (Bedrock KB Retrieve), filtrée par juridiction.

Le filtre de métadonnées vient du contexte : juridiction ∈ {CA, province du
mandat}, et éventuellement sujets. Les passages renvoyés sont des données non
fiables : le texte est tronqué et neutralisé (aucune balise d'encadrement ne
peut s'y glisser) avant d'être montré à un modèle.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from backend.agents import telemetry
from backend.common import config

KNOWN_SUBJECTS = (
    "kyc", "profil_risque", "convenance", "instruction", "reglement", "crypto", "esg", "fonds", "oeo",
    "aide_decision", "recommandation", "titres_proteges", "relation_client", "cadrage", "questions_investisseur",
)

# Titres des documents du corpus (docs/for_KB/README.md), en anglais.
DOCUMENT_TITLES = {
    "CA_21-329": "CSA/IIROC Staff Notice 21-329 (crypto-asset trading platforms)",
    "CA_21-332": "CSA Staff Notice 21-332 (crypto-asset trading platforms, pre-registration undertakings)",
    "CA_31-103CP": "Companion Policy 31-103CP (registration requirements)",
    "CA_31-103": "National Instrument 31-103 (registration requirements, exemptions and ongoing obligations)",
    "CA_31-368": "Joint CSA/CIRO Staff Notice 31-368 (client focused reforms)",
    "CA_81-334": "CSA Staff Notice 81-334 (ESG-related investment fund disclosure)",
    "CA_CIRO_GN-3200-26-001": "CIRO Guidance GN-3200-26-001 (order-execution-only services)",
    "CA_CIRO_bulletin-26-0059": "CIRO Bulletin 26-0059 (order-execution-only guidance)",
    "ON_FSRA_rule-2020-001": "FSRA Rule 2020-001 (financial professionals title protection)",
    "QC_AMF_financial-planner-title": "AMF: the financial planner title in Québec",
    "QC_NBDB_relationship-disclosure-information": "National Bank Direct Brokerage: relationship disclosure information",
    "QC_NBDB_tips-better-investment-decisions": "National Bank Direct Brokerage: questions before investing",
    "SK_FCAA_FPFA-proposed-regulations-notice": "FCAA: proposed Financial Planners and Financial Advisors regulations",
}

MAX_PASSAGES = 5
MAX_EXCERPT_CHARS = 700


def document_title(uri: str | None) -> str:
    name = PurePosixPath(uri or "").name
    for prefix in sorted(DOCUMENT_TITLES, key=len, reverse=True):
        if name.startswith(prefix):
            return DOCUMENT_TITLES[prefix]
    return name or "Unknown document"


def neutralize(text: str) -> str:
    """Retire les balises qui pourraient fermer l'encadrement des données."""
    return (
        text.replace("<", "‹").replace(">", "›").replace("\u0000", "").strip()
    )


def build_filter(jurisdictions: list[str], subjects: list[str] | None) -> dict[str, Any]:
    clauses: list[dict[str, Any]] = [{"in": {"key": "juridiction", "value": jurisdictions}}]
    valid = [s for s in subjects or [] if s in KNOWN_SUBJECTS]
    if len(valid) == 1:
        clauses.append({"listContains": {"key": "sujets", "value": valid[0]}})
    elif len(valid) > 1:
        clauses.append({"orAll": [{"listContains": {"key": "sujets", "value": s}} for s in valid]})
    return clauses[0] if len(clauses) == 1 else {"andAll": clauses}


_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        import boto3

        _CLIENT = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
    return _CLIENT


def retrieve(query: str, jurisdictions: list[str], subjects: list[str] | None = None, client=None) -> list[dict[str, Any]]:
    """Appelle Retrieve et renvoie au plus MAX_PASSAGES passages normalisés."""
    kb = config.kb_id()
    if not kb:
        raise RuntimeError("KB_ID is not configured")
    with telemetry.trace_span(
        "kb.retrieve",
        observation_type="retriever",
        input_data={"query": query, "jurisdictions": jurisdictions, "subjects": subjects},
    ) as span:
        response = (client or _client()).retrieve(
            knowledgeBaseId=kb,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": MAX_PASSAGES,
                    "filter": build_filter(jurisdictions, subjects),
                }
            },
        )
        passages = []
        for result in response.get("retrievalResults", [])[:MAX_PASSAGES]:
            metadata = result.get("metadata") or {}
            uri = (result.get("location") or {}).get("s3Location", {}).get("uri") or metadata.get("x-amz-bedrock-kb-source-uri")
            page = metadata.get("x-amz-bedrock-kb-document-page-number")
            # Extrait fidèle (registre, jamais traduit) ; la version neutralisée est celle montrée au modèle.
            excerpt = " ".join(((result.get("content") or {}).get("text", "")).split())[:MAX_EXCERPT_CHARS]
            passages.append({
                "document": document_title(uri),
                "section": f"page {int(page)}" if isinstance(page, (int, float)) else None,
                "excerpt": excerpt,
                "jurisdiction": metadata.get("juridiction"),
                "version": metadata.get("date_version"),
                "url": metadata.get("source_url"),
                "file": PurePosixPath(uri or "").name or None,
                "score": round(float(result.get("score", 0.0)), 3),
            })
        telemetry.set_span_output(
            span,
            [
                {
                    "document": p["document"],
                    "section": p["section"],
                    "jurisdiction": p["jurisdiction"],
                    "score": p["score"],
                }
                for p in passages
            ],
        )
        return passages
