# AGENTS

Le contrat d'API et d'architecture du projet est dans `contract/knowledge-graph.yaml`.

Avant toute tâche, lis ce fichier en entier. Il décrit les services, les routes, les schémas, les tables, le stockage, les agents et les outils, et indique quel service appartient à quel agent (`owner_agent`).

- C'est la référence commune : respecte les routes, les schémas et les noms qu'il définit.
- Ne le modifie pas seul. Un changement de contrat se discute avec l'équipe avant d'être codé.
- Si ce que tu dois faire n'y figure pas, ou le contredit, signale-le au lieu d'inventer.

## Solution retenue

Lis ensuite `SOLUTION.md`. Il explique la solution retenue et les raisons de chaque décision : flux d'une session, rôle des agents et des modules, règles R1-R10, Knowledge Base réglementaire, méthodes de calcul, plan.

- Pour les noms (routes, schémas, champs), le contrat fait foi.
- Les décisions de la section « Ce qu'on a écarté » sont prises : ne les rouvre pas sans demande explicite.
- Le découpage du travail en chantiers est dans `docs/workstreams.md`.

## Commandes AWS et Terraform

Le projet utilise le compte AWS de l'événement, jamais un compte personnel. Ses identifiants sont dans `.aws-local/` (ignoré par git).

- Charge-les dans la même commande que tout appel `aws` ou `terraform` : `source scripts/aws-env.sh && aws ...`. Une variable chargée dans une commande précédente ne survit pas forcément à la suivante.
- Le script affiche l'identité active : elle doit se trouver dans le compte `058264316309` (utilisateur IAM `alphaforge-dev`, clé d'accès durable). Sinon, ou si `.aws-local/` est absent, arrête-toi et demande, au lieu d'utiliser un autre profil.
- Cette clé n'expire pas avant la suppression du compte. Si elle est refusée (`InvalidClientTokenId`, `AccessDenied`), demande à un humain : ne cherche pas d'autres identifiants.
- N'écris jamais d'identifiants ailleurs que dans `.aws-local/`, et jamais dans un fichier suivi par git.
- Ne lance pas `terraform apply` et ne crée, ne modifie ni ne supprime de ressource AWS sans demande explicite.

## Observabilité : Langfuse

Les traces des agents (Strands, via OpenTelemetry) partent vers le projet Langfuse de l'équipe : https://us.cloud.langfuse.com. Le code est dans `backend/agents/telemetry.py`. Il est **fail-open** : si Langfuse est absent ou mal configuré, les agents fonctionnent quand même, sans traces.

- **Pour lire ou interroger Langfuse** (traces, sessions, coûts, jeux d'évaluation), utilise le skill `.agents/skills/langfuse/SKILL.md`. Lis-le avant toute action. Il passe par `npx langfuse-cli` : commence par les commandes en lecture (`__schema`, `--help`, `list`, `get`), et ne crée ni ne modifie de données Langfuse sans demande explicite.
- **Clés :**
  - la clé publique (`LANGFUSE_PUBLIC_KEY`, `pk-lf-…`) n'est pas secrète ;
  - la **clé secrète** (`sk-lf-…`) ne va **jamais** dans un fichier suivi par git, ni dans `terraform.tfvars`, ni dans l'état Terraform. En local, elle est dans `.env` (ignoré par git). Sur AWS, elle est dans un paramètre SSM SecureString (`LANGFUSE_SECRET_PARAM`), créé hors Terraform et lu par la Lambda agents.
- **Contenu des traces :** Langfuse est un **outil de développement**, utilisé pendant la construction de l'outil pour l'améliorer. Les utilisateurs de l'application ne le consultent pas, et l'explicabilité affichée dans le front vient des événements `tool.call` du contrat, pas de Langfuse. Il reçoit le texte des prompts et des réponses : n'y envoie que des données fictives (personas, portefeuilles de démo), jamais de données personnelles réelles. La règle du contrat « jamais le texte des questions ou des réponses » vise les journaux CloudWatch (`observability`) de l'application, pas Langfuse. Décision prise ; la phrase correspondante sera ajoutée au contrat avec la prochaine proposition de changement.
- **Les traces n'existent qu'après déploiement** : Lambdas reconstruites, `terraform apply` (variables `LANGFUSE_*`, droit `ssm:GetParameter`) et paramètre SSM créé. En local, il suffit de `.env` (ex. `backend/agents/scripts/smoke.py`).
