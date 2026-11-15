# AlphaForge AI : documentation technique

Datathon PolyFinances 2026. Document de synthèse : méthodes et justification, données, explicabilité avec un exemple relié aux traces, validations, limites et améliorations. L'état décrit est celui du dépôt au 15 novembre 2026 (contrat 0.4.1). Pour reproduire le projet : [`README.md`](../README.md).

## 1. Problème et positionnement

**Question traitée.** Un investisseur autonome veut tester une idée (« que se passe-t-il si j'ajoute 15 000 $ de NVDA à mon portefeuille ? ») sans conseiller. Il voit ce qu'il possède, mais rien ne l'aide à mesurer l'effet de l'idée sur l'ensemble de son portefeuille, ni à voir si elle est cohérente avec son objectif, son horizon et sa capacité à encaisser une perte.

**Ce que fait l'outil.** Il cadre l'intention, mesure l'impact sur tout le portefeuille, audite le résultat contre des règles écrites en code et des textes réglementaires cités, puis explique chaque chiffre et chaque verdict. Il ne recommande aucun titre, ne passe aucun ordre et ne promet aucun rendement.

**Positionnement réglementaire.** Banque Nationale Courtage direct exécute des ordres sans conseil. Pour ces comptes, l'OCRI dispense le courtier de l'obligation de convenance et interdit de recommander un titre précis. Sa note d'orientation GN-3200-26-001 (12 mars 2026) élargit les outils d'aide à la décision permis, à condition qu'ils restent factuels et neutres. AlphaForge se place dans cet esprit, sans prétendre être conforme : c'est une simulation pédagogique. Les alternatives sont donc décrites par catégorie d'actifs (« obligations canadiennes court terme »), jamais par titre.

**Les trois personas de l'énoncé** testent trois tensions : Amira (risque élevé, mais pas « tout est acceptable »), Mateo (autre chose que le rendement et le risque : l'ESG), Robert (remettre en question une demande incohérente avec son profil). Voir la section 6.

## 2. Approche agentique, méthodes et justification

### 2.1 Principe directeur

> **Le code calcule, le modèle cadre et cite, le vérificateur contrôle.**

Un modèle de langage ne calcule jamais un chiffre et ne décide jamais d'un verdict. Il fait ce pour quoi il est bon : comprendre une demande dans n'importe quelle langue, poser la bonne question, trouver dans un corpus le passage qui fonde une règle, rédiger. Tout ce qui est chiffré est calculé en code, et chaque résultat est inscrit dans un registre de preuves.

### 2.2 Composants

| Composant | Nature | Rôle | Pourquoi |
|---|---|---|---|
| **Orchestrateur** | Agent LLM (Claude Sonnet 5.5) | Seule voix face à l'utilisateur. Détecte la langue, traduit en anglais, lit profil et portefeuille, pose au plus une étape de questions, propose un mandat, traduit la restitution | Un seul point de contact garde la conversation cohérente. La traduction vers l'anglais rend les agents et la recherche dans la KB prévisibles |
| **Auditeur de convenance** | Agent LLM | Pour chaque verdict, trouve dans la KB le passage qui le fonde (juridiction CA et province) et formule le motif | La recherche de passages est un travail de langage. Il ne décide d'aucun verdict |
| **Rédacteur** | Agent LLM | Écrit quatre sections de restitution en anglais, à partir du registre seulement, avec des emplacements `{EV-nn}` et `{KB-nn}` à la place des chiffres | Séparer la rédaction du calcul rend toute phrase vérifiable |
| **Moteur de calcul** | Code Python (pandas) | Construit les scénarios 0, 1 et 2 et calcule les mesures | Reproductible et vérifiable : un modèle ne calcule pas de tête |
| **Règles R1 à R10** | Code Python | Produit les verdicts, avec seuils configurables | Un verdict de convenance doit être déterministe et auditable |
| **Vérificateur** | Code Python | Contrôle chaque phrase finale : emplacements, chiffres, formules interdites. Masque sans bloquer | Un filet qui ne ralentit pas la réponse |
| **Bedrock Guardrail** | Service AWS | Filtre les entrées et les sorties : ordres, promesses de rendement, conseil personnalisé, renseignements bancaires | Contrôle indépendant des prompts |
| **Knowledge Base** | Service AWS | 13 documents réglementaires, filtrés par juridiction | Les verdicts citent des textes réels, pas la mémoire du modèle |

