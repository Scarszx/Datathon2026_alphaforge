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

## WS2b db v0.4 : table Analyses

Signatures de WS0b inchangées. Points à valider avec l'équipe :

13. **Attributs hors liste du contrat.** `schema-run` contient `userLanguage` et `explanation`, absents de la liste `attributes` de db-analyses. Le repository stocke tous les champs reçus (DynamoDB sans schéma) : la liste du contrat est à compléter.
14. **Version de mandat par session.** La version est calculée sur toute la partition `sessionId` (clé partagée), pas par utilisateur. La propriété de la conversation doit être vérifiée par l'appelant (`conversations.get_conversation`) avant `put_mandate` / `put_run`.
15. **Concurrence de `put_mandate`.** Écriture conditionnelle `attribute_not_exists(itemKey)`, puis relecture et réessai, au plus `MAX_VERSION_ATTEMPTS = 5` fois. Au-delà : `ApiError("INTERNAL")`. Les champs `sessionId`, `version`, `userId`, `type`, `itemKey` fournis par l'appelant sont ignorés. `confirmedAt` vaut `now_iso()` s'il est absent.
16. **`put_run` sur un runId existant** lève `ApiError("INTERNAL")` (le runId est un ULID serveur, un doublon est un bug). `createdAt` vaut `now_iso()` s'il est absent.
17. **`update_run`** refuse (`ValueError`) de modifier `sessionId`, `itemKey`, `userId`, `type`, `runId`. Condition `attribute_exists(itemKey) AND userId = :uid` : run absent ou étranger → `RUN_NOT_FOUND`, aucun item fantôme. `fields` vide : renvoie le run tel quel.
18. **Objets renvoyés** : `userId`, `type`, `itemKey` ne sont jamais renvoyés. Les nombres suivent la règle 10.
19. **`delete_analyses`** supprime par `batch_writer` les seuls items de `user_id` ; à appeler avec `delete_messages`, avant `delete_conversation`.
20. **Limite de 400 Ko** non gérée : si un run l'approche, déplacer `evidence` dans S3 (note du contrat).
21. **WS1b** : table `Analyses`, `sessionId` (S) HASH, `itemKey` (S) RANGE, sans index, à la demande. Le conftest partagé ne crée pas cette table : `test_repo_analyses.py` la crée dans sa propre fixture.
22. **Champs de cadrage des messages (WS5, à valider par l'équipe).** `schema-message` porte `quickReplies`, `mandateDraft` et `runId`, mais ni le repository ni la liste d'attributs `db-messages` du contrat ne les prévoyaient. `put_message` accepte maintenant `quick_replies`, `mandate_draft` et `run_id` (optionnels, réservés à `role = assistant`), et `list_messages` les renvoie quand ils sont présents. **Écart de contrat** : ajouter `quickReplies`, `mandateDraft`, `runId` à `databases.db-messages.attributes`.
23. **`userLanguage` de la conversation (WS5, à valider par l'équipe).** `schema-conversation` porte `userLanguage`, absent du repository et de `db-conversations.attributes`. `set_user_language(user_id, session_id, lang)` l'écrit sans toucher `updatedAt` ; `_to_conversation` ne le renvoie que s'il est enregistré (le défaut `en` du contrat est appliqué par le lecteur). **Écart de contrat** : ajouter `userLanguage` à `databases.db-conversations.attributes`.
24. **`get_latest_run(session_id, user_id)` (WS5).** Dernier run possédé de la session (runId ULID, donc ordre chronologique), pour `read_evidence` (« registre du dernier run de la session »). Ajout pur, aucune signature existante modifiée.
