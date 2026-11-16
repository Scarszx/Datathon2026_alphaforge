# Profilage — session 01 (2026-11-15) : où passe le temps d'une requête

Objectif : comprendre pourquoi `POST /messages` et l'analyse (`POST /runs`) sont lents, et trouver quoi optimiser.
Le budget AWS n'est pas une contrainte.

## Méthode

- Source : Langfuse (projet de l'équipe, us.cloud.langfuse.com), lu en lecture seule via `npx langfuse-cli api observations list`.
- Échantillon : les **100 dernières traces racines**, du 2026-11-15 20:27 au 2026-11-16 02:45 UTC, soit 780 observations :
  32 tours de chat (`chat-message`), 16 analyses (`analysis-run`) et 52 traces `kb.retrieve` orphelines.
- Les chiffres « état actuel » portent sur les traces postérieures au 2026-11-16 00:10 UTC, c'est-à-dire après le passage
  à Claude Sonnet 5.5 (commit `290bccc`) et la lecture S3 en parallèle de l'optimiseur (`fd004c3`, effet visible à partir de 01:02 UTC).
- Les scripts d'agrégation (`tree.py`, `agg.py`) étaient dans le scratchpad de la session, donc temporaires. Pour refaire la mesure,
  il faut récupérer les observations avec les champs `core,basic,time,metrics,model,usage,trace_context,io`,
  reconstruire l'arbre par `parentObservationId`, puis sommer les durées par nom de span.
- **Limite :** le moteur déterministe (`module-engine` : `portfolio_impact`, optimiseur, bootstrap) n'a pas de span.
  Sa durée est estimée par l'écart entre le début de `analysis-run` et le début de `module-rules.check_rules`.

## Constat 1 : le goulot est le LLM, pas le calcul (avec une nuance pour l'analyse)

### Tour de chat (`chat-message`)

| | moyenne | p50 | p90 |
|---|---|---|---|
| Durée totale | 16,0 s | 14,6 s | 28,5 s |
| dont appels LLM (orchestrateur) | 14,3 s | 12,9 s | 25,0 s |
| dont Guardrails (3 appels séquentiels) | 1,1 s | 1,2 s | 1,7 s |
| dont outils déterministes | < 0,1 s | | |

**89 % du temps d'un tour de chat est du LLM.** Les outils (`get_profile`, `get_portfolio`, `propose_mandate`,
`search_assets`) prennent entre 10 et 300 ms chacun. Ce qui coûte cher, c'est l'aller-retour LLM que chaque appel d'outil déclenche.

### Analyse (`analysis-run` puis `analysis-complete-run`)

| Étape | p50 | Remarque |
|---|---|---|
| Moteur déterministe (non tracé) | **8,6 s** | 34 à 38 s à froid, ou avant `fd004c3` |
| `module-rules.check_rules` | 0,15 s | négligeable |
| Auto-invocation Lambda (partie sync → async) | 0,4 s | **6,7 s à froid** |
| `kb.retrieve` × 3-5 en parallèle | 0,5 s | |
| agent-auditor | 3,3 s (moy. 4,1) | |
| agent-writer | **13,8 s** | le plus gros poste |
| traduction (2 appels séquentiels, hors anglais) | 2 × ~8 s | |
| `module-verifier` + Guardrail de sortie | 0,6 s | négligeable |
| **Bout en bout** | **36 s** (moy. 41, p90 55) | |

Dans l'analyse, le calcul n'est pas négligeable : le moteur représente environ 20 % du temps à chaud et devient
le plus gros poste à froid. Mais les LLM (auditeur, rédacteur, traduction) font l'essentiel, soit environ 20 à 35 s.

## Constat 2 : pourquoi chaque agent prend ce temps

Repère : Sonnet 5.5 sur Bedrock produit environ 120 à 150 jetons de sortie par seconde. **La durée d'un appel est surtout
proportionnelle au nombre de jetons générés**, plus un coût fixe d'environ 1 à 2 s qui croît avec la taille de l'entrée.
Aucune trace ne contient de jetons en cache : le prompt caching Bedrock n'est pas activé (pas de `cache_prompt` ni de `cachePoint` dans le code).

### agent-orchestrator (chat) : de 2 à 5 appels LLM par tour, 4,6 s par appel

- Répartition des tours : 2 appels (8), 3 (1), 4 (5), 5 (2).
- Strands fait une boucle : appel LLM → l'agent demande un outil → exécution → nouvel appel LLM avec le résultat → …
  Chaque cycle renvoie **tout le contexte** (prompt système d'environ 15 000 caractères, schémas d'outils, historique), soit
  6 500 à 10 000 jetons d'entrée.
