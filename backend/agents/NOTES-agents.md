# NOTES WS5 (Lambda agents)

Hypothèses, décisions et écarts trouvés en implémentant `srv-agent-runtime` contre le contrat v0.4.0.
**À valider par l'équipe** : les points marqués ⚠️.

## Décisions prises avec l'équipe (2026-11-14)

1. **Complétion d'un run : asynchrone.** `POST runs` renvoie le run `partial` (moteur + règles, en environ 1 s hors démarrage à froid), puis la Lambda s'invoque elle-même (`InvocationType=Event`, événement interne `{"internal": "complete_run", ...}`, jamais une route). Le changement d'infra est dans `infra/terraform/iam.tf` (`SelfInvokeCompleteRun`) et `lambda.tf` (timeout de 180 s). ⚠️ **`terraform apply` reste à faire par l'équipe.** Sans Lambda (banc local), la complétion se fait dans la requête.
2. **Logique du mandat partagée** : `backend/common/mandates.py`, `backend/common/validation.py` et `backend/common/mandate_defaults.json` (déplacés depuis `backend/api`, qui les réexporte). Il n'existe toujours qu'une copie des seuils par horizon.
3. **Persistance des champs de cadrage** : `messages.put_message(..., quick_replies, mandate_draft, run_id)`, `conversations.set_user_language()` et `analyses.get_latest_run()` (voir `backend/common/repositories/NOTES-db.md`, points 22 à 24). ⚠️ **Écart de contrat** : ajouter `quickReplies`, `mandateDraft` et `runId` à `db-messages.attributes`, et `userLanguage` à `db-conversations.attributes`.

## Écarts et choix à valider

4. ⚠️ **Le scénario vedette ne donne pas une alternative en PASS, mais en WARN.** Sur le vrai jeu de départ comme sur le jeu synthétique, le scénario 1 (NVDA) est en **FAIL** (R1, et R2 en WARN), et l'alternative (obligations courtes) passe R1, R2 et R7. Mais **R6 est en WARN dans les 3 scénarios** : RY.TO pèse environ 15 % du portefeuille actuel (15 k$ en direct, plus sa part dans XIU.TO), au-dessus du seuil d'hypothèse de 10 %. Le verdict d'un scénario étant le pire de ses règles, l'alternative est en **WARN**. Trois options : relever le seuil WARN de R6 (par exemple 15 %, dans `rules_config.json`), changer le portefeuille de démonstration, ou l'assumer dans la vidéo (« la concentration existe déjà dans le portefeuille actuel »). Le test `test_r6_herite_du_portefeuille_actuel` documente ce cas.
5. ⚠️ **R1 : bandes de volatilité (nouvelle hypothèse d'équipe).** Le contrat dit « si l'idée suppose un profil plus élevé, WARN ou FAIL », sans dire comment mesurer ce profil. Le profil implicite d'un actif ou d'un portefeuille se lit dans sa volatilité annualisée : ≤ 10 % → 1, ≤ 14 % → 2, ≤ 18 % → 3, ≤ 25 % → 4, au-delà → 5 (`riskBandsByVolatility`). Un écart d'au moins 2 crans donne FAIL, un écart d'un cran WARN. Le scénario 0 est plafonné à WARN, puisque c'est l'état actuel.
6. **R2 : la pire baisse se mesure sur la fenêtre d'analyse** (5 ans glissants, `windowYears`). Les tests de résistance dans la fenêtre sont donc inclus. Ceux qui en sortent, comme le krach COVID avec le jeu élargi sur 10 ans, sont calculés, inscrits au registre et affichés, mais n'entrent pas dans le verdict. Le seuil d'alerte vaut 80 % du plafond (`maxLossWarnRatio`, hypothèse d'équipe).
7. **`threshold.nature` de R2** : la valeur vaut `team_assumption` pour le défaut par horizon. Pour une perte saisie par l'utilisateur, `nature` est **omis** : l'enum du contrat (`text | team_assumption`) n'a pas de valeur « réponse de l'utilisateur ».
8. **`scenario.metrics`** ajoute aux clés d'exemple du contrat `totalReturn`, `stressCovid2020` et `cryptoWeight`. Ce sont toujours des identifiants EV.
9. **Données manquantes d'un scénario** (historique trop court, période de stress non calculable) : elles vont dans `run.explanation.limitations`, car `schema-scenario` n'a pas de champ pour elles.
10. **`verdict.message`** (traduit) n'est présent qu'à `status = done`, ou dès `partial` si `userLanguage = en`. En `partial`, le front affiche le libellé de `reasonCode`, une clé stable.
11. **`quickReplies`** reste un tableau de chaînes dans `userLanguage` (contrat). Le lien « réponse affichée → valeur interne anglaise » n'a pas de champ : c'est l'orchestrateur qui réinterprète la réponse cliquée au tour suivant.
12. **`GUARDRAIL_BLOCKED`** (422) : `error.message` contient le message de refus configuré dans le Guardrail (Terraform, en anglais). Il n'est pas traduit. Rien n'est écrit dans l'historique.
13. **`explanation.steps`** contient les vrais appels d'outils, plus une étape `tool: "agent_invocation"` par invocation d'agent (le rédacteur et la traduction n'appellent pas forcément d'outil). Ces étapes ne sont pas émises comme `tool.call`.
14. **Échec du rédacteur** (fail-open du contrat) : le run passe en `status = error`, avec ses scénarios, ses verdicts et ses citations. `narrative` et `verifier` sont absents.
15. **Traduction** : une section dont la traduction perd ou ajoute un emplacement est affichée en anglais, et `verifier.placeholdersMatch = false` le signale.
16. **Vérificateur** : sont autorisés sans emplacement les constantes du mandat, les années, les numéros de documents (31-368, GN-3200-26-001…), les règles (R1-R10) et les petits entiers (≤ 10). Le reste est masqué, que ce soit un pourcentage, un montant, des points de base, un ratio, un décimal ou un entier > 10. Les motifs interdits existent en anglais et en français ; aucun n'est construit à partir d'une sortie de modèle.
17. **Historique de l'orchestrateur** : il est reconstruit à partir des 50 **premiers** messages de la session (`list_messages` pagine dans l'ordre chronologique). C'est suffisant pour une session de démonstration ; au-delà, il faudrait une lecture « derniers N ».
18. **`MANDATE_NOT_CONFIRMED`** n'est atteignable que si `confirmedAt` manque : tout mandat écrit par `POST /mandates` est confirmé.

