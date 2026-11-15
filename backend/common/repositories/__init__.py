"""Couche d'accès aux tables DynamoDB (contrat : section databases).

WS0 fixe ici les signatures, les docstrings et le comportement attendu.
WS2 (branche ws/db) implémente ce dossier sans changer les signatures.

Conventions partagées :
- Les fonctions qui prennent user_id ne renvoient jamais une ressource d'un
  autre utilisateur (une ressource étrangère se comporte comme inexistante).
- Les curseurs de pagination sont des chaînes opaques (base64 du
  LastEvaluatedKey de DynamoDB), jamais interprétés par le front.
- Une ressource introuvable ou non possédée lève ApiError avec le code du
  contrat (CONVERSATION_NOT_FOUND, PORTFOLIO_NOT_FOUND), ou retourne None
  quand la docstring le précise (les Lambdas décident alors de la réponse).
"""

from backend.common.repositories import analyses, conversations, messages, portfolios, users

__all__ = ["analyses", "conversations", "messages", "portfolios", "users"]
