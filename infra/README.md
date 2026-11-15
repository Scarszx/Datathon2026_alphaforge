# Infrastructure Grow (Terraform)

Décrit toute l'infrastructure du contrat v0.4.0 (`contract/knowledge-graph.yaml`) : Cognito, DynamoDB (dont `Analyses`), S3 (+ CloudFront pour le front), deux Lambdas, API Gateway HTTP API (17 routes), CloudWatch, Knowledge Base Bedrock (S3 Vectors) et Guardrail Bedrock. Prête pour un `terraform plan` — **jamais d'`apply` ici** : une seule personne le fera, après validation de l'équipe.

## Prérequis

- Terraform >= 1.5
- Python 3.12 avec `pip3` (pour `build_lambdas.sh`)
- Identifiants du compte d'événement, depuis le dépôt ou un worktree :
  `source scripts/aws-env.sh` (vérifier que le compte est `058264316309`)
- Accès réseau au registre Terraform pour `terraform init`

## Ordre des commandes

```bash
cd infra/terraform
terraform init                                  # télécharge le provider (sans credentials AWS)
terraform fmt -check -recursive                 # formatage
../scripts/build_lambdas.sh                     # construit build/api.zip et build/agents.zip
cp terraform.tfvars.example terraform.tfvars    # puis adapter (dataset_version, pandas_layer_arn)
terraform validate                              # passe aussi sans credentials ni zips
terraform plan                                  # humain, avec credentials (source scripts/aws-env.sh)
terraform apply                                 # une seule personne, après accord de l'équipe
../scripts/kb_sync.sh                           # corpus vers S3 + ingestion de la KB (à lancer tout de suite)
```

La KB et son magasin de vecteurs sont créés par le même `apply` que le reste (quelques secondes avec S3 Vectors). L'ingestion du corpus (`kb_sync.sh`) est l'étape la plus longue : la lancer juste après `apply`, avant les autres étapes manuelles.

Remarques :

- `terraform validate` passe **sans** identifiants AWS ni zips : aucune data source n'est évaluée par validate. En revanche `terraform plan` exige les zips de `build/` (lancer `build_lambdas.sh` avant).
- **`validate` ne remplace pas un `plan` réel** : il ne vérifie pas les appels de fonctions dans les `locals` ni le contenu des zips. Un `plan` (humain, avec credentials) reste obligatoire avant `apply`.
- Tant que `backend/api/app.py` et `backend/agents/app.py` n'existent pas (WS4, WS5), `build_lambdas.sh` produit des **zips factices** (le handler n'y est pas) et le contrôle `tickers.json` est reporté ; dès qu'il y a du code applicatif, le contrôle devient obligatoire. Le plan passe, la première invocation échouera jusqu'à l'arrivée du code réel.
- Le zip embarque l'arborescence `backend/` sans `__init__.py` dans `backend/` et `backend/common/` (namespace packages, conforme au socle WS0) ; le handler est donc bien `backend/api/app.handler`.

## Variables à adapter (`terraform.tfvars`)

