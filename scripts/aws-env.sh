# À charger dans le shell : source scripts/aws-env.sh
# Fait utiliser à aws et terraform les identifiants du compte de l'événement
# (fichiers .aws-local/, ignorés par git) au lieu du compte personnel.
# Dépôt principal, même depuis un worktree (les identifiants ne sont pas copiés dans les worktrees).
_repo_root="$(cd "$(git -C "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" rev-parse --path-format=absolute --git-common-dir)/.." && pwd)"
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
export AWS_CONFIG_FILE="$_repo_root/.aws-local/config"
export AWS_SHARED_CREDENTIALS_FILE="$_repo_root/.aws-local/credentials"
export AWS_PROFILE=alphaforge
unset _repo_root
aws sts get-caller-identity --query Arn --output text
