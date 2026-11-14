# NOTES WS4 api : hypothèses et points à valider

Signatures de WS0/WS2 inchangées. Points relevés pendant l'implémentation :

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
   cette route. Le fichier est initialisé depuis
   `assets_universe.csv@2026-11-13`. Si WS3 élargit l'univers, il faut
   régénérer `tickers.json` avant le déploiement ; sinon, un nouveau ticker
   valide sera refusé en `ASSET_NOT_FOUND` (risque de liste périmée).
8. **Holdings.** `quantity > 0` est appliqué. `avgCost` est seulement un
   nombre fini, car le contrat n'impose pas de signe. L'unicité des tickers
   n'est pas imposée, car le contrat ne la précise pas. Une liste vide est
   acceptée pour vider le portefeuille.
9. **Suppression d'une conversation.** Elle supprime les messages puis la
   conversation, comme recommandé par `NOTES-db.md`. L'opération reste non
   atomique (DynamoDB ne couvre pas les deux tables).
10. **Limite des messages.** La règle `content <= 2000` concerne
    `POST /messages`, route de WS5 : elle n'est pas appliquée ici.
11. **BaseCurrency.** Aucune route WS4 ne reçoit `baseCurrency` en entrée.
    Les valeurs par défaut restent `CAD` pour l'utilisateur et le portefeuille
    `main` ; la validation CAD/USD sera utile à WS5 si une entrée apparaît.
12. **Tests et pyproject.** `testpaths` racine ne contient que
    `backend/common/tests`. L'intégration devra y ajouter
    `backend/api/tests` pour qu'un `pytest` nu découvre les tests WS4, et
    ajouter `boto3`/`moto` en dépendances de développement.
13. **Registre des agents.** Le contenu de `registry.json` est une copie
    manuelle de la section agents et tools du contrat. Toute modification du
    contrat devra être répercutée dans ce fichier. Les clés snake_case dans
    `limits` (`max_tool_calls`, etc.) sont conservées telles quelles car le
    contrat lui-même les écrit ainsi.