- L'agent appelle presque toujours **un outil par cycle** (114 cycles sur 138), et non plusieurs en parallèle.
- La sortie structurée `OrchestratorTurn` est elle-même un dernier cycle, dans lequel l'agent écrit la réponse (500 à 1 700 jetons, donc 4 à 13 s).
- Séquence typique : `get_profile` → `get_portfolio` → `propose_mandate` → (`propose_mandate`) → `OrchestratorTurn`.
- **D'où viennent les cycles en trop :**
  1. `get_profile` est appelé dans 15 tours sur 16, et `get_portfolio` dans 13 sur 16. Le prompt dit « read them when you need them »
     (`llm/orchestrator/prompts.py:21`), et l'agent en a presque toujours besoin. Ce sont des lectures DynamoDB déterministes
     de 10 à 40 ms, mais chacune coûte un cycle LLM de 2 à 4 s.
  2. Les échecs de `propose_mandate` (voir le constat 3).

### agent-auditor : 1 appel, environ 4 s

- Il ne boucle pas : les recherches dans la Knowledge Base sont lancées par le code avant l'agent (3 à 5 `kb.retrieve` en
  parallèle, 4 workers, environ 0,45 s chacun).
- Environ 10 000 jetons d'entrée (verdicts et extraits de la KB) et environ 560 jetons de sortie (`AuditReport`). C'est court, donc rapide.

### agent-writer : 1 appel, environ 14 s

- Il ne boucle pas non plus. Il prend environ 9 000 jetons d'entrée et en écrit **environ 2 000 en sortie** (`WriterSections`) :
  2 000 / 146 jetons/s ≈ 14 s. **Sa durée est fixée par la longueur du texte demandé.**

### Traduction (agent-orchestrator, `TranslationBatch`) : 2 appels séquentiels, environ 8 s chacun

- Elle n'a lieu que si `userLanguage` n'est pas `en`. Premier appel : les sections du récit. Second appel : les motifs des
  verdicts et les mentions de juridiction.
- Environ 1 300 jetons de sortie par appel. Le second appel ne dépend que des verdicts de l'auditeur, pas du rédacteur,
  mais il attend que tout ce qui précède soit terminé (`pipeline._translate_run_texts`).

### Effet du modèle

Le passage d'Opus 5.5 à Sonnet 5.5 a fait passer le débit de 87 à 123 jetons/s pour l'orchestrateur et de 106 à 146 jetons/s pour le rédacteur,
soit environ 25 à 40 % de gain sur la durée des appels.

## Constat 3 : la validation du mandat échoue sur les noms d'industrie et provoque des timeouts

`propose_mandate` (`tools/catalog.py:209`) valide le brouillon de mandat que l'orchestrateur construit. En mode `build`,
`_check_build_preferences` (`tools/catalog.py:185`) exige que chaque industrie de `excludedIndustries` ou de `preferredIndustries`
soit **un nom exact** de la colonne `industry` de `universe.parquet`. Sinon, l'outil renvoie `valid: false` avec des suggestions proches
(`difflib`), et l'agent doit refaire un cycle.

**Le problème :** l'agent ne reçoit nulle part la liste des industries valides. La description de l'outil dit seulement
« dataset English industry names ». Il part donc des libellés du profil (par exemple « pétrole et gaz », « immobilier »)
et les développe de mémoire en noms d'industries de type Yahoo Finance. Certains de ces noms n'existent pas dans notre univers.

Mesures (14 tours avec `propose_mandate`, 23 appels) :

- **14 appels sur 23 renvoient `valid: false`**, toujours parce qu'une industrie est inconnue :
  `Oil & Gas Drilling` (5), `REIT - Office` (4), `Insurance - Specialty` / `Insurance - Reinsurance` (2),
  `Semiconductor Equipment`, `Health Care Plans`, `REIT - Hotel & Motel`.
- **Avant le commit `157a87e`** (2026-11-16 00:23 UTC, « toutes les industries inconnues signalées d'un coup, délai de l'orchestrateur porté à 30 s ») :
  l'outil signalait une seule industrie inconnue à la fois. L'agent corrigeait, retombait sur la suivante, et ainsi de suite.
  **Résultat : 5 tours d'affilée finis en `{"error": "timeout"}`** (26 à 31 s, à 23:51, 23:53, 00:10, 00:12 et 00:14 UTC), sans mandat valide.
  Ce sont les seuls échecs de l'échantillon.
