"""Contexte d'une requête, transmis aux outils hors de la vue du modèle.

userId, sessionId, runId, portfolioId et juridictions viennent d'ici, jamais
d'un paramètre fourni par le modèle (rule-identity-from-jwt). Le contexte
voyage dans l'invocation (invocation_state de Strands), jamais dans une
variable globale : deux invocations peuvent partager un conteneur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agents.data.store import DataStore


@dataclass
class RequestContext:
    user_id: str
    session_id: str
    store: DataStore
    message_id: str | None = None
    run_id: str | None = None
    portfolio_id: str = "main"
    province: str | None = None
    user_language: str = "en"
    # Registre du run lu par read_evidence (dernier run de la session, ou run en cours).
    evidence: list[dict[str, Any]] = field(default_factory=list)
    # Verdicts R1-R10 du même run : read_evidence les expose pour expliquer un échec.
    verdicts: list[dict[str, Any]] = field(default_factory=list)
    # Journal des appels d'outils de cette exécution (source de explanation).
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    # Passages renvoyés par search_regulation, par référence (P1, P2…) : l'auditeur
    # ne cite que ces références, le code reconstruit la citation (jamais inventée).
    passages: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Brouillon de mandat validé par propose_mandate (joint au message de l'assistant).
    captured: dict[str, Any] = field(default_factory=dict)
    # Objets du run en cours (moteur, règles), pour les outils de module.
    engine_result: Any = None
    mandate_item: dict[str, Any] | None = None
    clients: dict[str, Any] = field(default_factory=dict)

    @property
    def jurisdictions(self) -> list[str]:
        """Filtre de la KB : textes nationaux + province du mandat (contexte, jamais le modèle)."""
        return ["CA"] + ([self.province] if self.province and self.province != "CA" else [])
