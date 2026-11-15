# NOTES WS1b (infra v0.4)

Hypothèses et écarts trouvés en mettant l'infra au niveau du contrat v0.4.0.

## Décisions prises avec l'équipe

- **Magasin de vecteurs : S3 Vectors.** Il répond à l'open_question du contrat. La justification est dans `infra/README.md`.
- **Complétion asynchrone d'un run (décision WS5, à appliquer).** Le statement `SelfInvokeCompleteRun` (`iam.tf`) autorise `lambda:InvokeFunction` sur l'ARN construit de la Lambda agents (pas de cycle), et son timeout passe à 180 s (`lambda.tf`). L'API Gateway coupe toujours à 30 s : seules les invocations internes (`InvocationType=Event`) profitent des 180 s. **À appliquer par un `terraform plan` puis `apply` de l'équipe** (non lancé).

## Écarts et points à suivre

- **`MODEL_ANALYST` et `MODEL_GOVERNANCE` retirés de l'infra.** Les variables Terraform sont remplacées par `model_auditor` et `model_writer`. Les fonctions dépréciées `model_analyst()` et `model_governance()` ont été retirées de `backend/common/config.py` sur `main` après la fusion.
- **`date_recuperation`** figure dans les `.metadata.json` et dans le contrat (`storage-kb-corpus`), mais pas dans la liste d'attributs du chantier WS1b. Il est ingéré comme les autres, rien à faire.
- **Faux positifs du Guardrail à tester tôt** (SOLUTION.md 7.6), en particulier :
  - le sujet « Personalized investment recommendation » face à une demande de simulation (« what if I add 10 % XIU ») ;
  - le détecteur `US_BANK_ACCOUNT_NUMBER` face aux nombres des explications. Si la sortie est bloquée à tort, passer ce détecteur en `ANONYMIZE` ou le désactiver en sortie (`output_enabled = false`).
- **Pas de filtre `PROMPT_ATTACK`** dans le Guardrail : la liste du chantier ne le demande pas. Il pourrait servir contre les injections venues des outils et de la KB, mais il risque des faux positifs. À discuter.
- **Propagation IAM :** la création de la KB vérifie les droits de son rôle. Si `apply` échoue sur la KB juste après la création du rôle, relancer `apply`.
- **`data_deletion_policy = RETAIN`** sur la source de données : un `destroy` ne dépend pas de l'index. Les vecteurs disparaissent de toute façon avec l'index (`force_destroy`).
- **Existant, hors périmètre WS1b :** la ressource `DatasetRead` de la Lambda agents vaut `.../dataset/*/*` (`dataset_prefix_arn` se termine déjà par `/*`). C'est fonctionnel, car tous les objets sont sous `dataset/<version>/`, mais c'est redondant. Laissé tel quel.
