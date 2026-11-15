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

## Auditeur : recherches lancées par le code (2026-11-15)

29. **Le code lance les recherches, pas le modèle.** Pour chaque règle présente (R1-R9), `llm/auditor/agent.py` fait une recherche par sujet de `RULE_SUBJECTS` (un sujet par appel, jamais `orAll`), avec la phrase `RULE_TOPICS[règle] + motif déjà calculé` du verdict le plus grave. Les recherches tournent en parallèle (≤ 16, 13-14 mesurées), les passages des sujets sont fusionnés (le meilleur de chaque sujet d'abord), dédoublonnés et plafonnés à 5. Le modèle n'a plus d'outil : il répond « P2 soutient la règle » ou « aucun » ; une réf qui n'est pas dans les candidats **de la règle du groupe** est ignorée. ⚠️ Écart avec le contrat 0.4.2 (`agent-auditor.allowed_tools`, `tool-search-regulation.used_by`, `max_tool_calls`) : à faire valider avant de le modifier.
30. **Juridiction** : `kb.retrieve` jette tout passage dont `metadata.juridiction` est absente ou hors de {CA, province}, en plus du filtre envoyé à Bedrock.
31. **Un `pass` garde sa phrase par défaut** (« la règle n'a pas sauté »), jamais une phrase du modèle ; la citation, si elle existe, identifie la règle. ⚠️ Le rédacteur n'a pas été modifié : son prompt dit « citing the grounding regulation where a citation exists » et peut encore placer une citation à côté d'un pass comme si elle l'approuvait.
32. **Coupe des extraits** : plus de coupe sur `;`/`:` ni après `s.`, `art.`, `No.`, `para.`… (`kb._ABBREVIATIONS`) ; sans vraie fin de phrase après 40 % de la limite, coupe à un mot avec « … ». L'extrait reste toujours un préfixe exact du texte de la base.
33. **Questions de suivi sur KB-nn** : le prompt de l'orchestrateur impose `read_evidence(evidence_id)` puis la recopie mot pour mot de `excerpt` (anglais, entre guillemets), car le résumé du registre ne contient pas le texte.

## Lot A : vocabulaire et citations (2026-11-15)

34. **Seules les règles déclenchées (warn, fail) sont auditées.** `needs_regulation(rule, reason_code, status)` renvoie False pour pass et not_verified : ni recherche, ni citation, ni appel de modèle si tout est pass (GN-3200-26-001, 2.1.1 : un extrait du régulateur sous une règle « non déclenchée » se lit comme un accord). Mesuré dans Langfuse le 2026-11-15 avant ce changement : 13 recherches et 9 à 12 citations par run, dont la plupart sous des pass. ⚠️ Écart de contrat 0.4.3 : 0.4.4 le consigne.
35. **Le vocabulaire d'approbation réel diffère de la liste de la mission.** Les récits tracés contiennent « passes », « fits the retained risk profile », « in line with {KB-01} », « conviennent à ce mandat », « est conforme », « correspond au profil ». `JUDGEMENT_PATTERNS` (verifier.py) les couvre, en plus des motifs de la mission. Fixtures : `tests/fixtures/langfuse_narratives_2026-11-15.json`.
36. **Négations.** « is not suitable for you » et « non conforme » sont aussi des jugements, donc masqués. Exception : une phrase où l'outil dit qu'il ne juge pas (« does not assess », « takes no position », « ne se prononce pas »), qui garde ses mots de convenance mais pas ses mots de recommandation. « conformément à » reste, sauf devant un emplacement {KB-nn} (utilisé comme approbation dans les traces).
37. **Motifs traduits.** Les motifs de verdict (messageEn traduits) ne passaient pas par le vérificateur. `pipeline._translate_run_texts` remplace par la phrase anglaise tout motif traduit qui contient un jugement. Le prompt de traduction interdit aussi d'introduire « conforme », « convient », « adapté ».
38. **`rulesVersion` = 2 sur les runs** (`pipeline.RULES_VERSION`). Les runs enregistrés avant n'ont pas ce champ : l'interface ignorera leurs citations de règles pass/not_verified et les marquera comme produits par une version précédente.
39. **Numérotation des références P1…** : elle suit l'ordre des recherches (parallèles). Un test ne doit pas coder une référence précise pour une règle ; `test_routes._script_completion` envoie P1 à P9 et le code ne garde que les candidats de la règle.

## Lot B : comparaison par catégorie (2026-11-15)

40. **Le scénario 2 n'existe plus par défaut.** `run_engine` ne le construit que si `mandate.compareCategory` est présent ; la catégorie vient de `backend/common/comparison_categories.json` (partagé avec la Lambda API) et l'utilisateur la choisit. Aucun titre n'est jugé : chaque `add` et `set_weight` est remplacé par le FNB d'approximation au même montant ; deux `set_weight` vers le même FNB sont cumulés. ⚠️ Écart de contrat 0.4.4 : consigné en 0.4.5.
41. **Niveau affiché** (« a category this tool places at level N ») : bande de volatilité du FNB d'approximation lue dans les données (EV d'hypothèse « Risk level of the category … »), pas le `level` statique du fichier, qui ne sert qu'à trier la liste du front.
42. **Aucun symbole visible.** Libellé, description, proxyNote, libellés de preuve, notes de données manquantes et mises en garde de concentration du scénario 2 parlent de la catégorie (`ScenarioAnalysis.names`, `hide_symbols`). Le symbole reste dans `method` et `source` (« calculation only, not a selection »). La clé d'évidence est `category:<id>:volatility`, distincte de `asset:<ticker>:volatility` (le FNB peut aussi être un titre de l'idée).
43. **R5 ignore les symboles de l'utilisateur** (opérations, subjectTicker, positions du scénario 0). Dans les tests, Robert détient ZST.TO et XBB.TO, donc ces symboles ne déclenchent pas R5 même dans le texte ; les tests utilisent SPY. Le vérificateur applique la même règle au récit (`verify_narrative(..., universe, held)`), avec `held` lu dans le portefeuille (vide si illisible : on masque davantage, jamais moins).
44. **Pas encore couvert en code :** `read_evidence` renvoie `method` et `source` avec le symbole à l'orchestrateur. Seul le prompt lui interdit de le citer. Durcissement possible : remplacer le symbole par « a fund used only to approximate the category » dans le retour de l'outil.

## Lot C : une seule échelle de risque, côté backend (2026-11-15)

45. **`riskTolerance` et `riskCapacity` obligatoires** dans `validate_investor_profile` ; `riskLevel` accepté (chaîne) puis ignoré, jamais stocké. Les profils déjà dans DynamoDB gardent leur `riskLevel` ; `get_profile` le retire avant de l'envoyer à l'orchestrateur. Un profil ancien sans capacité reste lisible ; l'orchestrateur la demande déjà avant de proposer un mandat. ⚠️ Écart de contrat 0.4.5 : consigné en 0.4.6.
46. **`propose_mandate` refuse `fieldSources.riskCapacity = team_assumption`.** Constat Langfuse du 2026-11-15 : l'orchestrateur a proposé une capacité 2 « hypothèse d'équipe » sans la demander, alors que son prompt l'interdit. Le code l'impose maintenant ; le modèle reçoit l'erreur et corrige son brouillon.
