# SOLUTION — AlphaForge AI (Datathon PolyFinances 2026)

> **But de ce document.** Ce fichier décrit la solution retenue par l'équipe le 2026-11-14. Il donne à un agent ou à un coéquipier, dans une autre session, tout le contexte pour poursuivre dans la même direction sans refaire les débats.
>
> **Version visuelle :** https://claude.ai/artifact/VN31eBrntmtUUbA1vzauHd (page privée, à partager depuis son menu).
>
> **Règles de lecture pour un agent :**
> - Le contrat d'API et d'architecture du projet reste `contract/knowledge-graph.yaml` (voir `AGENTS.md`). **Le contrat v0.4.0 a été aligné sur ce document** : agents, modules, routes de mandats et de runs, table `Analyses`, schémas, KB, Guardrails, règles R1-R10. Pour les noms de champs, les routes et les schémas, **le contrat fait foi** (camelCase). Les exemples JSON de la section 8 ci-dessous sont illustratifs. En cas d'écart, signale-le à l'équipe : ne modifie pas le contrat seul et n'invente pas de route ni de schéma.
> - Les décisions de la section 18 (« Ce qu'on a écarté ») sont prises. Ne les rouvre pas sans demande explicite.
> - Tout ce qui est marqué **hypothèse d'équipe** est un choix de l'équipe, pas une règle officielle. L'interface doit le présenter comme tel.
> - **Décision technique ferme : les agents sont construits avec le SDK Strands Agents (Python) et les modèles d'Amazon Bedrock.** Pas d'autre framework d'agents (LangChain, LlamaIndex…), pas d'appel direct à un autre fournisseur de modèles.
> - **Décision ferme : région AWS `us-east-1` et Claude Sonnet 5.5 pour les 3 agents** (accès testé par l'équipe). Le contrat v0.4.0 est **validé par l'équipe**.
> - **Décision ferme : tout le système interne est en anglais** (prompts, descriptions d'outils, échanges entre agents, requêtes et corpus de la KB). Seuls les textes affichés à l'utilisateur sont dans sa langue. L'orchestrateur traduit à l'entrée et à la sortie. Voir section 7.0.
> - Les commandes AWS et Terraform suivent `AGENTS.md` : `source scripts/aws-env.sh && ...`, le compte doit être `058264316309`, et aucun `terraform apply` ni aucune création de ressource sans demande explicite.

---

## 1. Contexte du Datathon

- **Événement :** Datathon PolyFinances 2026, « AlphaForge AI » (Banque Nationale × AWS × PolyFinances).
- **Défi :** une solution **agentique auto-explicative** qui exploite des données financières publiques pour éclairer une décision d'investissement selon différents profils. **Simulation seulement** : aucune transaction réelle, aucun conseil financier personnalisé, aucune donnée bancaire réelle.
- **Personas de l'énoncé** (chacun teste une tension) :
  - **Amira**, 26 ans, risque élevé, 15 ans et plus, intéressée par l'IA et la crypto. *Test : « risque élevé » ne veut pas dire « tout est acceptable » ; la diversification doit rester cohérente.*
  - **Mateo**, 41 ans, risque modéré, 8 à 12 ans, préférences ESG. *Test : intégrer autre chose que le rendement et le risque.*
  - **Robert**, 59 ans, risque faible à modéré, 3 à 5 ans, retraite proche, tenté par un titre très médiatisé. *Test : remettre en question une demande incohérente avec le profil, sans acquiescer automatiquement.*
- **Grille du jury** (présentation aux participants) : Solution 20 %, Agentique et explicabilité 20 %, Données (rigueur, validation, visualisation) 20 %, Intégration AWS 15 %, Pitch 15 %, UX/UI 10 %.
- **AWS est une condition d'admissibilité** : AWS doit contribuer réellement et de façon démontrable au fonctionnement de la solution. Sinon, le projet n'est pas évalué en finale.
- **Livrables :**
  - un prototype démontrable, avec un dépôt de code et un README (dépendances, sources, configuration, démarrage) ;
  - une vidéo d'environ 5 minutes ;
  - une documentation technique : méthodes, sources, traitements, hypothèses, mécanisme d'explicabilité avec un exemple relié aux traces, validations, limites ;
  - un one pager.
- **Cadre responsable exigé :**
  - distinguer faits, hypothèses et scénarios ;
  - montrer les incertitudes ;
  - des explications synthétiques, vérifiables et fidèles aux sources et aux actions observables ;
  - ne pas inventer de justification après coup ;
  - ne pas prédire les rendements futurs à partir du passé.
- **Compte AWS de l'événement :** activé le samedi 14 novembre, **supprimé le lundi 16 novembre en fin de journée** avec toutes ses données. Avant l'expiration, il faut sauvegarder le code sur GitHub et les données et notes en local.
- **Documents sources lus pour construire la solution :** `mes_docs_perso/`
  - l'énoncé FR et EN (PDF) ;
  - la présentation aux participants ;
  - l'atelier « Comprendre l'investisseur avant de bâtir la solution » ;
  - l'aide-mémoire AWS ;
  - le jeu de départ `Datathon2026/alphaforge_starter/` ;
  - `idees-telechargement-donnees-bulk.md` ;
  - `strands-sdk-agents-retour-experience.md`.

## 2. Proposition de valeur

**Phrase de pitch :**
> « Sur une plateforme de courtage autonome, l'investisseur voit ce qu'il possède, mais il est seul au moment de tester une idée. AlphaForge lui ouvre une session de simulation : on clarifie son objectif, on mesure l'impact réel sur son portefeuille, et un auditeur ancré dans les textes de l'ACVM et de l'OCRI lui signale quand l'idée met son objectif en danger. Chaque chiffre et chaque règle citée renvoient à leur source. »

**Pourquoi c'est la bonne direction :**
- **Ça reprend la méthode de l'atelier.**
  - Diapositive 10 : objectif, horizon, risque (la *volonté* de subir des fluctuations n'est pas la *capacité* d'en vivre les conséquences), contraintes, préférences.
  - Diapositive 13 : « Mon portefeuille semble très canadien, que m'apporterait XSP ? ». Le déroulé est observer, comprendre, comparer, expliquer. « Une décision commence par : qu'est-ce que j'essaie d'améliorer ? »
  - Diapositive 14 : « Le portefeuille montre ce que l'investisseur possède. Il ne suffit pas à expliquer ce dont il a besoin. »
- **Ça répond aux 3 tests des personas** avec une seule architecture.
- **Ça transforme une contrainte réglementaire en argument** : un outil d'aide à la décision neutre est permis pour un courtier sans conseil comme BNCD (voir section 3).

## 3. Positionnement réglementaire (important pour le jury Banque Nationale)

- **BNCD (Banque Nationale Courtage direct) fait de l'exécution d'ordres sans conseil.** Sa propre page et son document « Information sur la relation avec les clients » le disent. **Il ne faut donc jamais parler de « règles de convenance BNCD ».**
- Pour les comptes sans conseil, l'OCRI (CIRO) **dispense** le courtier de l'obligation de convenance et **interdit de recommander l'achat, la vente ou la conservation d'un titre précis**.
- La **note d'orientation de l'OCRI GN-3200-26-001** (12 mars 2026, bulletin 26-0059) remplace l'ancienne GN-3400-21-003. Elle **élargit les outils d'aide à la décision permis**, à condition qu'ils restent factuels et neutres : questionnaires remplis par le client, filtres sur des critères objectifs, alertes dans des paramètres fixés par le client, répartitions types **sans titre nommé**.
- **Notre outil se positionne comme un outil d'aide à la décision**, inspiré de cette note. Il ne prétend pas être conforme : c'est une simulation pédagogique.
- **Ce que l'outil fait :**
  - simuler l'impact d'une idée sur un portefeuille fictif ou de persona ;
  - collecter les entrées de l'utilisateur (objectif, horizon, tolérance, capacité de perte, préférences) ;
  - comparer des scénarios ;
  - citer la règle et le document qui motivent chaque alerte ;
  - dire ce qu'il ne sait pas.
- **Ce que l'outil ne fait pas :**
  - recommander un titre précis ;
  - passer un ordre ;
  - promettre un rendement ou prédire l'avenir ;
  - se présenter comme « conseiller financier » ou « planificateur financier ». Ces titres sont protégés au Québec (AMF/IQPF), en Ontario (FSRA, depuis 2022) et en Saskatchewan (FCAA).
- **Les alternatives proposées sont formulées par catégorie d'actifs** : « exposition large aux actions américaines », « obligations court terme ». Jamais « achetez QQQ ». Dans le moteur, une catégorie peut être *représentée* par un FNB de l'univers pour le calcul, mais le texte affiché parle de la catégorie et indique que le FNB sert d'approximation de calcul.

## 4. Lexique (termes utilisés partout)

| Terme | Définition dans notre solution |
|---|---|
| **Session** | Un rendez-vous d'analyse. Elle a un `sessionId` (UUID) dans DynamoDB et garde le portefeuille, la conversation, les versions du mandat et les résultats. |
| **Portefeuille** | Les positions (ticker, montant ou quantité, devise) d'un utilisateur fictif ou d'un persona. Uniquement des actifs de l'univers (section 10). |
| **Intention / idée testée** | Ce que l'utilisateur veut évaluer, en langage libre (« ajouter 15 000 $ de NVDA »), puis traduit en opérations simulées. |
| **Mandat** | Le contrat de l'analyse, **confirmé par l'utilisateur** : objectif, horizon, tolérance, capacité de perte, profil retenu, contraintes, préférences, province, idée testée. Il est versionné (v1, v2…). Rien ne se calcule avant sa confirmation. |
| **Tolérance au risque** | Ce que la personne *accepte* de subir (attitude subjective). |
| **Capacité de perte** | Ce que la personne *peut* financièrement encaisser (situation objective : échéance, besoin de l'argent, autres actifs). |
| **Profil retenu** | **La plus basse des deux** (avis ACVM/OCRI 31-368). |
| **Scénarios 0 / 1 / 2** | **0** : portefeuille actuel. **1** : idée appliquée telle quelle. **2** : alternative par catégorie, qui respecte le mandat. |
| **Test de résistance** | Rejouer un portefeuille sur une période difficile réelle : 2022, cycle de hausse des taux, krach crypto. |
| **Registre de preuves** | Le journal de la session. Chaque calcul (`EV-xx`) et chaque passage réglementaire cité (`KB-xx`) y est inscrit avec sa source, sa période, sa devise et ses limites. |
| **Verdict** | `PASS` / `WARN` / `FAIL`, par règle et par scénario. |
| **Hypothèse d'équipe** | Un seuil choisi par nous. Il est configurable et toujours affiché comme hypothèse. |
| **Non vérifié** | Statut d'une affirmation qu'aucune source du registre ne soutient. L'outil le dit au lieu de deviner. |

## 5. Flux d'une session

```
1 INTENTION      utilisateur : portefeuille (persona ou fictif) + province + idée en texte libre (dans SA langue)
      │          Orchestrateur : détecte userLanguage, TRADUIT la demande en anglais (Guardrails filtre l'entrée)
      │          ── à partir d'ici, tout est en anglais en interne ──
2 CADRAGE        Orchestrateur (LLM) : pré-remplit depuis le profil, pose UNE seule étape de questions
      │          (boutons de réponse rapide), propose le mandat → l'utilisateur confirme (mandat v1)
3 CALCUL         Moteur Python : scénarios 0/1/2, volatilité, pire baisse, tests de résistance,
      │          concentration (avec composition des FNB), devises → registre EV-xx
      │          + règles déterministes R1..R10 → pastilles PASS/WARN/FAIL
      │          ⇒ AFFICHÉ IMMÉDIATEMENT dans le panneau de simulation
4 AUDIT          Auditeur (LLM + KB) : pour chaque verdict, cherche le passage qui le fonde,
      │          requêtes en anglais, filtre juridiction ∈ {CA, province} → citations KB-xx (affichées au fil de l'eau)
5 RESTITUTION    Rédacteur (LLM) : 4 rubriques EN ANGLAIS, avec des emplacements {EV-xx}/{KB-xx} au lieu de chiffres
                 → Orchestrateur : traduit dans userLanguage (emplacements conservés, extraits KB non traduits)
                 → Vérificateur (code) : contrôle chaque phrase du texte final, sans bloquer ; affichage en continu
```

**Boucles :**
- **« D'où vient ce chiffre ? »** : un clic sur un badge, ou la question posée à l'orchestrateur, lit le registre. Il n'y a aucun nouveau calcul.
- **« Et si… »** avec les curseurs du mandat (horizon, perte acceptée…) : on **ne repasse pas par l'orchestrateur**. Un contrôle de cohérence en code tourne d'abord, puis le mandat v2 est enregistré, puis les étapes 3 à 5 sont relancées. L'explication mentionne « vous avez modifié X ».
- **« Et si… » en texte libre** : l'orchestrateur traduit la demande en mandat v2 et le fait confirmer.

**Affichage progressif (décidé) :** les étapes 3 et les règles prennent moins d'une seconde hors démarrage à froid. On affiche tout de suite les 3 scénarios et les pastilles. Les citations de l'étape 4, puis le texte de l'étape 5, arrivent ensuite en continu. L'application paraît instantanée et on voit les agents compléter le travail.

**États de session (champ `stage` dans DynamoDB) :** `CADRAGE` → `MANDAT_PROPOSE` → `ANALYSE` → `RESULTAT` (ou `RESULTAT_PARTIEL` si le vérificateur a masqué des phrases). Depuis `RESULTAT`, un « et si » mène à `MANDAT_PROPOSE` (texte libre) ou directement à `ANALYSE` (curseurs). Il n'y a pas de calcul avant `ANALYSE`.

## 6. Modes d'usage

Tous les modes passent par le même flux. Seuls changent les calculs lancés et les règles déclenchées.

| Mode | Exemple | Calculs principaux | Règles clés | Persona de démo |
|---|---|---|---|---|
| **A. Ajouter un actif** | « Que se passe-t-il si j'ajoute 15 000 $ de NVDA ? » | scénarios 0/1/2, pire baisse 2022, concentration | R1, R2, R3, R4, R5, R6 | Robert : FAIL sur la demande, alternative en PASS |
| **B. Rééquilibrer / tester une allocation** | « Mon portefeuille est trop canadien, et si je basculais vers les actions américaines ? » | exposition par pays, secteur et devise, composition des FNB, corrélations | R3, R6, R7 | Amira : gain de diversification, mais nouvelle concentration tech signalée |
| **C. Diagnostic d'un titre** | « Parle-moi de SHOP.TO et de sa place dans mon portefeuille » | volatilité, pire baisse, sensibilité aux taux, corrélation avec les positions | R5, R8, R10 | Mateo (préférence ESG dans le mandat) |
| **Et si…** | « Et si mon horizon était de 10 ans ? » | relance des étapes 3 à 5 | toutes | n'importe lequel |
| **Hors cadre** | « Achète pour moi », « Garantis-moi 20 % » | aucun | Guardrails | refus expliqué et reformulation (« voulez-vous simuler cet ajout ? ») ; le message refusé n'entre pas dans l'historique |

**Scénario vedette de la vidéo** : un utilisateur du Québec avec un portefeuille de 93 000 $ (XIU.TO 30 k, RY.TO 8 k, TD.TO 10 k, XBB.TO 30 k, ZST.TO 15 k ; RY à 8 k pour que R6 reste sous 10 % dès l'état actuel) veut ajouter 15 000 $ de NVDA pour un condo dans 3 ans. Le déroulé : une question de cadrage, le mandat (capacité faible, donc profil faible), le scénario 1 en FAIL avec la citation de 31-368, l'alternative par catégorie en PASS, un clic sur une preuve, puis le curseur d'horizon passé à 10 ans qui fait basculer le verdict. Ensuite, un contraste avec Amira en mode B.

## 7. Composants

L'équilibre est fixé : **3 agents LLM + 2 briques de code + Guardrails + KB**. On n'ajoute pas d'agent. Les agents utilisent le **SDK Strands (Python)** avec Bedrock.

### 7.0 Politique de langue (décision ferme)

**Tout le système interne fonctionne en anglais. Seule la frontière avec l'utilisateur est dans sa langue.**

Pourquoi :
- le corpus de la KB est entièrement en anglais ;
- la langue du prompt influence le comportement du modèle ;
- le retour d'expérience Strands l'a montré : un sous-agent répond dans la langue de ce qu'on lui envoie.

Une seule langue interne rend le comportement des agents prévisible et la recherche dans la KB plus fiable.

| Élément | Langue |
|---|---|
| Prompts système des 3 agents (`prompts.py`) | **anglais** |
| Descriptions des outils et de leurs paramètres (docstrings lues par le modèle) | **anglais** |
| Échanges entre composants : arguments d'outils, champs du mandat, éléments du registre (`label`, `method`, `caveats`), raisons des verdicts | **anglais** |
| Requêtes vers la Knowledge Base (`search_regulation`) | **anglais** |
| Corpus de la KB et extraits cités (`excerpt`) | **anglais** (citation fidèle, jamais traduite dans le registre) |
| Journaux et traces | **anglais** |
| Message tapé par l'utilisateur | sa langue (stocké tel quel pour l'historique affiché) |
| Tout texte montré à l'utilisateur : messages de l'orchestrateur, réponses rapides, mandat affiché, motifs des verdicts, 4 rubriques, mentions de la province | **la langue de l'utilisateur** (`userLanguage`) |

Mécanisme :
1. **Entrée.** L'orchestrateur détecte la langue du message (`userLanguage`, code ISO 639-1 : `fr`, `en`…), l'enregistre sur la conversation, puis **traduit la demande en anglais** avant toute autre action. Tout ce qu'il transmet ensuite (arguments d'outils, brouillon du mandat, `run_analysis`) est en anglais. Les réponses rapides sont affichées dans la langue de l'utilisateur, mais chacune correspond à une valeur interne en anglais ou à une énumération.
2. **Traitement.** Moteur, règles, auditeur, rédacteur et vérificateur travaillent en anglais. L'auditeur cherche dans la KB avec des requêtes en anglais. Le rédacteur produit les 4 rubriques **en anglais** (version de référence, stockée).
3. **Sortie.** Avant l'affichage, l'orchestrateur **traduit dans `userLanguage`** tout ce qui va à l'utilisateur : son propre message, les 4 rubriques, les motifs des verdicts et les mentions de la province. Il ne fait rien si `userLanguage = en`.
   - Les emplacements `{EV-nn}` et `{KB-nn}` sont **conservés à l'identique**.
   - Les extraits réglementaires restent en anglais : l'interface les affiche comme « extrait original (anglais) ».
   - Les libellés fixes des mesures (« Volatilité annualisée ») sont traduits par l'interface à partir de clés stables.
4. Le **vérificateur** contrôle le texte final traduit : emplacements et chiffres, avec des motifs interdits en français et en anglais.

Le prompt système de l'orchestrateur, rédigé en anglais, contient donc explicitement la consigne suivante : *« If the user's message is not in English, translate it into English before doing anything else; all tool calls and all communication with other components are in English. When replying to the user, answer in the user's language (`userLanguage`), keep every {EV-nn}/{KB-nn} placeholder unchanged, and never translate quoted regulatory excerpts. »*

**Repli si la latence pose problème en démo :** le rédacteur peut écrire directement dans `userLanguage` (paramètre transmis en anglais dans son contexte), ce qui évite l'étape de traduction. Le reste de la politique ne change pas.

### 7.1 Orchestrateur — LLM (Claude Sonnet 5.5 via Bedrock)
- **Rôle :** il est la seule voix qui parle à l'utilisateur.
  - Il détecte la langue de l'utilisateur et traduit sa demande en anglais (7.0).
  - Il lit la session (portefeuille, profil de base, province) et détecte ce qui manque pour le mandat.
  - Il pose **une seule** étape de questions (2 au maximum, avec options de réponse rapide), dans la langue de l'utilisateur.
  - Il rédige le mandat (en anglais en interne, affiché traduit), attend la confirmation et lance `run_analysis`.
  - Il traduit la restitution dans la langue de l'utilisateur.
  - Il répond aux questions de suivi à partir du registre.
- **Outils :**
  - `load_session(session_id)` ;
  - `propose_mandate(mandate_draft)`, qui valide le schéma et enregistre en `MANDAT_PROPOSE` ;
  - `run_analysis(session_id, mandate_version)`, qui lance les étapes 3 à 5 ;
  - `read_evidence(evidence_id)`.
- **Interdits :** calculer de tête, citer un chiffre absent du registre, nommer un titre comme recommandation.
- **Fail mode :** fail-closed sur un mandat incomplet. Il pose la question ou propose des valeurs par défaut marquées « hypothèse », que l'utilisateur confirme.

### 7.2 Moteur de calcul — code Python (DuckDB/pandas)
- **Rôle :** à partir du mandat et du portefeuille, construire les scénarios 0/1/2 et calculer toutes les mesures (section 10). **Chaque résultat est inscrit au registre** (`EV-xx`).
- **Outils exposés** (fonctions Python, aussi appelables directement par le pipeline) :
  - `portfolio_impact(portfolio, operations, window)` ;
  - `stress_test(portfolio, period_id)` ;
  - `concentration(portfolio)` (titre unique, secteur, pays, devise, avec composition des FNB) ;
  - `correlation(assets, window)` ;
  - `asset_profile(ticker, window)` ;
  - `macro_regime(date)`.
- **Alternative (scénario 2) :** une règle déterministe. Elle garde le montant de l'idée, mais remplace l'actif risqué par une catégorie compatible avec le profil retenu, ou limite la poche à un plafond d'**hypothèse d'équipe**. Le moteur peut produire 1 ou 2 alternatives. Toutes sont décrites par catégorie.

### 7.3 Auditeur de convenance — LLM (Claude Sonnet 5.5) + KB + règles en code
- **Rôle :** les **verdicts viennent des règles R1 à R10, écrites en code** (section 9). L'auditeur ne décide pas du verdict. Il **cherche dans la Knowledge Base le passage qui fonde chaque verdict**, l'inscrit au registre (`KB-xx` : document, section, extrait court, juridiction, version, URL) et formule le motif en une phrase.
- **Outils :**
  - `check_rules(mandate, scenarios)` (code) ;
  - `search_regulation(query, subjects, jurisdictions)`, qui appelle Bedrock KB `Retrieve` avec un filtre de métadonnées `juridiction ∈ {CA, <province>}` et éventuellement sur `sujets`. **La requête est toujours en anglais**, comme le corpus.
- **Langue :** il travaille en anglais. Ses motifs de verdict sont en anglais, et l'orchestrateur les traduit pour l'affichage.
- **Fail mode :** si aucun passage pertinent n'est trouvé, le verdict reste affiché avec la mention « fondement : hypothèse d'équipe » ou « non vérifié ». L'auditeur n'invente jamais de citation.

### 7.4 Rédacteur — LLM (Claude Sonnet 5.5)
- **Rôle :** rédiger **4 rubriques** à partir du registre seulement :
  1. Quelles données ont été utilisées
  2. Pourquoi ce verdict
  3. Limites
  4. Ce qui changerait la réponse
- **Règle clé : le rédacteur n'écrit jamais de chiffre.** Il écrit des **emplacements** `{EV-07}`, `{KB-03}`. L'interface y insère la valeur exacte du registre sous forme de badge cliquable. Ça rend un chiffre faux impossible, supprime les problèmes d'arrondi et permet de diffuser le texte en continu sans risque.
- **Outil :** `read_evidence` (lecture seule du registre complet de la session).
- **Langue :** il rédige en anglais (version de référence). L'orchestrateur traduit ensuite dans la langue de l'utilisateur en conservant les emplacements (7.0).
- **Exceptions autorisées sans emplacement :** les constantes saisies par l'utilisateur et répétées (« 3 ans », « 15 000 $ ») et les noms de documents.

### 7.5 Vérificateur — code Python, non bloquant
- Il lit chaque phrase du texte **final, tel qu'il sera affiché** : la version traduite dans la langue de l'utilisateur, ou la version anglaise si `userLanguage = en`.
- **Contrôles :**
  1. Chaque `{EV-xx}` et `{KB-xx}` existe dans le registre de la session.
  2. Aucun nombre écrit à la main (%, $, points de base, ratio, nombre décimal) en dehors des constantes du mandat.
  3. Pas de formule de promesse ou de recommandation. La liste de motifs existe **en anglais et en français** : « you should buy », « guaranteed », « vous devriez acheter », « garanti »…
  4. Les emplacements de la version anglaise et ceux de la version traduite sont identiques : la traduction n'en a perdu ni ajouté aucun.
- **En cas d'échec :** la phrase est **masquée et signalée** (« phrase retirée : chiffre non vérifié »). La réponse continue. Il n'y a **pas de nouvelle tentative bloquante**.
- **Affichage :** un score dans l'interface (« 21/21 chiffres et 3/3 citations vérifiés »).

### 7.6 Guardrails — Amazon Bedrock Guardrails
- Placé en entrée et en sortie.
  - **En entrée**, il s'applique à la traduction anglaise de la demande, et aussi au texte original : les filtres de Guardrails sont les plus fiables en anglais, et la couverture des autres langues est à vérifier.
  - **En sortie**, il s'applique au texte final affiché.
- **Il bloque :**
  - les ordres de transaction (« achète pour moi ») ;
  - les promesses de rendement ;
  - les demandes de conseil personnalisé réglementé ;
  - les données personnelles (renseignements bancaires).
- **Faux positifs confirmés par le banc de fumée du 2026-11-14** : « Et si j'ajoute 10 % de XIU… » et « Compare XSP and ZEQT for my portfolio » (en anglais et en français) étaient bloqués. Correction en cours dans `ws/smoke-fixes` :
  - définitions des sujets affinées (hypothèses et comparaisons exclues) ;
  - un blocage **par sujet** sur un texte qui n'est pas en anglais n'est retenu que s'il se confirme sur la traduction anglaise ;
  - un blocage pour **renseignement personnel** sur le texte d'origine reste final.
- **Remplace l'idée d'un agent « intake guard »**, qui a été écartée.

## 8. Schémas de données (proposés, à aligner sur `contract/knowledge-graph.yaml`)

```jsonc
// Portefeuille
{ "positions": [ { "ticker": "XIU.TO", "amount": 30000, "currency": "CAD" } ],
  "base_currency": "CAD", "label": "Persona Robert" }

// Mandat (versionné)
{ "version": 1, "confirmed_at": "2026-11-15T14:02:00Z",
  "objective": "projet",              // croissance | revenu | preservation | projet | retraite
  "objective_detail": "achat condo",
  "horizon_years": 3,
  "risk_tolerance": 3,                 // 1 (faible) .. 5 (élevé)
  "risk_capacity": 1,                  // 1 .. 5
  "risk_profile": 1,                   // = min(tolerance, capacity)  ← R1
  "max_acceptable_loss_pct": 10,       // saisi, sinon défaut par horizon (hypothèse d'équipe)
  "constraints": ["pas de crypto"], "preferences": { "esg": false, "exclude_sectors": [] },
  "province": "QC",
  "idea": { "mode": "A", "operations": [ { "action": "add", "ticker": "NVDA", "amount": 15000, "currency": "CAD" } ] },
  "sources": { "horizon_years": "reponse_utilisateur", "risk_tolerance": "persona", "max_acceptable_loss_pct": "hypothese_equipe" } }

// Élément du registre — calcul
{ "id": "EV-07", "kind": "metric", "tool": "portfolio_impact", "scenario": 1,
  "metric": "annualized_volatility", "value": 0.152, "formatted": "15,2 %",
  "currency": "CAD", "price_basis": "adj_close", "window": "2021-11-12/2026-11-12",
  "method": "écart-type des rendements quotidiens × √252, calendrier aligné",
  "sources": ["Yahoo Finance via yfinance (starter)", "Banque du Canada Valet (USD/CAD)"],
  "caveats": ["biais du survivant", "le passé ne prédit pas l'avenir"] }

// Élément du registre — citation réglementaire
{ "id": "KB-03", "kind": "regulation", "rule": "R1",
  "document": "Joint CSA/CIRO Staff Notice 31-368", "section": "A.1 Determination of risk profile",
  "excerpt": "…a client's overall risk profile should reflect the lower of the two…",
  "jurisdiction": "CA", "version": "2025-12-10", "url": "https://…", "kb_file": "CA_31-368_staff-notice-CSA-CIRO_2025-12-10_en.pdf" }

// Verdict de règle
{ "rule": "R2", "scenario": 1, "status": "FAIL",
  "reason_code": "MAX_LOSS_EXCEEDED", "evidence": ["EV-08"], "citations": ["KB-03"],
  "threshold": { "value": 10, "nature": "hypothese_equipe" } }

// Session DynamoDB (clé de partition : sessionId)
{ "sessionId": "uuid", "stage": "RESULTAT", "province": "QC",
  "portfolio": {…}, "mandates": [ {v1}, {v2} ], "messages": [ … ],      // historique Strands
  "runs": [ { "mandate_version": 1, "scenarios": […], "evidence": […], "verdicts": […],
              "answer": { "sections": […], "verifier": { "numbers_ok": 21, "citations_ok": 3, "hidden": 0 } } } ] }
```

## 9. Règles de l'auditeur (R1–R10)

Les seuils marqués « hypothèse » vivent dans un fichier de configuration (par ex. `rules_config.json`) et sont affichés comme hypothèses d'équipe.

| Règle | Contrôle (en code) | Fondement | Nature |
|---|---|---|---|
| **R1** | `risk_profile = min(risk_tolerance, risk_capacity)`. Si l'idée suppose un profil plus élevé, WARN ou FAIL | Avis 31-368, partie A (le profil global reflète la plus basse des deux) | texte |
| **R2** | La pire baisse historique simulée du scénario dépasse `max_acceptable_loss_pct`, ou le défaut associé à l'horizon. Défauts proposés : < 3 ans → 10 %, 3–8 ans → 20 %, > 8 ans → 35 % | 31-103 art. 13.2 et 13.3 (horizon, profil) · seuils = hypothèse | texte + hypothèse |
| **R3** | L'impact est mesuré sur **l'ensemble du portefeuille**, jamais sur le titre ajouté seul | Avis 31-368, partie C « Impact on client's account or portfolio » | texte |
| **R4** | Au moins une alternative raisonnable est présentée dès qu'un scénario est en WARN ou FAIL | Avis 31-368, partie C « Reasonable range of alternative actions » | texte |
| **R5** | L'alternative et tout le texte affiché ne recommandent aucun titre nommé (contrôle sur le texte, liste de motifs) | Note de l'OCRI GN-3200-26-001 | texte |
| **R6** | Poids d'un titre unique (y compris via la composition des FNB) : WARN au-delà de 10 %, FAIL au-delà de 20 % du portefeuille | hypothèse d'équipe (aucune règle officielle trouvée) | hypothèse |
| **R7** | Crypto dans un scénario : avertissement sourcé, et plafond (0 % si refusée dans le mandat, 5 % pour un profil ≤ 3, 10 % pour un profil 4–5) | Avis 21-329 et 21-332 · plafonds = hypothèse | texte + hypothèse |
| **R8** | Préférence ESG : un fonds n'est présenté comme « ESG » que si une source le montre (méthodologie de l'émetteur). Pour une action, on indique seulement le secteur (fait) et « non vérifié » pour les controverses | Avis 81-334 (fonds ESG) | texte |
| **R9** | Mentions adaptées à la province : régulateur à nommer, titres que l'outil ne prend pas, orientation vers un professionnel inscrit | AMF (QC), FSRA (ON), FCAA (SK) | texte |
| **R10** | Aucune donnée macro utilisée avant sa date de publication (IPC, chômage) | Énoncé du Datathon, règle interne | interne |

## 10. Données et méthodes du moteur de calcul

**Jeu de départ** (`mes_docs_perso/Datathon2026/alphaforge_starter/`, fenêtre 2021-11-12 → 2026-11-12, extrait le 2026-11-13) :
- `assets_universe.csv` : 31 actifs.
  - 10 actions TSX : RY, TD, MFC, ENB, CNQ, CNR, FTS, ATD, SHOP, CSU, toutes en `.TO`.
  - 10 actions US : AAPL, MSFT, NVDA, GOOGL, AMZN, TSLA, JPM, JNJ, PG, XOM.
  - 9 FNB : XIU.TO, SPY, QQQ, ESGV, XBB.TO, ZST.TO, AGG, TLT, GLD.
  - 2 cryptos : BTC-USD, ETH-USD.
  - ZEQT, XSP et COST n'y sont pas. Ils sont ajoutés par le jeu élargi ci-dessous.
- `prices_daily.csv` (~40 000 lignes), `corporate_actions.csv`, `fx_usdcad_daily.csv` (Banque du Canada), `macro_rates.csv` (format long : V39079, rendements 2 et 10 ans GoC, IPC Canada, DFF, DGS2, DGS10, CPIAUCSL, UNRATE), `sources_metadata.csv`, `build_dataset.py`.

**Jeu élargi (décision d'équipe du 2026-11-14)** : le jeu de départ ne suffit pas. Son README le dit lui-même : *« It is not the dataset the jury expects you to use »* (« ce n'est pas le jeu de données que le jury s'attend à vous voir utiliser »). Et le critère « Données » pèse 20 %. WS3 construit donc un jeu plus large, toujours au format du contrat :
- **Univers d'environ 250 actifs**, choisis pour servir les cas d'usage, et non 5 000 titres :
  - **FNB canadiens courants chez les investisseurs autonomes** : indices larges, FNB de répartition d'actifs, obligations, dividendes, secteurs, or, ESG, épargne, dont **XSP.TO, ZEQT.TO** (cités dans l'atelier), XEQT.TO, VFV.TO, ZAG.TO ;
  - **les constituants du S&P/TSX 60** ;
  - **les grandes capitalisations américaines** de tous les secteurs, y compris des titres très médiatisés (test de Robert) ;
  - **les FNB américains** : larges, sectoriels SPDR, obligations, or, immobilier, ESG, thématiques (test d'Amira) ;
  - **3 cryptos** : BTC-USD, ETH-USD, SOL-USD.
- **Liste de candidats** dans `data/ingestion/universe.yaml`, rangée par catégorie. **Chaque ticker est validé à l'ingestion** : ceux que yfinance ne renvoie pas, ou qui ont trop peu d'historique, sont écartés et listés dans le manifeste. Aucun ticker n'est inventé.
- **Fenêtre de 10 ans** (environ 2016-11 → 2026-11) au lieu de 5. On gagne deux crises réelles comme tests de résistance : fin 2018 et le **krach COVID de 2020**, en plus de 2022. Les actifs plus récents (ex. ZEQT.TO, lancé en 2022) ont un historique plus court : il est signalé, jamais comblé.
- **Version du jeu** = date d'extraction. La variable Terraform `dataset_version` et `backend/api/tickers.json` (validation des tickers de WS4) sont mis à jour à l'intégration.
- **Volume** : environ 250 actifs × 2 500 jours, soit environ 600 000 lignes. C'est léger en Parquet.
- **Biais du survivant amplifié par 10 ans** : on le dit explicitement dans les limites.

**Pièges du jeu de départ à traiter (et à documenter) :**
1. Utiliser `adj_close` pour les rendements. Les prix sont déjà ajustés pour les fractionnements : **ne pas réappliquer** les lignes `split`.
2. Les prix sont dans la devise de cotation (`.TO` en CAD, le reste en USD). On convertit en **CAD** avec `fx_usdcad_daily.csv`, en reportant le dernier taux connu les jours fériés canadiens. **On affiche aussi la devise native**, parce que la conversion ajoute l'effet de change à la volatilité.
3. Les calendriers ne sont pas alignés : TSX, marchés US, et crypto 7 jours sur 7 en jours civils UTC. Les mesures par actif sont calculées sur leur calendrier natif (annualisation √252 pour les actions et FNB, √365 pour la crypto). Les portefeuilles et les corrélations sont calculés sur **l'intersection des jours ouvrés nord-américains**. On le documente.
4. **CNQ.TO, 2022-08-22 :** un « split » de 1,021 le même jour qu'un dividende de 0,75 $. C'est probablement une distribution spéciale : on l'isole et on le documente dans le contrôle qualité.
5. ZST.TO a une ligne à volume nul (2022-07-06).
6. **Macro mensuelle datée au mois de référence :** on ajoute une colonne `publication_date` à IPC et chômage (R10). Les valeurs FRED sont révisées.
7. **Biais du survivant :** l'univers a été choisi en 2026. On le mentionne dans chaque rubrique « Limites ».
8. Licence Yahoo : usage personnel. On le mentionne dans la documentation.

**Mesures :**
- rendement total sur la fenêtre ;
- volatilité annualisée ;
- **pire baisse** (maximum drawdown) sur la fenêtre et par période de test ;
- corrélations ;
- poids par titre, secteur, pays et devise, **avec la composition des FNB** ;
- éventuellement le ratio de Sharpe, avec le taux sans risque du jour tiré de V39079 ou DFF.

**Périodes de test de résistance**, dérivées des données par un outil qui écrit sa propre preuve EV (pas de dates choisies à la main) :
- **2022** : année civile 2022, quand actions et obligations ont baissé ensemble ;
- **Krach COVID 2020** : du sommet au creux de SPY au premier semestre 2020 (possible grâce à la fenêtre de 10 ans) ;
- **Hausse des taux** : du premier relèvement au dernier, selon V39079 (BoC) ou DFF (Fed) ;
- **Krach crypto** : du sommet au creux de BTC-USD dans la fenêtre.

**Fiche enrichie des FNB — `assets_metadata_enriched.json`** (décidé) :
- **Pour les 9 FNB du jeu de départ, plus les FNB clés du jeu élargi** (XSP.TO, ZEQT.TO, XEQT.TO, VFV.TO, ZAG.TO, XIC.TO), soit environ 15 fiches relevées à la main. Pour les autres FNB, on indique « composition non disponible » et l'exposition se lit par catégorie :
  - `sector_weights` ;
  - `top_holdings` (5 à 10 positions avec leur poids) ;
  - `country_weights` ;
  - `mer_pct` ;
  - pour ESGV, les `exclusions` de la méthodologie.
- **Chaque valeur porte `source_url` et `as_of_date`** (fiche de l'émetteur : iShares, Vanguard, SPDR, Invesco, BMO) et entre au registre comme preuve. Les chiffres qui circulent (« ~32 % de tech dans SPY ») **ne sont pas vérifiés** : il faut les relever nous-mêmes.
- **Pas d'indicateur ESG ni d'« exposition fossile » inventés pour les 20 actions.** On utilise le **secteur** (fait du jeu de départ : Énergie pour ENB, CNQ, XOM) et « controverses : non vérifié ».

**Stockage :** les CSV sont convertis en Parquet sur S3 et interrogés avec DuckDB dans la Lambda. Une copie locale sert aux tests.

## 11. Knowledge Base réglementaire

- **Corpus :** `docs/for_KB/`, 13 documents récupérés le 2026-11-14, **tous en anglais** (décision d'équipe : une seule langue pour le corpus). Le README du dossier les liste. Le rédacteur et l'orchestrateur répondent quand même dans la langue de l'utilisateur ; les extraits cités restent en anglais.
- **Métadonnées :** chaque fichier a un `<fichier>.metadata.json` au format Bedrock KB : `juridiction`, `regulateur`, `sujets` (liste), `date_version`, `langue`, `type_document`, `source_url`, `date_recuperation`.
- **La documentation du Datathon n'est pas dans la KB** : elle sert à construire l'outil, pas à répondre à l'utilisateur.

| Juridiction | Fichiers | Apport | Utilisé pour |
|---|---|---|---|
| CA | `CA_31-368_staff-notice-CSA-CIRO_2025-12-10_en.pdf` | Tolérance ≠ capacité ; le profil global reflète la plus basse. Partie C : impact sur le portefeuille, gamme d'alternatives, opérations demandées par le client | R1, R3, R4, questions de cadrage |
| CA | `CA_31-103_regulation-official-consolidated_2026-07-04_en.pdf` (AMF, version anglaise officielle), `CA_31-103CP_companion-policy-consolidated_2026-01-01_en.pdf` (non officielle, FCNB) | Art. 13.2 connaissance du client, art. 13.3 convenance | définitions du mandat, R2 |
| CA | `CA_CIRO_GN-3200-26-001_OEO-guidance_2026-03-12_en.txt`, `CA_CIRO_bulletin-26-0059_OEO_2026-03-12_en.txt` | Aide à la décision permise, interdiction de recommander un titre | R5, pitch |
| CA | `CA_81-334_staff-notice-ESG-funds_2024-03-07_en.pdf` | Ce qu'un fonds doit montrer pour se dire ESG | R8 (Mateo) |
| CA | `CA_21-329_staff-notice-crypto-platforms_2021-03-29_en.pdf`, `CA_21-332_staff-notice-crypto-platforms-PRU_2023-02-22_en.pdf` | Plateformes crypto : inscription, garde des actifs | R7 (Amira) |
| QC | `QC_AMF_financial-planner-title_en.txt`, `QC_NBDB_tips-better-investment-decisions_en.txt`, `QC_NBDB_relationship-disclosure-information_2025-09_en.pdf` | Titre réservé ; questions de BNCD/NBDB (objectifs, horizon, confort avec le risque, diversification, fréquence des transactions) ; BNCD = exécution sans conseil | R9, cadrage |
| ON | `ON_FSRA_rule-2020-001-title-protection_en.pdf` | « Financial planner » et « financial advisor » réservés | R9 |
| SK | `SK_FCAA_FPFA-proposed-regulations-notice_en.pdf` | Projet de règlement sur les titres (statut final à vérifier) | R9 |

**Comment l'interroger :**
- Bedrock Knowledge Base sur un bucket S3, avec filtre de métadonnées `juridiction` dans `["CA", province]`, et éventuellement `sujets` qui contient le sujet de la règle.
- Les règles de convenance sont **nationales** (31-103 est commun à toutes les provinces ; l'OCRI est national). La province change surtout le régulateur à nommer, les titres protégés et la langue.

**Conseils d'indexation :**
- Pour 31-103 (168 pages), si la recherche est bruitée, n'indexer que les articles 13.2 et 13.3.
- Créer la KB **en premier** le dimanche matin : le magasin de vecteurs est l'étape la plus longue.
- Garder un **repli local** : un index JSON des passages clés, avec citations exactes, pour que la démo ne tombe pas si la KB n'est pas prête. Mais la démo montre la vraie KB.
- Vérifier les conditions de réutilisation de chaque site avant de republier le corpus.

## 12. Interface

**Un seul écran, trois colonnes :**
1. **Portefeuille et mandat** : positions, total, puis le mandat confirmé avec la source de chaque ligne (persona, réponse, hypothèse) et des **curseurs** (horizon, perte acceptée) pour le « et si ».
2. **Conversation** : messages, boutons de réponse rapide, confirmation du mandat.
3. **Panneau de simulation** :
   - les 3 scénarios côte à côte, à la même échelle (volatilité, pire baisse 2022, répartition) ;
   - les pastilles PASS / WARN / FAIL par règle, avec le badge de citation `KB` ;
   - les 4 rubriques d'explication, avec les badges `EV` et `KB` cliquables qui ouvrent la carte de preuve ;
   - le score du vérificateur.
- **Ordre d'apparition :** scénarios et pastilles d'abord, puis citations, puis texte diffusé en continu.
- **Mention permanente :** « Simulation pédagogique, pas un conseil financier ». Les mentions de la province (R9) sont ajoutées.
- **Langue :** l'interface est dans la langue de l'utilisateur (`userLanguage`) : libellés fixes traduits à partir de clés stables, textes générés déjà traduits par l'orchestrateur. Les extraits réglementaires sont affichés en version originale anglaise, avec la mention « extrait original (anglais) ».

## 13. Architecture AWS

| Service | Rôle |
|---|---|
| **S3 + CloudFront** | Hébergement de l'interface ; Parquet ; corpus de la KB |
| **Lambda (ou AgentCore Runtime)** | Orchestrateur et pipeline. Réponse diffusée en continu (`RESPONSE_STREAM`, NDJSON, signal régulier pour garder la connexion ouverte). Garder la Lambda chaude pendant la démo |
| **Bedrock + Strands** | **Claude Sonnet 5.5 pour les 3 agents**, région **us-east-1** (décision validée : accès testé par l'équipe ; profil d'inférence `global.anthropic.claude-sonnet-5-5`, lu dans la config par agent pour pouvoir en changer). Toutes les ressources AWS restent dans us-east-1 |
| **Bedrock Knowledge Bases** | Corpus réglementaire avec filtre de métadonnées par juridiction |
| **Bedrock Guardrails** | Filtre d'entrée et de sortie |
| **DynamoDB** | Sessions, portefeuilles, mandats versionnés, registres, résultats. Les sessions de démo peuvent être rejouées si Bedrock ou le réseau flanche |
| **CloudWatch** | Jetons et durée par composant, traces affichées si le temps le permet |
| **Langfuse** (hors AWS, optionnel) | Traces OpenTelemetry de Strands (`backend/agents/telemetry.py`, fail-open), projet https://us.cloud.langfuse.com. Clé secrète dans `.env` en local et dans SSM sur AWS. Voir `AGENTS.md`. Le texte des prompts y est envoyé : données fictives seulement (règle du contrat à préciser) |

**Calcul :** nos propres outils Python (`@tool` de Strands). **Pas de serveur MCP** (décision prise). AgentCore Code Interpreter n'est pas retenu pour le MVP.

**Leçons du retour d'expérience Strands** (`mes_docs_perso/strands-sdk-agents-retour-experience.md`). Elles viennent du SDK TypeScript : vérifier l'équivalent en Python.
- Toujours fixer `maxTokens` (sinon le maximum est réservé contre le quota ; trop bas → `MaxTokensError`).
- Nommer chaque agent (`name`), sinon toutes les traces s'appellent « Strands Agent ». Ajouter un attribut de session aux traces.
- Pas d'affichage sur stdout dans Lambda (`printer=False` ou l'équivalent Python).
- Tester que chaque outil et chaque paramètre a une description non vide : une description vide est acceptée sans erreur.
- Un modèle par agent dans une table (`MODELS`) ; une toolbox qui déclare quels outils sont accordés à quel agent, vérifiée au démarrage.
- Tout texte venu d'un outil ou de la KB est une donnée non fiable : l'encadrer, et placer la vraie consigne **après** lui.
- Un message refusé ne doit pas entrer dans l'historique de session.
- **La langue d'un sous-agent suit la langue de ce qu'on lui envoie** (leçon 8 du retour d'expérience). D'où la politique de la section 7.0 : prompts, descriptions d'outils et messages entre composants toujours en anglais, et langue de sortie fixée explicitement.
- Séparer la logique pure (calculs, règles, vérificateur) des entrées-sorties, et la tester sans Bedrock.

## 14. Banc d'évaluation (à citer dans la documentation technique)

Un script lance une douzaine de scénarios sur le pipeline complet, avec **un contrôle vérifiable par scénario** :

| Scénario | Contrôle |
|---|---|
| Robert + « 30 % TSLA/NVDA », « tout sur NVDA », « 50 % BTC » | le scénario 1 est en FAIL et un scénario 2 en PASS existe |
| Amira, IA et crypto offensives | crypto ≤ plafond, et au moins 3 secteurs hors tech dans l'alternative |
| Mateo, préférence ESG | toute affirmation ESG cite un `KB` ou une source d'émetteur ; les autres sont « non vérifié » |
| Tous | le vérificateur ne masque aucune phrase (`hidden == 0`), 100 % des badges sont résolus |
| Tous | aucun titre nommé comme recommandation (R5) |
| Hors cadre (« achète pour moi », « garantis 20 % ») | refus de Guardrails ou de l'orchestrateur, message absent de l'historique |
| Province ON contre QC | les mentions R9 changent ; les règles de convenance restent identiques |
| Même demande en français et en anglais | mêmes verdicts et mêmes preuves EV ; réponse affichée dans la langue de la demande ; requêtes KB en anglais dans les traces ; emplacements identiques avant et après traduction |

Les calculs, les règles et le vérificateur ont aussi des **tests unitaires sans Bedrock**.

## 15. Périmètre et priorités

- **MVP (indispensable) :**
  - le mode A de bout en bout ;
  - le moteur de calcul, le registre et le vérificateur ;
  - l'orchestrateur, l'auditeur (R1 à R6) et le rédacteur ;
  - la KB avec filtre par juridiction ;
  - les sessions DynamoDB ;
  - l'affichage progressif.
- **Prévu :** modes B et C, Guardrails, R7 à R10, « et si » par curseurs (mandat v2), banc de tests, fiche enrichie des FNB.
- **Bonus :** traces CloudWatch dans l'interface, plus de FNB décomposés.

## 16. Calendrier

- **Dimanche 15 novembre**
  - Matin : vérifier l'accès Bedrock, **créer la KB**, préparer le Parquet et la fiche des FNB.
  - En local : moteur de calcul, registre, règles, vérificateur, avec tests.
  - Après-midi : agents Strands, DynamoDB, déploiement.
  - Soir : interface et premier passage du banc.
  - *Jalon : le mode A tourne en ligne pour 2 personas.*
- **Lundi 16 novembre**
  - Matin : modes B et C si possible, corrections, banc de tests.
  - Vidéo de 5 minutes : le scénario vedette, un contraste avec Amira, un clic sur une preuve et un curseur « et si ».
  - Documentation technique (avec les résultats du banc), one pager, README.
  - **Sauvegarder le code, les données et les traces avant l'expiration du compte.**

## 17. Plan de la vidéo (environ 5 minutes)

1. **Le problème (30 s)** : l'investisseur autonome est seul face à une idée ; reprendre la diapositive 14 de l'atelier.
2. **Le scénario vedette (2 min)** : utilisateur du Québec, NVDA, condo dans 3 ans. Cadrage en une étape, mandat, affichage immédiat des scénarios, FAIL cité (31-368), alternative par catégorie, clic sur une preuve.
3. **Le « et si » (30 s)** : curseur d'horizon à 10 ans ; le verdict bascule.
4. **Le contraste (1 min)** : Amira en mode B, gain de diversification et nouvelle concentration signalée.
5. **Sous le capot (1 min)** : schéma des composants, registre, vérificateur (score), KB filtrée par province, services AWS.

## 18. Ce qu'on a écarté (décisions prises)

| Écarté | Pourquoi |
|---|---|
| Serveurs MCP (EDGAR, FRED, Code Interpreter en MCP) | On écrit nos propres outils : plus fiables et reproductibles, et pas de dépendance à un tiers pendant la démo |
| Agent ESG dédié | Artificiel : l'ESG n'était qu'un exemple du persona Mateo. On passe par les préférences du mandat, l'avis 81-334 et la méthodologie des émetteurs |
| Agent « intake guard » ou « façade » | Fait doublon avec Bedrock Guardrails et ajoute de la complexité décorative |
| Orchestrateur LLM qui délègue librement | Résultats moins reproductibles : le pipeline des étapes 3 à 5 est fixe en code |
| « Règles de convenance BNCD » | BNCD fait de l'exécution sans conseil. On cite l'ACVM et l'OCRI |
| « Aucun titre au-delà de 5 à 10 % » présenté comme règle officielle | Aucune source trouvée : c'est une hypothèse d'équipe (R6) |
| Indicateurs ESG ou « exposition fossile » inventés pour les actions | Pas de source officielle : on utilise le secteur et « non vérifié » |
| Chiffres non sourcés (« NVDA −62 % en 2022 », « 32 % tech dans SPY ») | Tout chiffre doit venir de nos calculs ou d'une fiche d'émetteur datée |
| Vérificateur bloquant avec nouvelle tentative | Trop lent et risqué en direct : emplacements `{EV}` et masquage non bloquant |
| Optimisation « portefeuille optimal » sur rendements passés | Contraire à l'esprit de l'énoncé (pas de prédiction à partir du passé) |
| Univers de 5 000 titres | Inutile pour des personas. On retient environ 250 actifs choisis par cas d'usage, sur 10 ans (section 10) : plus que les 31 du jeu de départ, que son propre README juge insuffisant, mais pas un univers de filtrage de marché |
| Corpus ou prompts bilingues, ou en français | Une seule langue interne (l'anglais) rend le comportement des agents et la recherche dans la KB plus prévisibles ; la langue de l'utilisateur ne sert qu'à l'affichage |

## 19. Points ouverts et risques

- **Contrat v0.4.0 aligné sur ce document** (2026-11-14). Il reste à le faire valider par l'équipe et à propager les impacts listés dans `application.changelog.impacts_to_handle` : régénérer `backend/api/registry.json` et ses tests, ajouter dans Terraform la table `Analyses`, la KB, le Guardrail et les droits IAM.
- Le temps de création de la KB (magasin de vecteurs).
- Les faux positifs de Guardrails.
- Le démarrage à froid de la Lambda pendant la démo.
- Le statut final du règlement de la Saskatchewan.
- Les conditions de réutilisation des documents de la KB.
- La fiche enrichie des FNB, à relever et dater à la main.
- Les seuils d'hypothèse (R2, R6, R7), à valider en équipe.

## 20. Sources externes vérifiées (2026-11-14)

- Avis conjoint ACVM-OCRI 31-368 (FR) : https://fcnb.ca/sites/default/files/2025-12/2025-12-10-Avis%20conjoint%20des%20ACVM-OCRI-31-368.pdf
- CSA/CIRO Staff Notice 31-368 (EN) : https://www.asc.ca/-/media/ASC-Documents-part-1/Regulatory-Instruments/2025/12/6255537-CSA-CIRO-Notice-31-368-Client-Focused-Reforms.pdf
- Règlement 31-103, version officielle (AMF) : https://lautorite.qc.ca/fileadmin/lautorite/reglementation/valeurs-mobilieres/31-103/2026-07-04/2026juil04-31-103-vofficielle-fr.pdf
- Companion Policy 31-103CP (consolidation au 2026-01-01) : https://fcnb.ca/sites/default/files/2026-01/31-103-CONS-CP-2026-01-01_0.pdf
- OCRI, note d'orientation GN-3200-26-001 (FR) : https://www.ocri.ca/salle-de-presse/publications/note-dorientation-sur-les-services-et-les-activites-dexecution-dordres-sans-conseils-2
- CIRO, guidance OEO (EN) : https://www.ciro.ca/newsroom/publications/guidance-order-execution-only-account-services-and-activities
- CIRO, bulletin 26-0059 : https://www.ciro.ca/newsroom/publications/new-guidance-order-execution-only-account-services-and-activities
- CSA Staff Notice 81-334 (révisé) : https://OSC.gov.on.ca/sites/default/files/2024-03/20240307_81-334_sn-related-investment-fund-disclosure.pdf
- CSA/IIROC Staff Notice 21-329 : https://www.bcsc.bc.ca/-/media/PWS/New-Resources/Securities-Law/Instruments-and-Policies/Policy-2/21329-CSA-and--IIROC-Staff-Notice-March-29-2021.pdf
- CSA Staff Notice 21-332 : https://www.asc.ca/en/securities-law-and-policy/-/media/81AC364F57D44E2CABF1A5B6F4519E33.ashx
- FSRA, règle 2020-001 : https://fsrao.ca/media/11436/download
- FCAA, projet de règlement FPFA : https://fcaa.gov.sk.ca/public/CKeditorUpload/Notice_of_Proposed_Reg_and_Request_for_Comment_for_FPFA_Regulations_FINAL.v2.pdf
- AMF, planification financière : https://lautorite.qc.ca/devenir-professionnel/planification-financiere
- BNCD, questions avant d'investir : https://www.nbc.ca/fr/courtage-direct/centre-educatif/debuter-investissement-autonome/creer-plan-investissement/questions-avant-investir.html
- BNCD, information sur la relation avec les clients : https://www.nbc.ca/content/dam/shared/pdf/brokerage/17230-7-bncd-info-relation-clients.pdf
- TD Securities, résumé de la nouvelle guidance OEO : https://www.tdsecurities.com/ca/en/ciro-guidance-for-oeo-sample-portfolios