Le pipeline des étapes de calcul et d'audit est **fixe en code** : l'orchestrateur ne délègue pas librement. Les résultats sont ainsi plus reproductibles. Les droits de chaque composant sur les 13 outils sont une liste fermée vérifiée au chargement (`backend/agents/toolbox.py`).

### 2.3 Déroulement d'une session

**Phase 1, cadrage (synchrone, moins de 30 s).** Message de l'utilisateur, contrôle du Guardrail, orchestrateur (traduction, lecture du profil et du portefeuille, proposition d'un mandat), contrôle de la traduction anglaise, contrôle de la réponse, puis affichage. L'utilisateur confirme le mandat : c'est du code pur, sans modèle (`riskProfile = min(tolérance, capacité)`, perte retenue, avertissements).

**Phase 2, analyse (`POST /runs`).** Aucun calcul avant un mandat confirmé. Le moteur construit les scénarios, les règles donnent les verdicts, et le run est écrit en statut `partial` : le front affiche tout de suite chiffres et verdicts (réponse en 1,7 s lors des essais). La Lambda s'invoque ensuite elle-même, en asynchrone : l'auditeur cherche les citations, le rédacteur écrit, l'orchestrateur traduit, le vérificateur contrôle, le Guardrail filtre la sortie, et le run passe à `done` (environ 50 s au total).

### 2.4 Technologies et justification

| Choix | Justification |
|---|---|
| **Strands Agents SDK** (Python) sur **Amazon Bedrock**, Claude Sonnet 5.5 | Outils typés, sortie structurée, limites de cycles et de tokens fixées par agent. Un seul modèle pour les trois agents : simple à régler et à expliquer |
| **Deux Lambdas** (API légère 256 Mo, 10 s ; agents 2 048 Mo, 180 s) | L'API Gateway coupe à 30 s : le cadrage reste synchrone, l'analyse est faite en deux temps. L'API légère n'embarque pas pandas : elle démarre vite |
| **DynamoDB** (5 tables), **Cognito**, **API Gateway** (JWT), **S3 + CloudFront** | Services gérés, sans serveur, adaptés à une démonstration. L'identité vient du JWT, jamais du corps de la requête |
| **Knowledge Base Bedrock sur S3 Vectors**, embeddings Titan Text Embeddings V2 | S3 Vectors se crée en quelques secondes, sans coût fixe et sans étape manuelle, contrairement à OpenSearch Serverless ou Aurora pgvector |
| **Parquet sur S3**, lu avec pandas dans la Lambda | Jeu léger (environ 600 000 lignes), pas de base à administrer |
| **Terraform** | L'environnement de l'événement est supprimé le 16 novembre : l'infrastructure doit se recréer à partir du dépôt |
| **Langue interne : l'anglais** | Une seule langue pour les prompts, les outils, le corpus et les requêtes de la KB. La langue de l'utilisateur ne sert qu'à l'affichage |
| **Langfuse** (traces, outil de développement) | Relire ce que les agents ont réellement fait pendant la construction. Données fictives seulement. Les agents fonctionnent sans lui |

### 2.5 Décisions écartées

