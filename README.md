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