- **Après `157a87e`** : un seul échec, puis un mandat valide. Mais ces tours durent encore **20 à 26 s**, tout près de la limite de 30 s
  (délai de l'orchestrateur, et limite d'API Gateway).

Autres règles de `propose_mandate` qui peuvent provoquer un aller-retour (aucune observée en échec dans cet échantillon) :
ticker inconnu (« Use search_assets »), `operations` manquantes en `add_asset` ou `rebalance`, `subjectTicker` manquant en `diagnose`,
et `riskCapacity` marquée `team_assumption`.

## Constat 4 : autres observations

- **Guardrails :** 3 appels Bedrock séquentiels par tour (entrée, entrée traduite en anglais, sortie), d'environ 0,4 s chacun.
- **Traces orphelines :** 43 des 58 `kb.retrieve` récents apparaissent comme des traces séparées. Le contexte OpenTelemetry n'est pas
  transmis aux threads du `ThreadPoolExecutor` de l'auditeur (`llm/auditor/agent.py:115`). C'est sans effet sur la latence, mais les traces d'analyse sont incomplètes.
- **Démarrages à froid :** sur le moteur, 34 à 38 s contre 8,6 s à chaud. Sur l'auto-invocation, 6,7 s contre 0,4 s.
  La Lambda agents a probablement 2 048 Mo (`infra/terraform/lambda.tf:76`) ; à vérifier.

## Pistes (classées par gain attendu, rien n'est implémenté)

1. **Industries :** donner à l'agent la liste exacte des industries de l'univers (enum dans le schéma de `propose_mandate` ou bloc dans le prompt),
   et/ou accepter côté code une correspondance proche et sûre. C'est le seul cas qui fait échouer des tours. Gain : environ −4 à −5 s par échec évité.
2. **Profil et portefeuille dans le contexte de session :** les injecter dans `session_context` au lieu de laisser l'agent appeler `get_profile` et `get_portfolio`.
   Gain : −1 à −2 cycles, soit environ −3 à −6 s par tour.
