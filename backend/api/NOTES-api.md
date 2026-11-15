# NOTES WS4 / WS4b api : hypothèses et points à valider

Signatures de WS0/WS0b/WS2/WS2b inchangées. Points relevés pendant l'implémentation :

1. **Username du schema-user.** Le contrat exige `username` mais ne dit pas
   quel claim Cognito le fournit. Le code utilise `cognito:username`, puis
   `username`, puis `sub` en dernier repli. `displayName` vient du claim
   `name` quand il existe.
2. **PUT /me/profile sans GET préalable.** Le contrat dit que GET /me crée le
   profil, mais ne dit pas ce que fait PUT si l'utilisateur n'existe pas.
   Par prudence, PUT appelle aussi `put_user_if_absent` (idempotent) avant
   `update_investor_profile` pour éviter une erreur `INTERNAL`.
3. **Champs inconnus.** Les schémas du contrat ne précisent pas
   `additionalProperties`. Les corps contenant un champ non prévu sont
   refusés en `VALIDATION_ERROR` pour éviter les fautes de frappe silencieuses.
4. **SessionId.** Le contrat fixe un UUID v4 généré par le serveur : les
   paramètres de chemin sont validés (version 4, variante RFC 4122). Un
   sessionId mal formé renvoie `VALIDATION_ERROR`, un sessionId valide mais
   étranger renvoie `404`.
5. **Pagination.** Le contrat fixe seulement les défauts. `limit` est validé
   entre 1 et 100, comme dans la couche WS2, plutôt que d'accepter n'importe
   quel entier. Un curseur présent doit être une chaîne non vide.
6. **Route inconnue.** Le contrat n'a pas de code `ROUTE_NOT_FOUND`. Une
   route ou méthode non enregistrée renvoie `VALIDATION_ERROR` (400).
7. **Univers de tickers.** La validation utilise la copie embarquée
   `tickers.json`, autorisée par le contrat pour `srv-api-light`. Il n'y a
   donc **plus de lecture S3 et plus de droit S3 à demander à WS1** pour
   ces routes. Le fichier est initialisé depuis
   `assets_universe.csv@2026-11-13`. Si WS3 élargit l'univers, il faut
   régénérer `tickers.json` avant le déploiement ; sinon, un nouveau ticker
   valide sera refusé.
8. **Holdings.** `quantity > 0` est appliqué. `avgCost` est seulement un
   nombre fini, car le contrat n'impose pas de signe. L'unicité des tickers
   n'est pas imposée, car le contrat ne la précise pas. Une liste vide est
   acceptée pour vider le portefeuille.
9. **Suppression d'une conversation.** Elle supprime les messages, les
   analyses (`delete_analyses(session_id, user_id)`), puis la conversation,
   comme recommandé par `NOTES-db.md` et WS4b. L'opération reste non atomique
   (DynamoDB ne couvre pas les trois tables en une transaction).
10. **Limite des messages.** La règle `content <= 2000` concerne
    `POST /messages`, route de WS5 : elle n'est pas appliquée ici.
11. **BaseCurrency.** Aucune route WS4 ne reçoit `baseCurrency` en entrée
    (hors devise d'une opération de mandat). Les valeurs par défaut restent
    `CAD` pour l'utilisateur et le portefeuille `main`.
12. **Tests et pyproject.** `testpaths` racine ne contient que
    `backend/common/tests`. L'intégration devra y ajouter
    `backend/api/tests` pour qu'un `pytest` nu découvre les tests WS4/WS4b, et
    ajouter `boto3`/`moto` en dépendances de développement.
13. **Registre des agents (v0.4.0).** Le contenu de `registry.json` est une
    copie statique des sections `agents` (statut `retenu` uniquement :
    `agent-orchestrator`, `agent-auditor`, `agent-writer`), `modules`
    (`module-engine`, `module-rules`, `module-verifier`) et `tools` (13 outils)
    du contrat v0.4.0. Les clés snake_case dans `limits` (`max_tool_calls`,
    etc.) sont conservées telles quelles car le contrat les écrit ainsi.
14. **Mandats (WS4b, v0.4.0).**
    - **Validation des tickers dans `POST /mandates` :** le contrat déclare
      `errors: ["CONVERSATION_NOT_FOUND", "VALIDATION_ERROR"]` sur
      `api-mandates-create`. Un ticker d'`operations` ou `subjectTicker`
      absent de l'univers lève donc `VALIDATION_ERROR` (400) plutôt que
      `ASSET_NOT_FOUND` (404), tout en passant par le `ticker_validator`
      injectable.
    - **Province :** conformément au contrat (`schema-investor-profile` et
      spécification WS4b), `"CA"` (juridiction fédérale/nationale de la KB) est
      exclu du champ `province` de l'utilisateur et du mandat.
    - **Seuils par défaut (`effectiveMaxLossPct`) :** lus depuis
      `backend/api/mandate_defaults.json` (`< 3` ans : `10`, `3–8` ans : `20`,
      `> 8` ans : `35`), surchargeables via `RULES_CONFIG_PATH`.
    - **Contrôle de cohérence (`warnings`) :** rédigés en anglais conformément
      à `conventions.language_policy` (tout le système interne est en anglais).
