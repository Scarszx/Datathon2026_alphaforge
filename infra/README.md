# Infrastructure AlphaForge (Terraform)

Décrit toute l'infrastructure du contrat (`contract/knowledge-graph.yaml`) : Cognito, DynamoDB, S3 (+ CloudFront pour le front), deux Lambdas, API Gateway HTTP API, CloudWatch. Prête pour un `terraform plan` — **jamais d'`apply` ici** : une seule personne le fera, après validation de l'équipe.

## Prérequis

- Terraform >= 1.5
- Python 3.12 avec `pip3` (pour `build_lambdas.sh`)
- Identifiants du compte d'événement, depuis le dépôt ou un worktree :
  `source scripts/aws-env.sh` (vérifier que l'identité contient `WSParticipantRole`)
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
```

Remarques :

- `terraform validate` passe **sans** identifiants AWS ni zips : aucune data source n'est évaluée par validate. En revanche `terraform plan` exige les zips de `build/` (lanter `build_lambdas.sh` avant).
- Tant que `backend/api/app.py` et `backend/agents/app.py` n'existent pas (WS4, WS5), `build_lambdas.sh` produit des **zips factices** (le handler n'y est pas). Le plan passe, la première invocation échouera jusqu'à l'arrivée du code réel.
- Le zip embarque l'arborescence `backend/` sans `__init__.py` dans `backend/` et `backend/common/` (namespace packages, conforme au socle WS0) ; le handler est donc bien `backend/api/app.handler`.

## Variables à adapter (`terraform.tfvars`)

| Variable | Rôle |
|---|---|
| `aws_region` | Région (défaut `us-east-1`) |
| `dataset_version` | Version du jeu de données téléversée sous `s3://<bucket>/dataset/<version>/` (obligatoire) |
| `pandas_layer_arn` | Couche AWS SDK for pandas, runtime Python 3.12, architecture arm64 |
| `model_orchestrator` / `model_analyst` / `model_governance` | Profils d'inférence Bedrock (défaut `global.anthropic.claude-sonnet-5-5`) |
| `cors_origins` | Origines du front en développement (l'URL CloudFront est ajoutée automatiquement) |

**Trouver la couche pandas** : console AWS Lambda → « Layers » → onglet *AWS layers*, runtime *Python 3.12*, architecture *arm64* (`AWSSDKPandas-Python312-Arm64`), ou la table des couches de la documentation AWS SDK for pandas. Format : `arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python312-Arm64:<version>`.

**Modèles Bedrock** : l'invocation `bedrock-runtime` exige un profil d'inférence (l'ID nu `anthropic.claude-sonnet-5-5` est refusé en on-demand). Le défaut `global.…` route vers n'importe quelle région au prix liste ; l'alternative `us.anthropic.claude-sonnet-5-5` reste US/Canada (+10 %). L'IAM autorise déjà profil et modèle de fondation.

## Ce qui reste manuel après `apply`

1. Activer l'accès aux modèles Bedrock (console → Bedrock → *Model access*) pour le profil choisi.
2. Créer les comptes Cognito des personas : `admin-create-user` puis `admin-set-user-password` avec `--permanent` (contrat : srv-cognito.notes, pas de changement de mot de passe temporaire).
3. Exécuter l'ingestion (WS3) et téléverser le jeu de données : `data/output/<version>/` → `s3://<bucket>/dataset/<version>/` (bucket en output `dataset_bucket`).
4. Déposer le build du front dans `s3://<front bucket>/` (output `front_bucket`).

## Écart documenté au doc WS1

Le doc WS1 prévoit « Lambda API = tables seulement », mais le contrat exige que `PUT holdings` valide chaque ticker contre `universe.parquet` (lecture S3 de ce seul fichier). Décision de l'équipe : respecter le contrat → la Lambda API a `s3:GetObject` restreint à `dataset/*/universe.parquet`. À re-discuter si le front valide lui-même les tickers.
