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
- Le script affiche le compte actif : il doit contenir `WSParticipantRole`. Sinon, ou si `.aws-local/` est absent, arrête-toi et demande, au lieu d'utiliser un autre profil.
- Si les identifiants ont expiré (`ExpiredToken`), demande à un humain de lancer `scripts/aws-refresh-creds.sh`.
- N'écris jamais d'identifiants ailleurs que dans `.aws-local/`, et jamais dans un fichier suivi par git.
- Ne lance pas `terraform apply` et ne crée, ne modifie ni ne supprime de ressource AWS sans demande explicite.
