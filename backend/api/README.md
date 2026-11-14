# Lambda API (CRUD léger)

Chantier WS4, branche `ws/api` : implémente les routes du contrat dont le
provider est `srv-api-light`. N'écris que dans ce dossier.

## Routes implémentées

- `GET /v1/me`
- `PUT /v1/me/profile`
- `GET /v1/conversations`
- `POST /v1/conversations`
- `PATCH /v1/conversations/{sessionId}`
- `DELETE /v1/conversations/{sessionId}`
- `GET /v1/conversations/{sessionId}/messages`
- `GET /v1/portfolios`
- `PUT /v1/portfolios/{portfolioId}/holdings`
- `GET /v1/agents`

Les routes de `srv-agent-runtime` (POST messages, résumé de portefeuille et
recherche de marché) appartiennent à `backend/agents/` (WS5).

## Exécution

Le point d'entrée Lambda attendu par l'infra est :

```text
backend/api/app.handler
```

Le handler attend un événement API Gateway HTTP API payload v2, extrait
l'identité du JWT (`sub`) et route selon `routeKey`.

## Tests

Aucun compte AWS ni appel réseau : les repositories DynamoDB et le
validateur de tickers sont simulés.

```bash
python -m pytest backend/api/tests backend/common/tests
```

Le `pyproject.toml` racine ne découvre encore que `backend/common/tests` ;
passe les deux dossiers explicitement jusqu'à sa mise à jour par l'intégration.

## Dépendances

- `backend/api/requirements.txt` ne contient que `python-ulid` : ni pandas,
  ni pyarrow à l'exécution, conformément au contrat pour la Lambda légère.
- Les variables d'environnement de tables sont celles de
  `backend/common/config.py`.
- `PUT /holdings` valide les tickers contre la copie embarquée
  `tickers.json`, autorisée par le contrat pour `srv-api-light`.

Voir `NOTES-api.md` pour les hypothèses et les points à coordonner avec
l'équipe.

## Régénérer `tickers.json`

Si WS3 change l'univers, régénère la copie embarquée avant de redéployer :

```bash
python -m backend.api.scripts.build_tickers \
    --input data/output/<version>/universe.parquet \
    --output backend/api/tickers.json \
    --source "universe.parquet@<date-ou-version>"
```

Le script accepte aussi un CSV contenant une colonne `ticker`. `pyarrow`
n'est requis que pour lire un Parquet lors de cette régénération locale, pas
par la Lambda.
