# Front (SPA) — chantier WS6

SPA React + Vite du contrat AlphaForge v0.4.0 (simulation seulement : aucune transaction réelle, aucun conseil financier).

Le front ne calcule rien : il consomme l'API Gateway (Bearer Cognito) et affiche les chiffres du back
(registre de preuves d'un run, `/summary`). Les instructions de lancement sont dans le `README.md` de la racine,
section « Front (SPA) ».

```bash
npm install
npm run dev:demo     # mode démo, sans Cognito ni API
npm run build        # fichiers statiques dans dist/ (déploiement S3 + CloudFront)
npm test             # tests de composants (Vitest)
```

Pages : `/login`, `/chat` (session en 3 colonnes), `/portefeuille`, plus `/marches` et `/profil` (via l'API).

Écarts du chantier, hypothèses du mode démo et points à trancher à l'intégration : `NOTES-frontend.md`.
