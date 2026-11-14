"""Accès à la table Portfolios (contrat : db-portfolios).

Clé : partition userId, tri portfolioId ('main' par défaut). holdings est une
liste de { ticker, quantity, avgCost } ; aucun prix ni nom n'est stocké.
"""

from __future__ import annotations

from typing import Any


def list_portfolios(user_id: str) -> list[dict[str, Any]]:
    """Retourne tous les portefeuilles de l'utilisateur (schema-portfolio-list)."""
    raise NotImplementedError


def get_portfolio(user_id: str, portfolio_id: str) -> dict[str, Any] | None:
    """Retourne le portefeuille s'il appartient à user_id, sinon None.

    Un portefeuille d'un autre utilisateur est invisible (comme inexistant).
    """
    raise NotImplementedError


def ensure_main_portfolio(user_id: str, base_currency: str = "CAD") -> dict[str, Any]:
    """Crée le portefeuille 'main' vide s'il n'existe pas (contrat :
    api-portfolios-list le crée au premier GET) et le retourne.

    Écriture conditionnelle, donc idempotent.
    """
    raise NotImplementedError


def replace_holdings(
    user_id: str, portfolio_id: str, holdings: list[dict[str, Any]]
) -> dict[str, Any]:
    """Remplace toute la liste des positions (contrat : api-portfolio-holdings-put,
    le front envoie l'état complet de sa table), met à jour updatedAt et retourne
    le portefeuille.

    Lève ApiError('PORTFOLIO_NOT_FOUND') si absent ou non possédé.
    holdings : liste de { ticker, quantity, avgCost }, validée par la Lambda API.
    """
    raise NotImplementedError
