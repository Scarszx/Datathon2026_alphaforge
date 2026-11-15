# Couverture des exigences du Datathon

État au 15 novembre 2026, vérifié contre le dépôt (`main` + branche `david`). Sources des exigences : l'énoncé officiel, la présentation aux participants et la liste « Top must-know ».

## 1. Exigences et état

| # | Exigence | État | Où le vérifier |
|---|---|---|---|
| 1 | **AWS réel et démontrable** (condition d'admissibilité, 15 %) | Couverte | Terraform : API Gateway, deux Lambdas, DynamoDB, S3, Cognito, Bedrock (agents), Bedrock Knowledge Bases, Bedrock Guardrails, CloudWatch (`infra/terraform/`). Chaque service a un rôle dans le flux (`docs/documentation-technique.md`, section 2) |
| 2 | Solution agentique **auto-explicative** | Couverte | Registre de preuves EV-nn / KB-nn, champ `explanation` construit à partir des appels d'outils réels, vérificateur de phrases |
| 3 | Test **Amira** (risque élevé ≠ tout permis) | Couverte, renforcée | R6 (titre unique) et **nouvelle alerte de concentration sectorielle** ; R7 plafonne la crypto |
| 4 | Test **Mateo** (critères non financiers) | Couverte | R8 (ESG sourcé), préférences du mandat, **choix d'industries** à l'inscription et au profil |
| 5 | Test **Robert** (contester une demande hors profil) | Couverte | R1, R2, R6 : l'idée échoue, une alternative par catégorie est proposée |
| 6 | Adaptation sur au moins **deux situations contrastées** | Couverte | Robert (mode A) contre Amira (mode B), contraste de province (R9), curseurs « et si » |
| 7 | **Incertitudes montrées** | Était partielle, **corrigée** | Nouvelles fourchettes à 90 % de la volatilité et de la pire baisse (voir section 2) |
| 8 | **Faits, hypothèses, scénarios** distingués | Couverte | `kind` = metric / etf_fact / assumption ; seuils marqués « hypothèse d'équipe » |
| 9 | Pas d'**anticipation** (look-ahead) | Couverte | R10 : une valeur macro n'est utilisée qu'après sa date de publication |
| 10 | **Données documentées** (source, date, traitement, limites, licence) | Couverte | `data/README.md`, section 4 (conditions d'utilisation) et section 5 (limites) |
| 11 | **Simulation seulement**, pas de conseil personnalisé | Couverte | Guardrails en entrée et en sortie, R5 (aucun titre recommandé), mentions R9 |
| 12 | Livrable : prototype + dépôt + README | Couverte | `README.md`, `frontend/`, `backend/`, `infra/` |
| 13 | Livrable : documentation technique | Couverte (à relire) | `docs/documentation-technique.md` |
| 14 | Livrable : one-pager | Couverte (à relire) | `docs/one-pager.md` |
| 15 | Livrable : **vidéo d'environ 5 minutes** | **Non couverte** | À enregistrer par l'équipe (voir section 3) |

## 2. Ce qui a été ajouté dans cette branche

1. **Fourchettes d'incertitude (exigence 7).** Pour chaque scénario, la volatilité et la pire baisse s'accompagnent d'une fourchette 5e à 95e percentile, calculée par bootstrap par blocs mobiles (500 rééchantillonnages, blocs de 21 jours, graine fixe donc reproductible). Elle montre à quel point le chiffre dépend de la période observée. Elle ne prédit pas l'avenir, et la méthode le dit. Les deux valeurs sont des éléments du registre (`volatilityRange`, `maxDrawdownRange`) : le rédacteur les cite par emplacement dans la rubrique « limites », et le vérificateur les contrôle comme les autres. Un historique de moins de 42 jours ne produit pas de fourchette.
2. **Concentration sectorielle (test d'Amira).** R6 avertit (WARN, jamais FAIL) quand un secteur GICS dépasse 40 % du portefeuille, fonds documentés inclus (par transparence). Seuil : hypothèse d'équipe (`sectorWarnPct` dans `rules_config.json`). Les catégories de fonds sans composition ne comptent pas comme des secteurs. Le titre unique garde la priorité sur le secteur.
3. **R4 pour le mode rééquilibrage.** Le moteur ne construit pas d'alternative pour un rééquilibrage. R4 affichait un échec trompeur (`ALTERNATIVE_MISSING`). Elle affiche maintenant `not_verified` / `ALTERNATIVE_NOT_APPLICABLE` : ni réussite ni échec affirmés.
4. **Industries d'intérêt** (choix multiple, 21 catégories) à l'inscription et dans le profil, enregistrées dans `preferences`.
5. **Quatre classes d'actifs ajoutées à l'univers** (voir section 4), dans `data/ingestion/universe.yaml` seulement.

Aucun changement de route ni de schéma. Les nouveaux `reasonCode` (`SECTOR_CONCENTRATION_ELEVATED`, `ALTERNATIVE_NOT_APPLICABLE`) et les nouvelles clés de mesure sont des chaînes libres dans le contrat v0.4.x. L'équipe devrait quand même les consigner dans le contrat à la prochaine proposition de changement.

## 3. Ce qui n'a pas pu être fait, et pourquoi

| Élément | Raison | Quoi faire |
|---|---|---|
| Vidéo de 5 minutes | Je ne peux ni enregistrer ni présenter | Suivre le scénario vedette de `SOLUTION.md` section 6, puis le contraste avec Amira |
| **Déployer** les nouveautés (Lambdas, jeu de données dans S3) | `AGENTS.md` interdit `terraform apply` et toute modification de ressource AWS sans demande explicite | Après relecture : reconstruire la Lambda agents, relancer l'ingestion, renvoyer le jeu dans S3 |
| Rendre les nouvelles classes d'actifs **visibles dans l'application** | Elles n'existent dans l'application qu'après la reconstruction du jeu de données (`python -m data.ingestion.build_dataset`) et son envoi dans S3 | Même étape que ci-dessus |
| **Fiches des 15 FNB** (secteurs, pays, positions) | Les valeurs doivent venir des fiches officielles des émetteurs, avec URL et date. Je ne les recopie pas de mémoire : une valeur inventée contredirait la règle « aucune valeur inventée ». Tant que les fiches sont vides, la concentration à travers les FNB n'est pas mesurée, et la nouvelle alerte sectorielle ne voit que les actions directes | Relevé manuel dans `data/ingestion/etf_enriched.source.json` |
| Fiabiliser le Guardrail d'entrée | Limite connue du classificateur de Bedrock (`docs/guardrail-etat-et-pistes.md`) ; chaque piste change le compromis entre faux refus et violations passées | Décision d'équipe |
| Étendre R2 à une fenêtre de 10 ans | Change les verdicts des personas : à arbitrer par l'équipe (documentation technique, section 8) | Décision d'équipe |
| Démontrer AWS **après le 16 novembre** | Le compte AWS de l'événement est supprimé le 16 novembre en fin de journée | Enregistrer la vidéo et des captures de la console AWS avant |
| Choisir le modèle le plus économique pour écrire le code | Je n'ai pas accès au choix du modèle dans cet environnement | — |

## 4. Autres classes d'actifs : suggestions

L'univers couvre déjà : actions canadiennes et américaines, FNB larges (Canada, États-Unis, international, marchés émergents), FNB d'allocation, obligations (agrégées, court terme, haut rendement), dividendes, secteurs, FPI, or, ESG, encaisse, thématiques et cryptoactifs.

**Ajoutées au fichier d'univers (non déployées).** Chaque ticker a été vérifié sur Yahoo Finance le 15 novembre.

| Classe | Tickers | Pourquoi |
|---|---|---|
| Matières premières diversifiées | DBC, PDBC, SLV | L'or était la seule matière première. Diversifie l'inflation et les cycles |
| Obligations à rendement réel et de sociétés | XRB.TO, ZCS.TO, XCB.TO | Le test de 2022 (actions et obligations en baisse ensemble) montre l'intérêt de l'inflation comme facteur |
| Actions privilégiées canadiennes | CPD.TO, ZPR.TO | Revenu courant, classe fréquente chez les investisseurs autonomes canadiens |
| Infrastructures mondiales | IGF | Actifs réels, flux stables, utile pour Mateo et Robert |

**Pistes non réalisées, avec les contraintes :**
- **Alternatives par catégorie pour ces classes** : ajouter des entrées dans `alternativeCategories` (`rules_config.json`). C'est un choix de produit : quelle catégorie pour quel profil. À décider avant de coder.
- **Placements garantis (CPG) et comptes d'épargne** : pas de données publiques de prix. Seule l'approximation par FNB d'encaisse (CASH.TO, ZMMK.TO) est possible, déjà dans l'univers.
- **Obligations d'épargne et titres du gouvernement** : taux publiés par la Banque du Canada, mais pas de série de prix. Ils peuvent servir de référence sans risque dans le calcul de rendement ajusté, ce qui demande un nouveau calcul (non ajouté).
- **Dérivés, marge, levier** : l'énoncé dit qu'ils ne sont pas requis. Je les déconseille.
- **Immobilier direct, capital-investissement** : pas de données publiques journalières, donc hors périmètre vérifiable.