| Variable | Rôle |
|---|---|
| `aws_region` | Région (défaut `us-east-1`) |
| `dataset_version` | Version du jeu de données téléversée sous `s3://<bucket>/dataset/<version>/` (obligatoire) |
| `pandas_layer_arn` | Couche AWS SDK for pandas, runtime Python 3.12, architecture arm64 |
| `model_orchestrator` / `model_auditor` / `model_writer` | Profils d'inférence Bedrock des 3 agents (défaut `global.anthropic.claude-opus-5-5`) |
| `kb_corpus_version` | Version du corpus sous `s3://<bucket>/kb/<version>/` (défaut `2026-11-14`)  ; seul ce préfixe est indexé |
| `embedding_model_id` / `embedding_dimensions` | Modèle d'embeddings de la KB (défaut `amazon.titan-embed-text-v2:0`, 1024 dimensions) |
| `cors_origins` | Origines du front en développement (l'URL CloudFront est ajoutée automatiquement) |

**Trouver la couche pandas** : console AWS Lambda → « Layers » → onglet *AWS layers*, runtime *Python 3.12*, architecture *arm64* (`AWSSDKPandas-Python312-Arm64`), ou la table des couches de la documentation AWS SDK for pandas. Format : `arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python312-Arm64:<version>`.

**Modèles Bedrock** : l'invocation `bedrock-runtime` exige un profil d'inférence (l'ID nu `anthropic.claude-opus-5-5` est refusé en on-demand). Le défaut `global.…` route vers n'importe quelle région au prix liste ; l'alternative `us.anthropic.claude-opus-5-5` reste US/Canada (+10 %). L'IAM autorise déjà profil et modèle de fondation.

## Knowledge Base réglementaire (`bedrock_kb.tf`)

- **Corpus** : même bucket que le jeu de données, préfixe `kb/<kb_corpus_version>/` (`storage-kb-corpus`). `kb_sync.sh` y copie `docs/for_KB/` (sans `README.md`), avec chaque `<fichier>.metadata.json`.
- **Métadonnées** : Bedrock lit les fichiers `.metadata.json` à l'ingestion. Les attributs `juridiction`, `regulateur`, `sujets`, `date_version`, `langue`, `type_document`, `source_url` et `date_recuperation` deviennent filtrables au `Retrieve` (ex. `juridiction` ∈ {`CA`, province}). Rien à déclarer dans Terraform.
- **Découpage** : passages fixes de 300 tokens, chevauchement de 20 %, pour des extraits courts dans les citations `KB-nn`.
- **Embeddings** : Titan Text Embeddings V2 (1024 dimensions), disponible en us-east-1.

### Choix du magasin de vecteurs : Amazon S3 Vectors

| Option | Création | Coût fixe | Terraform |
|---|---|---|---|
| **S3 Vectors (retenu)** | quelques secondes | aucun (paiement à l'usage) | complet (`aws_s3vectors_vector_bucket`, `aws_s3vectors_index`) |
| OpenSearch Serverless | 10 min et plus | OCU minimales facturées en continu | l'index vectoriel exige le provider `opensearch` ou une étape manuelle |
| Aurora pgvector | longue | cluster | schéma SQL à créer à la main |

C'est l'option la plus rapide à créer sur le compte d'atelier, sans étape manuelle (open_question du contrat). Contrainte : 2 Ko de métadonnées filtrables par vecteur. Le texte du passage (`AMAZON_BEDROCK_TEXT`) et le bloc interne de Bedrock (`AMAZON_BEDROCK_METADATA`) sont donc déclarés non filtrables. Les attributs du corpus, de l'ordre de 300 octets, restent filtrables.

## Guardrail (`guardrail.tf`)

- Sujets refusés : ordres de transaction, promesses ou garanties de rendement, recommandation personnalisée d'un titre. Leurs définitions excluent la simulation de portefeuille et la comparaison de catégories d'actifs, pour limiter les faux positifs.
- Renseignements personnels bloqués : numéros de carte, comptes et numéros d'acheminement bancaires, NAS, et numéro de compte bancaire canadien (regex transit-institution-compte).
- La version publiée (`aws_bedrock_guardrail_version`) est republiée à chaque modification du Guardrail. Les outputs `guardrail_id` et `guardrail_version` sont injectés dans la Lambda agents.

## Ce qui reste manuel après `apply`

0. Lancer `infra/scripts/kb_sync.sh` (corpus + ingestion), puis suivre le job avec la commande qu'il affiche (statut `COMPLETE`, aucun document en échec).
1. Modèles Bedrock : aucune activation manuelle. La page *Model access* est retirée : Bedrock active les modèles serverless (Claude Opus 5.5, Titan Text Embeddings V2) au premier appel. Pour Anthropic, une première utilisation sur un compte peut demander de décrire le cas d'usage ; Opus 5.5 est déjà testé sur ce compte.
2. Créer les comptes Cognito des personas : `admin-create-user` puis `admin-set-user-password` avec `--permanent` (contrat : srv-cognito.notes, pas de changement de mot de passe temporaire).
3. Exécuter l'ingestion (WS3) et téléverser le jeu de données : `data/output/<version>/` → `s3://<bucket>/dataset/<version>/` (bucket en output `dataset_bucket`).
4. Déposer le build du front dans `s3://<front bucket>/` (output `front_bucket`).

## Validation des tickers (Lambda API)

La Lambda API valide les tickers de `PUT holdings` avec une copie **embarquée** dans son zip : `backend/api/tickers.json` (contrat : srv-api-light.rules — « lecture S3 de ce seul fichier, ou copie embarquée »). Elle n'a donc **aucun droit S3**, et ses variables d'environnement ne contiennent ni `DATASET_BUCKET` ni `DATASET_VERSION`.

Cette liste est **figée au moment du build** : si l'univers d'actifs change (WS3), il faut régénérer `tickers.json` depuis `universe.parquet` et reconstruire le zip — `build_lambdas.sh` échoue si le fichier manque dès qu'il y a du code applicatif. La Lambda agents, elle, lit le bucket (`s3:GetObject` sur le préfixe du jeu de données), et ne lit pas le préfixe `kb/` : seule la KB y accède, avec son propre rôle de service.