## Coordination avec WS3 (données)

19. **`etf_enriched.json`** : le format lu est `{ "etfs": { "<ticker>": { sectorWeights: {secteur: %}, countryWeights: {pays: %}, topHoldings: [{ticker, name, weight %}], merPct, exclusions?, esgMethodologyUrl?, sourceUrl, asOfDate } } }`. Une liste `[{ticker, ...}]` est aussi acceptée. Les tickers de `topHoldings` doivent être des symboles de l'univers pour que la lecture par transparence de R6 fonctionne.
20. **`macro.parquet.publication_date`** est lue si elle existe (R10). Le jeu de départ ne l'a pas : la seule série utilisée (V39079, journalière) est connue à sa date.
21. **`manifest.json.periodEnd`** sert de date d'analyse (`asOf`). À défaut, c'est le dernier cours de SPY ou de XIU.TO.

## Tests et banc

22. **Fixtures synthétiques** (`tests/fixtures/make_fixtures.py`, avec une graine fixe) : le contrat interdit de redistribuer les prix Yahoo. Elles ont la forme des crises réelles, mais leurs valeurs sont fictives.
23. **Vrai jeu de départ** : `ALPHAFORGE_STARTER_DIR=<…>/alphaforge_starter pytest backend/agents/tests/test_starter_dataset.py`, ignoré par défaut. Ce test a révélé un bug corrigé : une hausse de taux isolée en fin de série était prise pour un cycle (`MIN_HIKES = 2`).
24. **`pytest` à la racine** lance `backend/common` et `backend/agents`. **`backend/api/tests` se lance à part**, parce que `test_universe` vérifie que pyarrow n'est pas importé dans le processus.
25. **Faux modèle Strands** (`tests/fake_model.py`) : la vraie boucle `Agent` tourne (outils, hooks, sortie structurée, plafonds, délai) ; seul Bedrock est remplacé.

## Points ouverts (compte AWS)

26. ⚠️ **Taille de la couche pandas non mesurée** : les identifiants AWS avaient expiré. Le zip agents fait 24 Mo compressé et 46,8 Mo décompressé, après retrait de mcp, starlette, uvicorn, cryptography et jwt (`build_lambdas.sh`), modules jamais importés (vérifié par un import bloquant). La limite est de 250 Mo décompressés avec la couche.
27. ⚠️ **Faux positifs du Guardrail et vrai modèle** : `scripts/smoke.py` n'a pas encore été lancé (il coûte des appels Bedrock). Il teste 3 demandes normales, 2 demandes interdites, un Retrieve filtré et un vrai tour de l'orchestrateur.
28. **Budget de 25 s de `POST messages`** : trois appels ApplyGuardrail (original, traduction, réponse) s'ajoutent à l'orchestrateur. À mesurer ; si besoin, le Guardrail d'entrée ne porterait que sur la traduction.