Serveurs MCP tiers (on écrit nos outils, plus fiables et sans dépendance pendant la démo) ; agent ESG dédié (l'ESG passe par les préférences du mandat et l'avis 81-334) ; agent « garde-fou » séparé (fait doublon avec le Guardrail) ; orchestrateur qui délègue librement (moins reproductible) ; vérificateur bloquant avec nouvelle tentative (trop lent en direct) ; « portefeuille optimal » sur rendements passés (contraire à l'énoncé) ; indicateurs ESG inventés pour les actions ; chiffres non sourcés ; univers de 5 000 titres. La liste complète et les raisons : `SOLUTION.md`, section 18.

## 3. Données

### 3.1 Sources

| Source | Données | Traitement et conditions |
|---|---|---|
| Yahoo Finance (`yfinance`) | Prix journaliers (`adj_close`), dividendes, fractionnements, secteurs | Usage personnel et pédagogique : pas de redistribution, aucun CSV de prix dans le dépôt |
| Banque du Canada (API Valet) | USD/CAD, taux directeur (V39079), rendements du gouvernement du Canada 2 et 10 ans, IPC | Conditions de la Banque du Canada |
| FRED | Taux des fonds fédéraux (DFF), rendements du Trésor 2 et 10 ans, IPC américain, chômage | Séries d'agences fédérales |
| Fiches d'émetteurs de FNB | Gabarit prévu (secteurs, pays, principales positions, frais, source et date) pour 15 FNB clés | **Non renseignées à ce jour** (section 8) |
| Corpus réglementaire | 13 documents publics en anglais, version et URL de chacun dans `docs/for_KB/README.md` | Récupérés le 2026-11-14 |

Le jeu de départ fourni par les organisateurs (31 actifs, 5 ans) est facultatif et son propre README juge qu'il ne suffit pas. L'équipe l'a élargi.

### 3.2 Actifs retenus

**241 actifs sur 10 ans** (novembre 2016 à novembre 2026), choisis pour servir les cas d'usage et non pour couvrir le marché : FNB canadiens courants chez les investisseurs autonomes (indices larges, répartition d'actifs, obligations, dividendes, secteurs, or, ESG ; dont XIU, XIC, XSP, ZEQT, XEQT, VFV, XBB, ZAG), constituants de l'indice S&P/TSX 60, grandes capitalisations américaines de tous les secteurs (dont des titres très médiatisés pour tester Robert), FNB américains et trois cryptoactifs (BTC-USD, ETH-USD, SOL-USD). La liste de candidats est dans `data/ingestion/universe.yaml` ; **chaque ticker est validé à l'ingestion** et ceux qui échouent ou qui ont moins d'un an d'historique sont écartés et listés dans le manifeste. Aucun ticker n'est inventé.

La fenêtre de 10 ans apporte deux crises réelles de plus comme tests de résistance : fin 2018 et le krach COVID de 2020, en plus de 2022.

### 3.3 Traitements (détail dans `data/README.md`, section 5)

- **`adj_close`** pour les rendements ; les prix sont déjà ajustés des fractionnements, qui ne sont **jamais réappliqués**. Une nouvelle extraction à une date ultérieure modifie les valeurs passées de `adj_close` : le jeu est donc versionné par date d'extraction (`2026-11-14`).
- **Devises** : conversion en CAD avec le dernier taux USD/CAD connu, devise native aussi affichée. **Le taux ne commence que le 2017-01-03**, donc les mesures en CAD aussi.
- **Calendriers** non alignés (TSX, marchés américains, cryptoactifs 7 jours sur 7) : aucun remplissage dans les fichiers ; les mesures par actif suivent le calendrier natif (annualisation √252, √365 pour la crypto), les portefeuilles l'intersection des jours ouvrés nord-américains.
- **Macro mensuelle** : datée au mois de référence mais publiée plus tard. Une date de publication prudente (le 28 du mois suivant) évite tout biais d'anticipation (règle R10).
- **Anomalie isolée** : un « fractionnement » de 1,021 le 2022-08-22 pour CNQ.TO, le même jour qu'un dividende, vraisemblablement une distribution spéciale : isolé et documenté, jamais appliqué.
- **Historiques courts** (ZEQT lancé en 2022, SOL en 2020) : conservés tels quels, jamais comblés.
- **ESG** : aucun indicateur n'est inventé pour les actions. Seul le secteur est un fait ; « controverses : non vérifié ».

### 3.4 Hypothèses

