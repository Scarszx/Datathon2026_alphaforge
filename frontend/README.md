# Front (SPA) : lancer sur votre ordinateur

Front du contrat d'API Grow (simulation seulement : aucune transaction réelle, aucun conseil financier).
Tout le front est dans ce dossier `frontend/` (chantier WS6). Les écarts et hypothèses du chantier sont dans `NOTES-frontend.md`.

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
| `npm run dev` | **Réel** : Cognito pour la connexion, API Grow pour les données | Un fichier `.env` (voir plus bas) |

En mode démo, les données (comptes, portefeuilles, conversations) sont gardées dans le `localStorage` du navigateur.
Pour tout remettre à zéro : outils de développement du navigateur → Application → Local Storage → supprimer `af.demo.db`.

### Mode réel : fichier `.env`

Copier `.env.example` en `.env` (dans `frontend/`) et renseigner :
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
| `/chat` | **Session en 3 colonnes** : portefeuille + mandat avec curseurs « et si », conversation (mandat proposé à confirmer), panneau de simulation (scénarios, verdicts R1-R10, citations, explication, vérificateur) | Oui |
| `/portefeuille` | Résumé du portefeuille, édition des positions, autocomplétion de ticker | Oui |
| `/marches` | Taux, devises et actifs (via l'API : `/market/search`, `/portfolios/{id}/summary`) | Oui |
| `/profil` | Profil investisseur + réponses au questionnaire d'inscription, consultables et modifiables | Oui |

La session (`/chat`) remplace l'assistant flottant des versions précédentes. Les écarts et hypothèses
du chantier sont consignés dans `frontend/NOTES-frontend.md`.

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
frontend/src/api/auth.ts           Cognito : connexion, inscription (confirmée d'office, sans code) (jetons en sessionStorage)
frontend/src/api/client.ts         fetch + Bearer + erreurs au format schema-error
frontend/src/api/endpoints.ts      une fonction par route
frontend/src/api/demo.ts           mode démo : simulation de Cognito et des routes /v1 (actif seulement si VITE_DEMO=1)
frontend/src/lib/store.tsx         session (utilisateur courant)
frontend/src/lib/risk.ts           questionnaire d'inscription, score, calcul, stockage par portefeuille
frontend/src/lib/publicProfile.ts  questionnaire public de l'accueil
frontend/src/pages/                Landing (accueil), Login, Register, Chat, Portfolio, Markets, Profile
```
