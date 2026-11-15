# AlphaForge AI — Datathon PolyFinances 2026

Un banc d'essai agentique et auto-explicatif pour l'investisseur autonome. **Simulation pédagogique seulement : aucune transaction, aucun conseil financier personnalisé.**

L'utilisateur arrive avec un portefeuille (fictif ou celui d'un persona), sa province et une idée à tester, par exemple « que se passe-t-il si j'ajoute 15 000 $ de NVDA ? ». L'outil :

1. **cadre l'intention** : un agent pose une seule étape de questions, puis l'utilisateur confirme un mandat (objectif, horizon, tolérance et capacité de perte) ;
2. **mesure l'impact** sur tout le portefeuille, en code : scénario actuel, idée telle quelle, alternative par catégorie d'actifs, et tests de résistance (2022, hausse des taux, krach crypto) ;
3. **audite le résultat** contre des règles écrites en code, en citant les textes de l'ACVM, de l'OCRI et de la province (Bedrock Knowledge Base) ;
4. **explique** ses données, son verdict, ses limites et ce qui changerait la réponse. Chaque chiffre et chaque citation renvoient au registre de preuves.

## Technologies

- **Agents :** Strands Agents SDK (Python) sur Amazon Bedrock.
- **Services AWS :** Bedrock Knowledge Bases, Bedrock Guardrails, Lambda, API Gateway, DynamoDB, S3, CloudFront, Cognito, CloudWatch. Infrastructure en Terraform.

## Documents de référence

| Document | Contenu |
|---|---|
| [`SOLUTION.md`](SOLUTION.md) | La solution retenue et les raisons de chaque décision |
| [`contract/knowledge-graph.yaml`](contract/knowledge-graph.yaml) | Le contrat : services, routes, schémas, tables, agents, modules, outils, règles |
| [`docs/workstreams.md`](docs/workstreams.md) | Le découpage du travail en chantiers |
| [`docs/for_KB/`](docs/for_KB/README.md) | Le corpus réglementaire de la Knowledge Base |
| [`AGENTS.md`](AGENTS.md) | Les consignes pour les agents de code et pour les commandes AWS et Terraform |

## Structure du dépôt

| Dossier | Contenu |
|---|---|
| `backend/common/` | Configuration, erreurs, identité et accès DynamoDB partagés |
| `backend/api/` | Lambda API (profil, conversations, portefeuilles, mandats) |
| `backend/agents/` | Lambda agents (orchestrateur, auditeur, rédacteur, calcul, règles, vérificateur) |
| `data/` | Ingestion du jeu de données de marché |
| `infra/` | Infrastructure Terraform |
| `frontend/` | Interface web |

Les instructions d'installation, de reproduction et de démarrage seront complétées à mesure que les chantiers avancent.

## Front (SPA) — lancer sur votre ordinateur

Front du contrat d'API AlphaForge v0.4.0 (simulation seulement : aucune transaction réelle, aucun conseil financier).
Le front vit dans `frontend/` (chantier WS6) : tout le front est à la racine de ce dossier.

