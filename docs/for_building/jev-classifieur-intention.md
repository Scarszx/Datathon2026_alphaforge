# Piste Jev (TypeSafe) pour le filtre d'entrée : ce qu'on a compris

Fiche de décision, rédigée le 2026-11-15 à partir de la documentation publique de Jev. **Rien n'est implémenté.** Elle sert si l'équipe décide de remplacer, ou de compléter, le contrôle par sujets du Bedrock Guardrail sur `english_request`.

Contexte du problème : le Guardrail Bedrock (version 2) bloque des phrases de simulation centrales qui contiennent un ticker, par exemple « What if I add 10% of XIU to my portfolio? » (voir « Limite connue » dans `docs/workstreams.md`, section Intégration). Un classificateur de sujets sémantique y est trop sensible aux exemples interdits.

## En bref

| | |
|---|---|
| Ce que c'est | Un « modèle de décision » (TypeSafe, catégorie « System One »). On lui envoie un texte et des questions typées, il répond par une option ou une probabilité. Il ne génère pas de texte et ne donne pas ses raisons. |
| Accès | Via OpenRouter, une clé API suffit. Point d'entrée **alpha** : `POST https://openrouter.ai/api/alpha/decisions` (« la forme peut changer »). Early access depuis le 2026-09-15 ; Jev 1.14 est sorti le 2026-10-14. |
| Identifiants de modèle | `typesafe/jev-1.14` (figé), `typesafe/jev-1.13` (encore disponible), `~typesafe/jev-latest` (alias mobile). |
| Prix | 0,042 $ par million de tokens d'entrée, sortie gratuite (« peut changer à tout moment »). |
| Taille | Contexte de 262 144 tokens ; en mode normal, 64 k tokens par requête, 32 k pour l'état plus la plus longue question. Au-delà (et pour les images), mode « long contexte », plus lent et moins précis. |

## Les primitives

| Primitive | Réponse | Ce qui nous intéresse |
|---|---|---|
| **Noul** | `noul` : probabilité (0 à 1) que l'énoncé soit vrai | Une question oui/non. **Pas de champ `confidence`** : la probabilité porte déjà l'incertitude. |
| **Choice** | `choice` (option retenue), `probabilities` (par option), `confidence` | Une option parmi un ensemble fermé (jusqu'à 255 d'après un tiers, non confirmé par la doc officielle). La réponse est toujours l'une de nos options. |
| **Score** | `score`, `probabilities`, `confidence`, `legend` | Niveaux ordonnés (10 au plus). Peu utile ici. |
| **Box** | cadre dans une image | Hors sujet. |

Les questions d'une même requête sont évaluées **en parallèle et indépendamment** : elles ne se voient pas entre elles.

### Forme d'un appel (adaptée de la documentation, non testée)

```json
{
  "model": "typesafe/jev-1.14",
  "state": "What if I add 10% of XIU to my portfolio?",
  "questions": {
    "intent": {
      "type": "choice",
      "instructions": "What does the user want the assistant to do?",
      "criteria": {
        "simulation": "Analyze or simulate the effect of a hypothetical change on a fictional portfolio.",
        "trade_order": "Execute a real buy, sell or transfer order.",
        "return_promise": "Guarantee or predict a specific future return.",
        "personal_advice": "Say which specific security to buy, sell or hold.",
        "other": "None of the above."
      }
    },
    "asks_real_order": { "type": "noul", "instructions": "Does the message ask the assistant to place or execute a real buy, sell or transfer order?" },
    "asks_return_guarantee": { "type": "noul", "instructions": "Does the message ask the assistant to guarantee or promise a specific future return?" },
    "asks_personal_advice": { "type": "noul", "instructions": "Does the message ask the assistant to tell the user which specific security to buy, sell or hold?" }
  }
}
```

Réponse attendue (forme documentée) :

```json
{
  "id": "…", "model": "typesafe/jev-1.14-<date>", "provider": "…",
  "answers": {
    "intent": { "type": "choice", "choice": "simulation", "probabilities": { "simulation": 0.97, "…": 0.01 }, "confidence": 0.96 },
    "asks_real_order": { "type": "noul", "noul": 0.02 }
  },
  "usage": { "input_tokens": 0, "output_tokens": 0, "cost": 0 }
}
```

Une réponse peut aussi être de type `refusal` (pas de valeur) : les autres réponses de la même requête restent valides. À gérer.

## Chiffres relevés (et leur provenance)