Fenêtre d'analyse de 5 ans glissants ; perte maximale par défaut selon l'horizon (moins de 3 ans : 10 %, 3 à 8 ans : 20 %, plus de 8 ans : 35 %) ; concentration d'un titre (avertissement à 10 %, échec à 20 %) ; plafonds de crypto (0 % si refusée, 5 % pour un profil de 3 ou moins, 10 % pour 4 et 5) ; bandes de volatilité pour le profil de risque implicite (10, 14, 18 et 25 %). **Ce sont des hypothèses d'équipe, affichées comme telles**, jamais comme des règles officielles. Elles sont dans un fichier de configuration (`backend/agents/rules/rules_config.json`).

### 3.5 Corpus réglementaire

Treize documents : règlement 31-103 et son instruction complémentaire, avis 31-368 (réformes axées sur le client), 21-329 et 21-332 (cryptoactifs), 81-334 (fonds ESG), orientation GN-3200-26-001 et bulletin de l'OCRI sur les comptes sans conseil, textes de l'AMF (Québec), de la FSRA (Ontario) et de la FCAA (Saskatchewan) sur les titres protégés, et deux documents de Banque Nationale Courtage direct. Chacun porte des métadonnées (juridiction, régulateur, sujets, version, URL) qui permettent de filtrer à la recherche : juridiction **CA plus la province de l'utilisateur**. Découpage en passages de 300 tokens avec 20 % de chevauchement, pour des extraits courts dans les citations.

## 4. Moteur de calcul et règles

### 4.1 Scénarios

- **Scénario 0** : le portefeuille actuel.
- **Scénario 1** : l'idée telle que formulée (`add`, `remove` ou `set_weight`, avec un montant ou un poids cible).
- **Scénario 2** : une alternative décrite par catégorie d'actifs, de même montant que l'idée, compatible avec le profil retenu ; le FNB qui la représente pour le calcul est signalé comme approximation.

### 4.2 Mesures

Rendement total, volatilité annualisée, pire baisse, corrélations, poids par titre, secteur, pays et devise, et tests de résistance **dérivés des données** (aucune date choisie à la main) : année 2022, krach COVID 2020 (sommet et creux de SPY), cycle de hausse des taux (selon V39079 ou DFF) et krach crypto (BTC-USD). Les périodes non calculables sont dites telles quelles.

### 4.3 Règles de convenance

| Règle | Contrôle (en code) | Fondement | Nature |
|---|---|---|---|
| R1 | Profil de risque = le plus bas de la tolérance et de la capacité ; l'idée ne doit pas supposer un profil plus élevé | Avis 31-368, partie A | Texte, bandes d'équipe |
| R2 | La pire baisse historique ne dépasse pas la perte maximale acceptée (alerte à 80 %) | 31-103 art. 13.2 et 13.3 | Texte plus hypothèse |
| R3 | L'impact est mesuré sur l'ensemble du portefeuille | Avis 31-368, partie C | Texte |
| R4 | Au moins une alternative raisonnable dès qu'un scénario est en alerte ou en échec | Avis 31-368, partie C | Texte |
| R5 | Aucun titre nommé comme recommandation | Note de l'OCRI GN-3200-26-001 | Texte |
| R6 | Poids d'un titre unique : alerte à 10 %, échec à 20 % | Aucune règle officielle trouvée | Hypothèse d'équipe |
| R7 | Crypto : avertissement sourcé et plafond selon le profil | Avis 21-329 et 21-332 | Texte plus hypothèse |
| R8 | Une affirmation ESG exige une source ; sinon « non vérifié » | Avis 81-334 | Texte |
| R9 | Mentions adaptées à la province (AMF, FSRA, FCAA) | Textes provinciaux | Texte |
| R10 | Aucune donnée macro utilisée avant sa publication | Règle interne de l'énoncé | Interne |

Un verdict de scénario est le pire de ses règles (`fail`, `warn`, `pass`, ou `not_verified` si une mesure manque).

## 5. Explicabilité

### 5.1 Mécanisme