3. **Traduction :** lancer la traduction des motifs et mentions en parallèle du rédacteur (elle ne dépend que de l'auditeur),
   et les deux lots de traduction en parallèle. Gain : environ −8 s par analyse hors anglais.
4. **Rédacteur :** une section par appel, avec les appels en parallèle (environ 14 s → environ 4-5 s), ou un texte plus court.
   On peut aussi essayer Haiku 5.5 pour la traduction.
5. **Prompt caching Bedrock** sur le prompt système et les outils de l'orchestrateur (6 500 à 10 000 jetons renvoyés à chaque cycle).
   Vérifier d'abord ce que Strands `BedrockModel` expose.
6. **Démarrages à froid :** provisioned concurrency sur la Lambda agents, et plus de mémoire, donc plus de CPU (nécessite `terraform apply`).
7. **Moteur :** ajouter des spans (lecture S3 ou calcul ?), puis plus de threads de lecture, un seul fichier de prix, ou un cache `/tmp`.
8. **Guardrails :** lancer en parallèle le contrôle de l'entrée traduite et celui de la sortie (environ −0,4 s).

## Constat 5 : d'où viennent les libellés d'industrie (cause des échecs du constat 3)

- Le questionnaire d'inscription et la page Profil proposent 21 catégories larges, définies dans
  `frontend/src/lib/industries.ts`. Chaque catégorie a un champ `covers` qui donne **la liste exacte** des industries
  correspondantes dans le jeu de données (par exemple « Pétrole et gaz » → `Oil & Gas Refining & Marketing, Oil & Gas Midstream, Oil & Gas Integrated`).
- **Seul le libellé français est stocké** dans `investorProfile.preferences`, sous la forme `"Industrie : Pétrole et gaz"` ou
  `"Industrie à éviter : Immobilier (FPI)"`. Le champ `covers` reste dans le front ; le backend n'a pas de copie de cette table.
- L'orchestrateur reçoit donc le libellé seul via `get_profile`, et le prompt lui demande de
  « list every dataset industry it covers » (`llm/orchestrator/prompts.py:28`) : **il devine** la correspondance de mémoire.
  C'est de là que viennent `Oil & Gas Drilling`, `REIT - Office`, `Insurance - Specialty`, `Health Care Plans`
  (le vrai nom est `Healthcare Plans`) et `Semiconductor Equipment`.
- Vérifié sur `data/output/2026-11-15/universe.parquet` (582 titres, 103 industries) : les 32 noms de `covers` existent tous dans le jeu.
  La table du front est donc fiable, mais plus étroite que l'univers : par exemple `Oil & Gas E&P` et `Oil & Gas Equipment & Services`
  existent dans le jeu mais ne sont pas dans « Pétrole et gaz ». À trancher : faut-il élargir `covers` ?
  À vérifier aussi : la version du jeu déployée (`DATASET_VERSION`) correspond-elle à ce fichier ?
- Écart mesuré (nombre de titres du jeu) :

  | Catégorie du front | Couvert par `covers` | Familles du jeu laissées de côté |
  |---|---|---|
  | Pétrole et gaz | 3 industries, 16 titres | `Oil & Gas E&P` (9), `Oil & Gas Equipment & Services` (3) |
  | Immobilier (FPI) | `REIT - Specialty`, 5 titres | 5 autres `REIT - …`, 11 titres |
  | Assurance et régimes de santé | P&C, Brokers, Healthcare Plans | `Insurance - Life` (6), `Insurance - Diversified` (6) |
  | Banques et crédit | `Banks - Diversified` (11), Credit Services | `Banks - Regional` (9) |
  | Services publics | `Regulated Electric` (24) | Diversified, IPP, Gas, Water (10) |

  Au total, les 21 catégories couvrent 292 actions sur 475. Les autres ne peuvent être ni choisies ni exclues depuis le profil.
  Conséquence : un utilisateur qui « évite le pétrole et le gaz » garderait 12 titres pétroliers si l'on appliquait `covers` tel quel.
  L'agent, lui, essayait d'élargir (bonne intention, mauvais noms).

### Idée examinée : plusieurs jeux d'industries validés en parallèle, le premier valide l'emporte

- La validation (`propose_mandate`) prend 10 à 20 ms et est déterministe. **La lancer en parallèle ne fait rien gagner** :
  le temps perdu est celui du LLM qui écrit chaque brouillon (environ 400 à 800 jetons de JSON, soit 3 à 5 s), puis relit la réponse.
- Faire écrire N brouillons au LLM dans le même cycle multiplie par N les jetons de sortie de ce cycle : on évite un aller-retour,
  mais ce cycle devient plus long.
- « Le premier valide gagne » revient à choisir au hasard entre des mandats qui ne disent pas la même chose (par exemple, un jeu
  qui aurait laissé tomber une industrie à exclure). C'est un risque d'exactitude sur ce que l'utilisateur confirme.
- Conclusion : supprimer la devinette donne mieux. Avec des noms exacts, le premier essai est valide et il n'y a aucun retour.

### Piste retenue à discuter : résoudre les libellés dans le code, pas dans le LLM

1. Mettre la table libellé → industries du jeu dans un fichier partagé, lu par le front et par le backend (ou côté backend seulement,
   le front gardant son affichage).
2. Pendant le tour, `get_profile` (ou `session_context`) renvoie pour chaque libellé les industries exactes déjà résolues :
   `{"label": "Pétrole et gaz", "datasetIndustries": [...]}`. L'agent recopie au lieu de deviner.
3. Garde-fou côté code dans `propose_mandate` : quand un nom est inconnu et qu'une seule correspondance proche est sûre, la corriger
   et la signaler dans `warnings` au lieu de renvoyer `valid: false`.
4. Pour les industries que l'utilisateur tape dans le chat (hors profil), donner la liste des 103 industries du jeu
   dans la description de l'outil ou dans un enum du schéma.

Contrat : `preferences` reste une liste de textes, donc aucun champ public ne change. À vérifier avec l'équipe si la table devient un fichier partagé.

### Décision de l'utilisateur (2026-11-15) : recherche sur les industries du jeu au lieu des 21 catégories

- Les 21 cases « j'aime » et « j'évite » sont remplacées par une **barre de recherche avec autocomplétion** sur les industries
  du jeu. L'utilisateur tape, choisit une suggestion, et elle s'ajoute à la liste.
- Les deux listes sont **facultatives** et peuvent rester vides. C'est déjà le cas dans le code (`EMPTY_INDUSTRIES`) et dans le
  contrat (« vides par défaut, jamais exigées ») ; il faut le conserver.
- Effet attendu : le profil contient les noms exacts du jeu, l'agent les recopie, `propose_mandate` est valide au premier essai,
  et il n'y a plus de cycle LLM perdu pour ça.
- Chiffres utiles : l'univers 2026-11-15 compte 103 industries d'actions. Les candidats de l'optimiseur (actions en USD
  avec une industrie) sont 398 titres sur **101 industries**. `Agricultural Inputs` et `Other Industrial Metals & Mining`
  n'existent que hors USD, donc les choisir n'aurait aucun effet sur un portefeuille construit.
