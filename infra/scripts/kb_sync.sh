#!/usr/bin/env bash
# job-kb-sync (contrat v0.4.0) : envoie le corpus réglementaire docs/for_KB/
# (documents + .metadata.json) vers s3://<bucket>/kb/<version>/, puis lance
# l'ingestion de la Knowledge Base. À relancer après chaque modification du corpus.
#
# Usage (humain, après terraform apply, depuis le dépôt ou un worktree) :
#   infra/scripts/kb_sync.sh
# Les valeurs viennent des outputs Terraform (état local de la personne qui a
# fait apply). Surcharges possibles : DATASET_BUCKET, KB_ID, KB_DATA_SOURCE_ID,
# KB_PREFIX, AWS_REGION.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
tf_dir="$repo_root/infra/terraform"
corpus_dir="$repo_root/docs/for_KB"

# Identifiants du compte de l'événement (jamais un compte personnel).
# shellcheck source=/dev/null
source "$repo_root/scripts/aws-env.sh"
identity="$(aws sts get-caller-identity --query Arn --output text)"
if [[ "$identity" != *:058264316309:* ]]; then
    echo "Identité inattendue : $identity (compte 058264316309 attendu). Arrêt." >&2
    exit 1
fi

tf_out() { terraform -chdir="$tf_dir" output -raw "$1"; }

bucket="${DATASET_BUCKET:-$(tf_out dataset_bucket)}"
kb_id="${KB_ID:-$(tf_out kb_id)}"
ds_id="${KB_DATA_SOURCE_ID:-$(tf_out kb_data_source_id)}"
prefix="${KB_PREFIX:-$(tf_out kb_corpus_prefix)}"   # kb/<version>/

if [[ ! -d "$corpus_dir" ]]; then
    echo "Corpus absent : $corpus_dir" >&2
    exit 1
fi

region="${AWS_REGION:-us-east-1}"   # contrat v0.4.0 : tout en us-east-1

echo "Corpus : $corpus_dir -> s3://$bucket/$prefix"
# README.md décrit le corpus mais n'en fait pas partie.
aws s3 sync "$corpus_dir/" "s3://$bucket/$prefix" \
    --exclude "README.md" --delete --region "$region"

echo "Ingestion : KB $kb_id, source $ds_id"
job_id="$(aws bedrock-agent start-ingestion-job \
    --knowledge-base-id "$kb_id" --data-source-id "$ds_id" \
    --region "$region" \
    --query ingestionJob.ingestionJobId --output text)"

echo "Job lancé : $job_id"
echo "Suivi :"
echo "  aws bedrock-agent get-ingestion-job --knowledge-base-id $kb_id --data-source-id $ds_id --ingestion-job-id $job_id --region $region --query 'ingestionJob.[status,statistics]'"
