#!/usr/bin/env bash
# Met à jour .aws-local/credentials quand les identifiants temporaires expirent.
# Usage : dans CloudShell, lancer `aws configure export-credentials --format env`,
# copier les lignes export, puis : scripts/aws-refresh-creds.sh  (coller, puis Ctrl-D)
set -euo pipefail
root="$(cd "$(git -C "$(dirname "$0")" rev-parse --path-format=absolute --git-common-dir)/.." && pwd)"
input="$(cat)"
get() { printf '%s\n' "$input" | sed -n "s/^export $1=//p" | tr -d '"' | head -n1; }
key="$(get AWS_ACCESS_KEY_ID)"; secret="$(get AWS_SECRET_ACCESS_KEY)"; token="$(get AWS_SESSION_TOKEN)"
[[ -n "$key" && -n "$secret" && -n "$token" ]] || { echo "Lignes export incomplètes." >&2; exit 1; }
umask 077
mkdir -p "$root/.aws-local"
printf '[alphaforge]\naws_access_key_id = %s\naws_secret_access_key = %s\naws_session_token = %s\n' \
  "$key" "$secret" "$token" > "$root/.aws-local/credentials"
echo "Identifiants mis à jour. Expiration : $(get AWS_CREDENTIAL_EXPIRATION)"
