# Portefeuille — prototype local

Prototype front-end du tableau de bord d'investissement (même style blanc/rouge que `bnc-portefeuille.zip`),
avec assistant IA simulé, questionnaire de profil de risque et ordres d'achat/vente **simulés**.
Tout tourne dans le navigateur : **aucune base de données, aucun serveur, aucune clé d'API**.

## Lancer

```bash
npm install
npm run dev        # http://localhost:5173
```

Compte démo : `demo@example.com` / `demo1234` (ou créez un compte; il reçoit 10 000 $ simulés).
Bouton « Réinitialiser la démo » en bas du tableau de bord pour tout remettre à zéro.

## Ce qui est inclus

| Zone | Route |
|---|---|
| Page d'accueil + questionnaire public (sans compte) | `/` |
| Connexion / mot de passe oublié (simulé) | `/connexion`, `/mot-de-passe-oublie` |
| Inscription + questionnaire de profil | `/inscription` |
| Tableau de bord (style du ZIP) + assistant flottant + ordre | `/tableau-de-bord` |
| Profil de risque (consulter / modifier) | `/profil` |

## Organisation

```
src/
  styles.css          # globals.css du ZIP (inchangé) + section « AJOUTS »
  lib/format.ts       # copie du ZIP          components/Chart.tsx  # copie du ZIP
  lib/market.ts       # actifs et prix FICTIFS, historique simulé
  lib/profile.ts      # questions + score de risque
  lib/portfolio.ts    # valeur, répartition, rendement, risque
  lib/trading.ts      # aperçu / exécution / annulation d'ordres (logique pure)
  lib/store.tsx       # « fausse API » : localStorage (utilisateurs, portefeuille, chats)
  agent/agent.ts      # agent simulé : registre d'outils → plan → exécution → réponse
  components/, pages/
```

`lib/store.tsx` est la seule couche à remplacer par des appels REST quand l'API Node + PostgreSQL existera;
`lib/trading.ts`, `lib/portfolio.ts`, `lib/profile.ts` et `agent/agent.ts` sont portables tels quels (ou en Python pour l'agent).

## Non implémenté

API Node/Express, PostgreSQL/Prisma, service Python FastAPI, Docker, vraie authentification, vrais cours de marché,
LLM réel, page détaillée d'un titre, tests automatisés, déploiement AWS.