L'explication n'est pas rédigée a posteriori par le modèle : elle est **construite à partir de ce qui s'est réellement exécuté**.

1. **Registre de preuves.** Chaque mesure du moteur devient un élément `EV-nn` (valeur, méthode, fenêtre, devise, source, réserves). Chaque passage de la KB retenu devient un élément `KB-nn` (document, section, extrait, juridiction, version, URL).
2. **Texte par emplacements.** Le rédacteur n'écrit jamais un chiffre : il écrit `{EV-07}` ou `{KB-03}`. Le front remplace chaque emplacement par un badge cliquable qui ouvre la preuve. Un emplacement inconnu n'affiche **jamais** de chiffre.
3. **Vérificateur.** Pour chaque phrase du texte final, dans la langue de l'utilisateur : mêmes emplacements que la version anglaise, emplacements présents au registre, aucun chiffre écrit à la main, aucune formule de recommandation ou de promesse. Une phrase fautive est masquée et signalée.
4. **Champ `explanation`.** Sources (jeu de données, version, date), étapes réellement exécutées (agent, outil, statut, durée), contrôles de gouvernance, hypothèses et limites. Il est construit à partir des événements `tool.call` du run, et il est toujours affiché. Il ne contient jamais le raisonnement interne détaillé d'un modèle.
5. **Journaux** : un événement `agent.usage` par invocation d'agent et un `tool.call` par appel d'outil, avec compteurs et paramètres seulement, jamais le texte des échanges.

### 5.2 Exemple : du verdict aux données et aux traces

Run de Robert (59 ans, risque faible à modéré, Québec, portefeuille de 92 000 $) qui veut ajouter 15 000 $ de NVDA pour un condo dans 3 ans. Essai du 15 novembre 2026, jeu de données `2026-11-14`.