Prérequis : [Node.js](https://nodejs.org) 18 ou plus récent.

```bash
cd frontend
npm install          # installe les dépendances (dossier node_modules, non inclus dans le zip)
npm run dev:demo     # mode démo : tout fonctionne sans Cognito ni API
```

Ouvrez ensuite **http://localhost:5173** dans votre navigateur.

- Compte prêt à l'emploi : **demo** / **demo1234**, ou créez votre propre compte depuis « Créer un compte ».
- Arrêter le serveur : `Ctrl + C` dans le terminal.

### Les deux modes

| Commande | Mode | Ce qu'il faut |
|---|---|---|
| `npm run dev:demo` | **Démo** : connexion, inscription, portefeuille, profil et assistant simulés dans le navigateur (`frontend/src/api/demo.ts`). Prix fictifs. | Rien |
| `npm run dev` | **Réel** : Cognito pour la connexion, API AlphaForge pour les données | Un fichier `.env` (voir plus bas) |

En mode démo, les données (comptes, portefeuilles, conversations) sont gardées dans le `localStorage` du navigateur.
Pour tout remettre à zéro : outils de développement du navigateur → Application → Local Storage → supprimer `af.demo.db`.

### Mode réel : fichier `.env`

Copier `.env.example` en `.env` et renseigner :
- `VITE_API_BASE_URL` : URL d'API Gateway, sans `/v1`
- `VITE_COGNITO_REGION`, `VITE_COGNITO_CLIENT_ID` : user pool Cognito (client sans secret, flux `USER_PASSWORD_AUTH` activé)

Pour l'inscription, le user pool doit autoriser l'inscription libre (`SignUp`) et le client d'application doit pouvoir écrire
les attributs `email`, `given_name` et `family_name`. L'API doit créer l'utilisateur à son premier `GET /v1/me`.

### Construire une version de production

```bash
npm run build        # résultat dans dist/
npm run preview      # sert dist/ sur http://localhost:4173
```

Pour une version de production en mode démo : `npx vite build --mode demo`.

## Parcours et pages

| Route | Contenu | Connexion requise |
|---|---|---|
| `/` | Accueil (présentation du prototype) + **questionnaire public** | Non |
| `/login` | Connexion | Non |
| `/inscription` | Création de compte + **questionnaire d'inscription** | Non |
| `/portefeuille` | Résumé du portefeuille, édition des positions, autocomplétion de ticker | Oui |
| `/marches` | Taux, devises et actifs (via l'API : `/market/search`, `/portfolios/{id}/summary`) | Oui |
| `/profil` | Profil investisseur + réponses au questionnaire d'inscription, consultables et modifiables | Oui |

L'assistant (bouton flottant) est présent sur toutes les pages connectées.

## Les deux questionnaires

Ils sont volontairement différents.

### 1. Questionnaire public (page d'accueil, sans compte)

Repris du prototype. Fichiers : `src/lib/publicProfile.ts`, `src/components/PublicQuestionnaire.tsx`.

- 6 questions : objectif, horizon, réaction à une perte de 20 %, expérience, niveau de risque accepté, but de placement.
- Score sur 100 = points obtenus / points maximum. Profil : moins de 35 **Conservateur**, moins de 65 **Modéré**, sinon **Dynamique**.
- Calcul dans le navigateur seulement. Rien n'est envoyé à l'API ni repris à l'inscription.

### 2. Questionnaire d'inscription (« Questionnaire interactif »)

Fichiers : `src/lib/risk.ts`, `src/components/RiskForm.tsx`.

5 questions, chaque réponse vaut **1 à 5 points** (1re option = 1 point … 5e option = 5 points) :

1. Horizon d'investissement
2. Perte maximale acceptable sur un an
3. Si ton portefeuille perd 20 %, que fais-tu ?
4. Objectif financier principal
5. Capacité financière à absorber une perte

**Score** = somme des points, de 5 (minimum) à 25 (maximum).

**Premier calcul** :

```
résultat = 10 − 9 × ((Score − 5) / 20)
```

Score 5 → 10 (très prudent) · Score 25 → 1 (très tolérant au risque). Exemple : score 16 → 10 − 9 × (11 / 20) = **5,05**.

Après l'inscription :
- le résultat est **enregistré pour chaque portefeuille** de l'utilisateur (`localStorage`, clé `af.risk.<userId>`, l'API n'a pas de champ pour ce résultat);
- un portefeuille créé plus tard reçoit le dernier résultat à l'ouverture de la page Profil;
- le profil investisseur de l'API (`PUT /v1/me/profile`) est rempli à partir des réponses : niveau de risque selon le score
  (5–9 faible, 10–14 faible à modéré, 15–19 modéré, 20–25 élevé), horizon et objectif;
- sur **Profil**, l'utilisateur revoit chaque réponse avec ses points, le score, le calcul et le résultat par portefeuille,
  et peut modifier ses réponses (le résultat est recalculé pour tous ses portefeuilles).

## Organisation du front

```
frontend/src/api/types.ts          types des schémas du contrat
frontend/src/api/auth.ts           Cognito : connexion, inscription, code de confirmation (jetons en sessionStorage)
frontend/src/api/client.ts         fetch + Bearer + erreurs au format schema-error
frontend/src/api/endpoints.ts      une fonction par route
frontend/src/api/demo.ts           mode démo : simulation de Cognito et des routes /v1 (actif seulement si VITE_DEMO=1)
frontend/src/lib/store.tsx         session (utilisateur courant)
frontend/src/lib/risk.ts           questionnaire d'inscription, score, calcul, stockage par portefeuille
frontend/src/lib/publicProfile.ts  questionnaire public de l'accueil
frontend/src/pages/                Landing (accueil), Login, Register, Chat, Portfolio, Markets, Profile
```

## Autres dossiers

- `backend/alphaforge/` : serveur Python de démonstration du prototype. Doublon de `backend/agents/` (WS5) ;
  décision d'équipe : à retirer. Le front ne s'y branche pas.
- `data/` : l'ingestion officielle est dans `data/ingestion/` (WS3). `data/build_dataset.py` est un doublon à retirer
  (décision d'équipe). Aucun CSV de prix n'est commité (conditions d'utilisation de Yahoo).
- `portefeuille-prototype/` : le prototype d'origine, extrait de `portefeuille-prototype.zip`. Pour le lancer :
  `cd portefeuille-prototype && npm install && npm run dev`.