- Points à régler avant de coder : l'origine de la liste côté front (fichier généré ou route, avec un éventuel changement de contrat),
  la recherche en français (les noms sont en anglais), les profils existants qui stockent encore les anciens libellés français,
  la ligne 14 du contrat (onboarding : « industries du profil développées en industries du jeu »), `Portfolio.tsx:49`
  (développement par `covers`) et `llm/orchestrator/prompts.py:28`.

## Constat 6 : agent-writer, d'où viennent ses 14 s

Mesures sur 11 analyses avec Sonnet 5.5 (16 au total en comptant Opus).

- **Un seul cycle, un seul appel LLM, à chaque analyse.** L'agent n'a jamais appelé `read_evidence` : le budget de 4 appels d'outil et la limite de 6 tours (`models.py`) ne servent pas.
  La sortie structurée `WriterSections` arrive dans ce même cycle.
- **Durée :** 13,8 s en moyenne (p50 13,8 s, max 16 s). Entrée d'environ 8 800 jetons, sortie d'environ 2 000 jetons à environ 146 jetons/s.
- **Ce qu'il écrit vraiment :** les 4 sections font environ 3 070 caractères, soit **environ 770 jetons visibles**. C'est conforme à la consigne « deux à quatre phrases par section ».
- **Le reste, environ 1 250 jetons (60 %), est du raisonnement caché (« thinking »).** Les 11 appels contiennent un bloc `reasoningContent`
  (texte vide, signature chiffrée). Il est facturé et généré avant le texte, ce qui représente **environ 8 à 9 s sur 14**.
- **Pourquoi il réfléchit :** Sonnet 5.5 a la réflexion adaptative activée par défaut, avec l'effort `high` par défaut. `models.py` ne passe ni
  `additional_request_fields` ni réglage d'effort : on a donc le comportement par défaut. Le prompt contient beaucoup de contraintes (aucun chiffre,
  des emplacements `{EV-nn}`, des formulations interdites, les règles du mode build), et le modèle planifie avant d'écrire.
  (Sur les mêmes traces, l'orchestrateur réfléchit dans 29 appels sur 57, et l'auditeur dans 2 sur 11.)
- **Entrée :** le prompt système fait environ 900 jetons ; le reste est l'`analysis_record` en JSON (mandat, scénarios, verdicts, preuves). Elle ajoute
  surtout du temps avant le premier jeton, mais elle n'est pas l'essentiel.
- **Place dans la chaîne :** auditeur → **rédacteur** → traduction → vérificateur, en série. Le rédacteur attend l'auditeur parce que la section `why` cite les KB.
- **Qualité actuelle (point de comparaison pour toute modification) :** vérificateur sur les 11 runs : emplacements résolus 100 %,
  `forbiddenPhrases` 0, **`handwrittenNumbers` = 1 dans 8 runs sur 11** (une phrase masquée parce qu'elle contient un chiffre écrit à la main).

### Leviers sur le rédacteur (à mesurer, rien n'est fait)

1. **Effort plus bas** (`medium` ou `low`) via `additional_request_fields` de Strands `BedrockModel`, ou réflexion coupée
   (`thinking: {type: "between_tools"}` sur Sonnet 5.5, accepté seulement avec un effort `high` ou plus bas). Gain possible : jusqu'à environ −8 s.
   Risque : plus de chiffres écrits à la main ou de phrases interdites. On compare avec les chiffres du vérificateur ci-dessus.
   Il faut vérifier la forme exacte du champ sur Bedrock Converse avec un appel de test.
2. **Une section par appel, les 4 appels en parallèle :** environ 200 jetons visibles chacun, soit environ 3 à 4 s au lieu de 14 s (même effet sur la réflexion).
3. **Lancer plus tôt :** `data_used` et `limits` ne dépendent pas de l'auditeur et peuvent tourner en même temps que lui.
   `why` et `what_would_change` viennent après.
4. **Alléger l'`analysis_record`** (preuves inutiles au récit) : gain faible, sur le temps avant le premier jeton seulement.
5. **Prompt caching** (`CacheConfig` ou `cachePoint` dans Strands 1.65) : peu utile ici, puisqu'il y a un seul appel par analyse avec un enregistrement différent à chaque fois.

## Questions ouvertes pour la suite

- Comment se répartissent les 8,6 s du moteur (S3 ou calcul numpy/pandas) ? Il faut des spans.
- Quelle fraction des sessions réelles est en français, donc paie la traduction ?
- Les libellés d'industrie du profil investisseur viennent-ils du questionnaire ? Une table fixe libellé → industries du jeu
  supprimerait la devinette de l'agent.