**Conclusion affichée.** Scénario 1 (« l'idée telle quelle ») : **échec**. Raison R1 : *l'idée testée suppose un niveau de risque supérieur au profil retenu.*

**Chaîne de preuves.**

| Élément | Contenu | D'où cela vient |
|---|---|---|
| Profil retenu | 2 sur 5, minimum de la tolérance (3) et de la capacité (2, argent nécessaire à un achat dans 3 ans) | Mandat confirmé par l'utilisateur ; champ `fieldSources` indique « persona » ou « réponse de l'utilisateur » pour chaque valeur |
| Preuve du titre ajouté | Volatilité annualisée de NVDA : **51,9 %** (EV, méthode : écart-type des rendements quotidiens × √252, `adj_close`, fenêtre de 5 ans, 2021-11-15 à 2026-11-13) | Outil du moteur `portfolio_impact`, enregistrée au registre |
| Bande de risque | 51,9 % dépasse 25 % : bande 5. Écart de 3 crans avec le profil : échec (2 crans ou plus) | Règle R1, hypothèse d'équipe (bandes de volatilité) |
| Citation | Instruction complémentaire 31-103CP, page 66 : *« The risk profile for a client should reflect the lower of (a) … »* (KB-01), et avis 31-368, page 5 (KB-02) | Auditeur, outil `search_regulation`, filtre juridiction CA |
| Autres verdicts du même scénario | R2 en alerte (pire baisse de 18,4 % sur 20 % permis ; krach COVID : −21,4 %), R6 en alerte (poids du plus gros titre : 14,0 %) | Règles R2 et R6, preuves EV correspondantes |
| Scénario 2 | Alternative par catégorie : réussite. Le portefeuille actuel (scénario 0) réussit aussi | Moteur de calcul |

**Traces observables du même run** (champ `explanation.steps`, 17 étapes) : `get_portfolio` et `portfolio_impact` (moteur), `check_rules` (règles), dix `search_regulation` (auditeur, une par règle), puis les invocations du rédacteur et de l'orchestrateur (traduction). Contrôle de fin de run : 31 emplacements sur 31 résolus, aucune phrase masquée, aucun chiffre écrit à la main.

**Ce que l'utilisateur peut vérifier.** En cliquant sur chaque badge, il voit la valeur, la formule, la fenêtre, la devise et la source. Le texte qui explique le verdict ne contient aucun chiffre qui ne soit pas dans le registre.

### 5.3 Ce que l'explication ne fait pas

Elle n'expose pas le raisonnement interne détaillé des modèles et ne prétend pas justifier ce qui ne s'est pas passé. Quand une donnée manque (historique court, période non calculable, composition de FNB absente), elle le dit dans les limites du run.

## 6. Adaptation aux personas

Trois situations d'investisseurs, un même moteur et un même jeu de règles ; seuls changent le mandat et ses sources.

| Persona | Profil | Idée testée | Ce que l'outil fait |
|---|---|---|---|
| **Robert** | Faible à modéré, 3 à 5 ans, Québec, 92 000 $ | Ajouter 15 000 $ de NVDA pour un condo dans 3 ans | **Remet en question** la demande : l'idée échoue (R1), la perte maximale est proche de la limite (R2), la concentration monte (R6). Il propose une alternative par catégorie qui réussit. Il n'acquiesce pas automatiquement |
| **Mateo** | Modéré, 8 à 12 ans, préférence ESG, Québec, 92 000 $ | Ajouter 5 000 $ de SHOP.TO | **Intègre autre chose que le rendement et le risque** : la préférence ESG déclenche R8, qui refuse d'affirmer quoi que ce soit sans méthodologie publiée (« non vérifié »). L'idée échoue sur R1 (volatilité de SHOP.TO : 64,4 %, bande 5, contre un profil de 3) |
| **Amira** | Élevé (tolérance 5, capacité 4), 15 ans et plus, Ontario, 79 000 $ très canadien | Basculer 25 000 $ de XIC.TO vers VFV.TO (mode B, rééquilibrage) | **Mesure sans acquiescer** : volatilité de 15,8 % à 16,0 % et pire baisse de −26,1 % à −26,6 %, donc un gain de diversification faible, et l'outil le dit. Son exposition crypto (7,6 %) reste sous le plafond de 10 % de son profil, mais R7 maintient l'avertissement sourcé sur la garde et les plateformes (3 citations de la KB). R4 signale qu'aucune alternative par catégorie n'a pu être associée (`ALTERNATIVE_MISSING`) : « risque élevé » ne veut pas dire « tout est acceptable » |

Le contraste de province est appliqué par R9 : la même demande n'affiche pas les mêmes mentions en Ontario et au Québec, alors que les règles de convenance restent identiques. Les curseurs « et si » (horizon, perte maximale) créent une nouvelle version du mandat et relancent l'analyse : avec un horizon de 10 ans, la perte retenue passe de 20 % à 35 %, R2 repasse en réussite et un avertissement signale l'écart avec « condo dans 3 ans ». Le verdict global de l'idée reste en échec, car R1 échoue indépendamment de l'horizon.

## 7. Validations

### 7.1 Tests automatiques (sans AWS)

274 tests pour `common` et les agents, 106 pour la Lambda API, 13 pour l'ingestion des données, 13 pour les composants du front. Ils couvrent les calculs, chaque règle, le vérificateur, les outils, les droits, la validation des mandats, les routes, le Guardrail simulé et la traduction avec ses emplacements. Les agents sont testés avec un faux modèle scripté.

### 7.2 Banc de fumée sur les vrais services

`backend/agents/scripts/smoke.py` : le Guardrail (cas à bloquer et cas à laisser passer, en anglais et en français), la Knowledge Base (pertinence des passages et filtre de juridiction), un vrai tour de l'orchestrateur en français et la traduction avec conservation des emplacements. Résultat du 15 novembre : tout passe sauf un cas connu du Guardrail (section 8).

### 7.3 Essai de bout en bout du 15 novembre 2026 (API réelle, Lambdas déployées)

| Parcours | Résultat |
|---|---|
| Robert : cadrage, mandat, run | Scénarios 0, 1, 2 : réussite, échec, réussite. Run terminé en 57 s, 4 sections, 33 emplacements sur 33, 14 citations de la KB, 39 preuves chiffrées. R1 cite la volatilité de NVDA (51,9 %) |
| Robert : curseur d'horizon à 10 ans | Nouvelle version du mandat, run terminé en 48 s, avertissement `HORIZON_EXCEEDS_PROJECT` |
| Mateo : cadrage, mandat, run | Scénarios 0, 1, 2 : avertissement, échec, avertissement (R8 : ESG non vérifié ; R1 : SHOP.TO à 64,4 % de volatilité contre un profil de 3). Run terminé en 57 s, 4 sections, 29 emplacements sur 29, 13 citations de la KB |
| Amira : cadrage, mandat, run (mode B) | Mandat valide (retrait puis ajout de 25 000 $ avec `amount`). Scénarios 0 et 1 : avertissement (R7). Run terminé en 47 s, 4 sections, 31 emplacements sur 31, 18 citations de la KB |
| Messages hors cadre (« Achète 100 actions de NVDA pour moi », « Garantis-moi 20 % », « Dis-moi quelle action acheter ») | Refus 422 `GUARDRAIL_BLOCKED` dans les trois cas, rien n'entre dans l'historique |

### 7.4 Défauts trouvés par ces essais, et corrigés

Les essais ont révélé des écarts avec la propre règle du projet (« explications fidèles aux données et aux actions observables »). Ils ont été corrigés et chacun a un test.

- **Faux positifs du Guardrail** (version 2) sur des phrases de simulation avec un ticker : exemples sans ticker et tier STANDARD (version 3). Le filtre de sortie a aussi retiré deux réponses de l'orchestrateur qui approuvaient l'idée de l'utilisateur (« Bonne idée ») ou lui proposaient un style d'investissement selon son profil : deux règles de neutralité ajoutées à son prompt.
- **Opération de mandat mal formée** : l'orchestrateur avait écrit `remove` avec un `weight`, que la validation laissait passer ; le moteur retirait alors des positions entières. Les opérations sont désormais validées selon le contrat (`add` et `remove` portent un montant, `set_weight` un poids cible).
- **Composition des FNB** : une fiche vide était traitée comme une composition disponible, et le libellé de la preuve promettait une décomposition des FNB qui n'existe pas. Une fiche vide est désormais déclarée « composition non disponible » (réserve affichée dans les preuves et les verdicts), et le libellé ne promet plus rien.
- **Preuve de R1** : l'échec de R1 vient de la volatilité du titre ajouté, mais la preuve citée était celle du portefeuille. R1 cite désormais d'abord la volatilité du titre qui fonde le verdict.

### 7.5 Ce qui n'est pas validé

- **La pertinence des citations** : les passages de la KB sont réels et filtrés par juridiction, mais aucun jeu étiqueté n'en mesure la pertinence. Un passage cité pour une règle peut ne la soutenir que de loin (c'est le cas de l'avis 31-368 cité pour R2, qui parle de la cohérence du profil de risque plus que de la perte maximale).
- **La stabilité des modèles** : le comportement de l'orchestrateur varie d'un appel à l'autre. Les règles ajoutées à son prompt ont tenu sur les essais du 15 novembre, mais sans garantie.
- **La qualité de la traduction** sur un jeu de phrases étiqueté : seuls les emplacements sont contrôlés automatiquement.

## 8. Limites

- **Hypothèses d'équipe** (section 3.4) : aucune n'est une règle officielle. Elles sont affichées comme telles.
- **Biais du survivant** : l'univers a été choisi en 2026, et la fenêtre de 10 ans l'amplifie. Les sociétés disparues ou sorties des indices n'y figurent pas.
- **Le passé ne prédit pas l'avenir.** Chaque restitution le rappelle.
- **Composition des FNB non renseignée.** Les 15 fiches clés sont des gabarits vides. Un FNB compte comme une position unique, et la concentration d'un titre détenu *à travers* un FNB n'est pas mesurée. L'outil l'indique, mais cela affaiblit R6 et les mesures de technologie « par transparence ».
- **Fenêtre de 5 ans pour R2.** Le krach COVID de 2020 est calculé et affiché comme test de résistance, mais, hors de la fenêtre de 5 ans, il n'entre pas dans le verdict de R2. La question d'une fenêtre de 10 ans est ouverte : elle ferait entrer le krach COVID, avec des conséquences à arbitrer sur les verdicts des personas.
- **Conversion en CAD** à partir du 2017-01-03 seulement.
- **Guardrail d'entrée.** Le classificateur de sujets est sémantique et refuse encore certaines formulations légitimes : celles qui disent « pour mon portefeuille » ou « sa place dans mon portefeuille », et les tournures à l'impératif (« Je veux déplacer… »). Les formulations « Et si… » et celles qui parlent de risque, de volatilité ou de ce que change un ajout passent. L'état, les mesures et les pistes sont dans `docs/guardrail-etat-et-pistes.md`. Le blocage est final et la demande n'est jamais reformulée pour le contourner.
- **Mode B (rééquilibrage) sans alternative.** Le moteur ne construit pas de scénario 2 pour un rééquilibrage. R4 affiche maintenant `not_verified` (`ALTERNATIVE_NOT_APPLICABLE`) au lieu d'un échec : elle ne prétend ni réussite ni échec. Une alternative par catégorie pour ce mode reste à concevoir.
- **Incertitude d'échantillonnage.** Volatilité et pire baisse portent une fourchette à 90 % par bootstrap par blocs (graine fixe). Elle mesure la sensibilité à la période observée, pas l'avenir, et suppose que les blocs de 21 jours passés représentent les blocs possibles.
- **Concentration sectorielle (R6).** Avertissement au-delà de 40 % pour un secteur GICS (hypothèse d'équipe). Sans fiches de FNB renseignées, seules les actions directes comptent.
- **Cadrage d'Amira : l'utilisateur doit nommer les fonds.** Pour ne pas proposer de produit adapté au profil, l'orchestrateur ne liste jamais de fonds candidats. « Un fonds indiciel américain large » ne suffit donc pas pour écrire les opérations ; « de XIC.TO vers VFV.TO » suffit (elle détient déjà VFV.TO). Compromis assumé entre neutralité et fluidité du dialogue.
- **Latence du cadrage** : de 6 à 17 s selon les essais, pour une limite de 30 s côté API Gateway.
- **Environnement temporaire** : le compte AWS de l'événement est supprimé le 16 novembre 2026 en fin de journée. Le code, l'infrastructure (Terraform) et les procédures de reproduction restent dans le dépôt ; les données de marché se régénèrent depuis les sources publiques.
- **Données hors d'une région** : le tier STANDARD du Guardrail évalue dans trois régions américaines. Données fictives seulement.

## 9. Améliorations envisagées

1. **Renseigner les fiches des 15 FNB** (secteurs, pays, principales positions, frais, avec URL et date) pour mesurer la concentration à travers les fonds.
2. **Mesurer la pertinence des citations** sur un jeu étiqueté, et restreindre les sujets de recherche par règle.
3. **Étendre la fenêtre d'analyse de R2 à 10 ans**, ou faire comparer R2 à la pire baisse entre la fenêtre et les tests de résistance, après avoir arbitré l'effet sur les verdicts.
4. **Fiabiliser le filtre d'entrée** : itérer sur la définition du sujet « Personalized investment recommendation », ou le remplacer par un classificateur d'intention à seuils réglables (piste étudiée dans `docs/jev-classifieur-intention.md`).
5. **Rendre le cadrage plus prévisible** : valider le brouillon de mandat par un jeu de cas par persona, et relancer l'orchestrateur lorsqu'un filtre de sortie retire sa réponse, au lieu d'afficher un refus.
6. **Exposer l'onglet de traçabilité** de l'explication dans le front (étapes, durées, outils), aujourd'hui affichée dans un panneau.
7. **Mode « diagnostic d'un titre »** (mode C) plus complet, et alternatives sourcées pour plus de catégories d'actifs.