- **Latence** : médiane 194 ms pour Jev 1.13 sur un triage de 60 tickets (article d'OpenRouter ; une seule journée, un seul jeu de consignes). La fiche de la piste 5 parlait de 70 à 500 ms : ordre de grandeur plausible, mais notre mesure fera foi.
- **Coût par message** : un appel de trois questions de 447 tokens d'entrée a coûté 0,000019 $. La fiche de la piste 5 parlait de 0,000003 $ : c'est probablement trop bas, compter **de l'ordre de 0,00001 à 0,00003 $** par message. Négligeable de toute façon.
- **Précision** : sur 40 messages d'injection de consigne, 40 sur 40, avec des scores de 0,86 à 0,99 pour les injections et 0,01 à 0,20 pour les messages ordinaires. **Petit échantillon**, à ne pas extrapoler.
- **Étalonnage** : TypeSafe affirme que les probabilités sont étalonnées en moyenne (un 0,8 est juste environ 8 fois sur 10), pas message par message.

## Ce que la documentation dit sur les limites (« model jaggedness »)

- **L'ordre des options compte** : « Jev penche vers la première option ». Il faut réordonner les options et vérifier que la réponse ne change pas. (La fiche de la piste 5 le notait déjà.)
- **Il répond à la question écrite, pas à celle qu'on voulait poser** : négations, conditions implicites et portées sont lues littéralement. Pas de double négation, pas de `true` qui veut dire non.
- **Le bruit nuit** : plus l'état contient de contenu sans rapport avec la décision, moins il est précis. Pour nous, l'état serait seulement l'`english_request`, donc court.
- **Chiffres, dates, comparaisons** : à faire en code, pas par Jev.
- **Texte adverse** : l'état n'est pas traité comme hostile ; un texte injecté peut déplacer les réponses.
- **Non couvert par la doc** : performance en français ou dans d'autres langues, biais, stabilité d'une exécution à l'autre. À mesurer nous-mêmes. Dans notre cas le module lirait l'**anglais** (la traduction produite par l'orchestrateur), ce qui évite en partie la question, mais pas la qualité de la traduction.

## Seuils : ce que recommande TypeSafe

- Sur un Noul, **seuiller la probabilité elle-même**. Points de départ : **0,7** (oui) et **0,3** (non), la zone entre les deux recevant sa propre issue (relecture).
- Les seuils doivent croître avec le risque de l'action (exemple de la doc : 0,5 en général, 0,9 avant une opération destructrice).
- Sur un Choice, seuiller la probabilité de l'option sur laquelle le code agit, pas la `confidence` (pour un ensemble fixe, c'est une simple transformation de la probabilité maximale). Une probabilité de 0,5 est faible avec 2 options et forte avec 10 : fixer le seuil question par question.
- La doc ne donne **pas** de valeurs universelles : « les bons seuils dépendent du domaine et du modèle ». Il faut 100 à 200 exemples étiquetés, balayer les seuils (par exemple de 0,3 à 0,9) et lire précision et rappel par question. Un Noul dont la précision reste basse à tous les seuils est une question mal posée : à reformuler.
- La recette officielle « Guardrails for LLMs » (docs.typesafe.ai/cookbooks/llm_guardrails) filtre les entrées et les sorties avec une batterie de Noul plus un Score de gravité, et des politiques « strict » (relecture ≥ 0,35, action ≥ 0,70) et « permissive » (≥ 0,70 et ≥ 0,85). Elle **ne publie ni précision, ni latence, ni coût** et n'explique pas la dérivation des seuils.
- Motifs utiles : **« Noul d'abord »** (un contrôle bon marché avant une étape coûteuse) et **« Noul compagnon »** (détecter quand aucune option du Choice ne convient). Ajouter une option `other` à tout Choice.

## Esquisse d'intégration dans Grow

- **Où** : en remplacement du contrôle **par sujets** du point ② (`english_request`), dans `backend/agents/routes/messages.py`. Le Guardrail Bedrock resterait pour les renseignements bancaires (PII) et pour les sorties (③ et ④). Cela garde AWS dans le dispositif, ce qui compte pour la condition d'admissibilité et la grille (« Intégration AWS »).
- **Ce qui change pour le point ①** : le texte d'origine ne serait plus bloqué par sujet, seulement par PII. L'orchestrateur lirait donc un message non filtré par sujet ; ses outils sont en lecture seule (profil, portefeuille, recherche d'actifs, validation de brouillon), le risque est faible mais à noter.
- **Questions** : un Choice d'intention (`simulation` en premier, pour que l'option biaisée par l'ordre soit la plus sûre, puis un test d'ordre inversé) et trois Noul (ordre réel, promesse de rendement, conseil personnalisé). Une phrase par question, sans négation.
- **Décision en code** : blocage si une probabilité d'interdit dépasse le seuil haut ; passage si toutes sont sous le seuil bas ; entre les deux, **passage avec journalisation** (le pire échec pour la démo est de refuser une simulation légitime). Seuils ajustés sur un banc étiqueté.
- **Panne** : même politique que Bedrock aujourd'hui, ouverture en cas de panne (journalisée sans le texte), avec les nouvelles tentatives que préconise la doc de la recette (429, 5xx, et le 402 « budget en vol »). Un autre 402 signifie plus de crédit : à surveiller.
- **Secret** : la clé OpenRouter dans un paramètre SSM SecureString lu par la Lambda agents (même schéma que la clé Langfuse), jamais dans git ni dans Terraform. En local, dans `.env`.
- **Confidentialité** : n'envoyer que l'`english_request`, jamais d'identifiant, et ne pas renseigner `user` ni `session_id` (champs facultatifs de l'API). Le routage OpenRouter accepte `provider.data_collection: "deny"` et `provider.zdr`, mais **rien ne garantit qu'un fournisseur de Jev les honore** : à tester. TypeSafe dit s'engager à ne pas entraîner de modèle sur les données des utilisateurs et propose le « zero data retention » aux clients entreprise. Données fictives uniquement, comme pour Langfuse.
- **Contrat** : nouvelle source externe, nouveau garde-fou, et la description de `srv-bedrock-guardrails` à réécrire (« ordres, promesses, conseil » ne viendraient plus de Bedrock). Cela passe par une proposition à valider par l'équipe (`AGENTS.md`).

