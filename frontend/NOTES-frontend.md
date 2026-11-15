# Notes du chantier WS6 (front)

Adaptation du front au contrat d'API AlphaForge **v0.4.0** (`contract/knowledge-graph.yaml`).
Branche `ws/frontend` (basée sur `main` à `166f459`). Le front ne calcule rien : tous les chiffres
affichés viennent du back (`/summary`, registre de preuves du run), sauf le mode démo qui simule
le back avec des données fictives marquées.

## Écarts constatés (à trancher à l'intégration)

1. **`warnings` du mandat en anglais.** La réponse de `POST /conversations/{sid}/mandates` livre des
   textes en anglais (ex. « Risk capacity is lower than risk tolerance… »). Le contrat prévoit que
   l'interface soit dans `userLanguage` ; le passage des warnings à `{code, message}` (ou leur
   traduction serveur) est prévu côté back. En attendant, le front les affiche tels quels, avec la
   mention « Avertissements du contrôle de cohérence (textes du serveur) » (`mandate.warningsAssumption`).
2. **i18n complet appliqué à `/chat` seulement.** Le module `lib/i18n.ts` (clés stables fr/en) couvre
   la page de session. Les autres pages (Portefeuille, Marchés, Profil, inscription) restent en
   français uniquement, comme avant le chantier. Le contrat `language_policy` vise surtout la
   conversation ; étendre l'i18n aux autres pages reste à faire si l'équipe le décide.
3. **`Run.explanation` non affichée.** Le run expose `explanation` (pas d'exécution d'agents), mais
   aucun panneau de `/chat` ne la montre aujourd'hui : le panneau de simulation montre déjà les
   verdicts, la KB et le vérificateur. À ajouter si l'équipe veut un onglet « traçabilité ».

## Hypothèses du mode démo (`src/api/demo.ts`)

Le mode démo simule le back dans le navigateur (activé par `npm run dev:demo`, `VITE_DEMO=1`) :

- **Prix et historiques fictifs**, générés de façon déterministe par ticker ; aucune donnée Yahoo.
- **Métriques de scénario dérivées de ces prix fictifs** : volatilité annualisée (√252), pire baisse,
  tests de résistance (facteurs 1,15 / 0,9 sur la pire baisse de 60 jours) — méthodes affichées dans
  les cartes de preuve `EV-nn` avec la mention « démo ».
- **Seuils d'équipe** : R4 (crypto ≤ 5 %), R6 (premier titre ≤ 10 %), marqués
  `nature: "team_assumption"` ; R1/R2 affichent le seuil du mandat.
- **KB fictive** : `KB-01` = Avis 31-368 (obligation de convenance), `KB-02` = Avis 21-332
  (plateformes de crypto-actifs). Titres des documents réels, **extraits simulés** et marqués
  « Extrait simulé en mode démo » — le texte réglementaire n'est jamais reproduit.
- **Progression** : un run reste `partial` ~4 s puis passe à `done` (narrative + vérificateur),
  pour reproduire l'affichage progressif du contrat.
- **Mandats** : validation serveur simulée (enums, bornes 1-5, province ≠ CA → 422), version
  incrémentale, `riskProfile = min(tolérance, capacité)` (R1), `effectiveMaxLossPct` = valeur saisie
  ou défaut par horizon (< 3 ans : 10 %, 3-8 : 20 %, > 8 : 35 %, hypothèse d'équipe), `changedFields`.
- La simulation d'orchestrateur est **heuristique** (mots-clés fr) : elle sert à démontrer le flux
  cadrage → confirmation → curseurs « et si », pas la qualité d'un LLM.

## Définition de fini

- L'app fonctionne contre une API simulée (`npm run dev:demo`) et `npm run build` produit des
  fichiers statiques déployables sur S3 + CloudFront (dossier `frontend/dist/`).
- Aucun CSV de prix commité (conditions d'utilisation de Yahoo ; règle `storage-dataset` du contrat).
- `npm test` (Vitest) couvre : emplacements `{EV-nn}`/`{KB-nn}` (badge inconnu = jamais de chiffre),
  affichage progressif partial → done, carte de mandat.

## Hors périmètre WS6 (décisions d'équipe, à exécuter sur `main`)

- Suppression des doublons du prototype : `backend/alphaforge/`, `backend/local_server.py`,
  `backend/lambda_handler.py`, `data/build_dataset.py`, `data/universe.py`, `data/dataset/`,
  `data/esg_screen.csv` (l'ingestion officielle est `data/ingestion/`, WS3).
- Langue des `warnings` serveur, i18n des pages hors `/chat` (voir écarts ci-dessus).
