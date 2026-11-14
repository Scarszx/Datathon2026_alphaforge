# AlphaForge — front (SPA)

Front du contrat d'API AlphaForge v0.3.0 (simulation seulement). Le front ne calcule rien : il affiche ce que renvoie `/v1/*`.

## Configuration
Copier `.env.example` en `.env` et renseigner :
- `VITE_API_BASE_URL` : URL d'API Gateway, sans `/v1`
- `VITE_COGNITO_REGION`, `VITE_COGNITO_CLIENT_ID` : user pool Cognito (client sans secret, flux `USER_PASSWORD_AUTH` activé)

```bash
npm install
npm run dev   # http://localhost:5173
```

## Pages
| Route | Contenu | API |
|---|---|---|
| `/login` | Connexion directe à Cognito | Cognito |
| `/portefeuille` | Résumé calculé par le back, édition des positions, autocomplétion de ticker | `/portfolios*`, `/market/search` |
| `/profil` | Profil investisseur | `/me`, `/me/profile` |

## Assistant (chat)
Bouton flottant présent sur toutes les pages connectées. Un clic ouvre le chat en plein écran, un second clic (ou `Échap`) le réduit. Historique, conversations épinglées (stockées dans le navigateur, l'API n'a pas ce champ), renommage et suppression. API : `/conversations*`.

## Organisation
```
src/api/types.ts      types des schémas du contrat
src/api/auth.ts       Cognito (jetons en sessionStorage, renouvellement)
src/api/client.ts     fetch + Bearer + erreurs au format schema-error
src/api/endpoints.ts  une fonction par route
src/lib/store.tsx     session (utilisateur courant)
```