## Différences avec la fiche de la piste 5

| Fiche | Constaté dans la documentation |
|---|---|
| 70 à 500 ms | médiane de 194 ms mesurée ailleurs (Jev 1.13) : à mesurer chez nous |
| environ 0,000003 $ par message | plutôt 0,00001 à 0,00003 $ pour trois questions et un court texte |
| « indépendant d'AWS (survit à la suppression du compte) » | vrai pour le service, mais notre Lambda disparaît lundi soir avec le compte : l'argument ne vaut que pour une exécution hors AWS |
| « early access » | confirmé, et le point d'entrée est en alpha : la forme de l'API peut changer |
| « l'ordre des options fait bouger les probabilités » | confirmé (« penche vers la première option ») |
| politique de données « à confirmer » | seulement des engagements généraux ; ZDR pour les entreprises ; rien sur les régions |

## Questions ouvertes avant de décider

1. **Disponibilité réelle** : un résumé de recherche indique que Jev 1.14 n'est pas disponible via le routage intra-UE d'OpenRouter. Non vérifié sur la page du modèle (elle ne s'est pas chargée). À confirmer, par exemple par un appel d'essai.
2. **Stabilité** : à mesurer en relançant un banc plusieurs fois (TypeSafe propose un cookbook de « self-consistency » pour les décisions de modération). Figer `typesafe/jev-1.14` plutôt que `~typesafe/jev-latest`.
3. **Qualité sur nos phrases** : le banc actuel `GUARDRAIL_CASES` n'a que 5 cas. Il faut un jeu étiqueté d'au moins 100 phrases (simulations avec tickers, « et si… », comparaisons, vraies demandes d'ordre, promesses, conseils, cas limites), en anglais et en traductions françaises.
4. **Compte OpenRouter** : une carte ou des crédits, et la clé. Le compte AWS étant supprimé lundi soir, la démo doit être enregistrée avant.
5. **Délai** : calibration et intégration représentent une demi-journée à une journée de travail, pour un résultat qui reste à prouver. La correction de l'autre agent (exemples sans tickers, `ws/guardrail-topics`) coûte beaucoup moins : à comparer d'abord.

## Plan d'essai minimal, sans toucher au code de production

1. Écrire le jeu étiqueté (100 phrases) dans un fichier de test.
2. Un script jetable envoie chaque phrase avec les quatre questions, en deux ordres d'options, trois fois.
3. Mesurer faux positifs sur les simulations, faux négatifs sur les interdits, stabilité entre exécutions et latence.
4. Balayer les seuils, choisir, puis décider.

## Sources (lues le 2026-11-15)

- Guide OpenRouter : https://openrouter.ai/docs/guides/community/jev
- Tutoriel OpenRouter : https://openrouter.ai/docs/guides/community/jev-tutorial
- Référence de l'API : https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request
- Recette de classification : https://openrouter.ai/docs/cookbook/evaluate-and-optimize/jev-classification
- Articles OpenRouter : https://openrouter.ai/blog/insights/what-is-jev/ et https://openrouter.ai/blog/tutorials/jev-vs-llm-when-to-use-each/
- Documentation TypeSafe : https://docs.typesafe.ai (pages Confidence, Model jaggedness, Legal, recette « Guardrails for LLMs »)
- Le lien fourni (`https://openrouter.ai/typesafe/jev-1.14#documentation`) renvoyait une erreur 404 au moment de la lecture ; le contenu a été lu via les pages ci-dessus.
