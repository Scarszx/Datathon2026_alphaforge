# NOTES WS2 db : hypothèses et écarts avec le contrat

Signatures de WS0 inchangées. Points à valider avec l'équipe :

1. **Nom de l'index local de Conversations.** Le contrat dit « index local sur updatedAt » sans nom. Le code utilise `updatedAt-index` (`conversations.UPDATED_AT_INDEX`), clé de partition `userId`, clé de tri `updatedAt` (S), projection `ALL`. **WS1 doit créer l'LSI avec ce nom exact** (un LSI ne peut être ajouté qu'à la création de la table).
2. **Dépendances.** `pyproject.toml` est hors périmètre WS2. À ajouter : `boto3` (dépendance ; fourni par le runtime Lambda, inutile dans les zips) et `moto[dynamodb]>=5` en dev. En local : `uv pip install boto3 "moto[dynamodb]"`.
3. **`update_investor_profile` sur un utilisateur absent** lève `ApiError("INTERNAL")` : le contrat n'a pas de code « utilisateur inconnu ». La Lambda API peut appeler `put_user_if_absent` avant (le `username` vient alors des claims JWT).
4. **Nom du portefeuille par défaut** : `"Principal"` (`portfolios.MAIN_PORTFOLIO_NAME`), le contrat ne fixe que `portfolioId = 'main'`.
5. **`messages.list_messages` / `delete_messages` ne prennent pas `user_id`** : l'appelant doit vérifier la propriété avec `conversations.get_conversation` avant. `userId` est stocké sur chaque message mais jamais renvoyé.
6. **`limit` est borné à 1..100** côté repository (défaut 20 et 50 selon le contrat).
7. **Curseurs** : base64 urlsafe du JSON de `LastEvaluatedKey`. Un curseur illisible, ou émis pour un autre utilisateur ou une autre session, lève `ApiError("VALIDATION_ERROR")`.
8. **Champs renvoyés** : uniquement ceux des schémas du contrat. `createdAt` est stocké dans Users mais absent de `schema-user`, donc non renvoyé ; `userId` n'est pas renvoyé dans conversations, messages ni portefeuilles.
9. **`rename_conversation` ne modifie pas `updatedAt`** (renommer ne fait pas remonter la conversation). `touch_conversation` et `delete_conversation` lèvent `CONVERSATION_NOT_FOUND` si la conversation est absente ou étrangère (écriture conditionnelle, pas d'item fantôme).
10. **Nombres** : les `float` sont convertis en `Decimal` à l'écriture et relus en `int` ou `float` (une valeur entière comme `190.0` revient en `190`).
11. **`delete_messages`** n'est pas atomique avec `delete_conversation` : supprimer les messages d'abord, puis la conversation.
12. **Horodatage** : `YYYY-MM-DDTHH:MM:SSZ` (seconde près). Deux conversations touchées dans la même seconde ont un ordre arbitraire entre elles.
