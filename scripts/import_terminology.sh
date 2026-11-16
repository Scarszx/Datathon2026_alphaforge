#!/usr/bin/env bash
# Importe (ou remplace) la terminologie Amazon Translate « grow-finance-en-fr » dans le compte de l'événement.
# À lancer par un humain, une fois : sans elle, la traduction du run fonctionne, avec un vocabulaire moins juste.
#   scripts/import_terminology.sh
# Nom différent : TRANSLATE_TERMINOLOGY=autre-nom scripts/import_terminology.sh (même valeur dans la Lambda agents).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
csv="$here/../backend/agents/translate/terminology/grow-finance-en-fr.csv"
name="${TRANSLATE_TERMINOLOGY:-grow-finance-en-fr}"

# Identifiants du compte de l'événement (affiche l'identité : doit être le compte 058264316309).
source "$here/aws-env.sh"

aws translate import-terminology \
  --region us-east-1 \
  --name "$name" \
  --merge-strategy OVERWRITE \
  --description "Vocabulaire financier de Grow (en vers fr-CA), non relu par un spécialiste" \
  --terminology-data "Format=CSV,Directionality=UNI" \
  --data-file "fileb://$csv"

aws translate get-terminology --region us-east-1 --name "$name" \
  --query 'TerminologyProperties.{Name:Name,Terms:TermCount,Source:SourceLanguageCode,Targets:TargetLanguageCodes}'
