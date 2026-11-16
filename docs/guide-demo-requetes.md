# Guide de démo : requêtes qui fonctionnent

> Pour la personne qui fait la simulation devant le jury. Chaque requête se copie-colle telle quelle dans le chat.
> Sources : 204 requêtes réelles tracées dans Langfuse (15 et 16 novembre 2026), dont 161 réussies,
> et un test du Guardrail en production (version 4) sur chaque requête composée.

| Repère | Signification |
|---|---|
| ✅ **Testée** | Envoyée telle quelle en production, réponse correcte (durée observée indiquée). |
| 🧪 **Composée** | Assemblée à partir de formulations qui ont marché. Le Guardrail la laisse passer (testé le 16 novembre), mais elle n'a pas été jouée de bout en bout : à essayer une fois avant la démo. |
| ⛔ **À éviter** | A échoué dans l'historique (refus du Guardrail, réponse masquée ou délai dépassé). |

---

## 0. Avant de commencer (important)

### ⚠️ Les comptes de démo n'ont plus de profil

Les profils investisseurs de **tous** les comptes ont été supprimés le 15 novembre (passage aux industries du jeu de données).
`robert`, `amira` et `mateo` existent toujours, avec leurs portefeuilles, mais **sans profil**. Conséquences :

- **À la connexion, l'application affiche le questionnaire.** S'il est rempli, elle **construit un portefeuille et remplace celui du compte, sans demander de confirmation**.
  C'est probablement ce qui est arrivé à `amira` : son portefeuille est maintenant un portefeuille construit de 54 actions américaines.
- **Dans le chat, l'agent demande la capacité de risque** s'il ne la trouve pas dans le profil. Les requêtes 🧪 ci-dessous donnent donc toujours
  la tolérance, la capacité et l'horizon : elles marchent avec ou sans profil.

**À faire avant la démo (une seule des deux options) :**

1. **Restaurer les personas**, de préférence. Depuis la racine du dépôt :
   `source scripts/aws-env.sh && .venv/bin/python scripts/seed_personas.py robert amira mateo`.
   Cette commande remet les profils et les portefeuilles d'origine (celui d'`amira` compris).
2. **Ou créer un compte neuf** et montrer l'onboarding (section 1). C'est une bonne ouverture de démo.

| Persona (après restauration) | Portefeuille | Profil |
|---|---|---|
| **robert** | XIU.TO, RY.TO, TD.TO, XBB.TO, ZST.TO | Québec, retraite proche, horizon 3 à 5 ans, tolérance 3, pas de crypto |
| **amira** | XIC.TO, XIU.TO, SHOP.TO, VFV.TO, BTC-USD | Ontario, croissance, horizon 15 ans et plus, tolérance 5, capacité 4 |
| **mateo** | XESG.TO, XIC.TO, VFV.TO, XEF.TO, XBB.TO | Québec, croissance modérée, préférence ESG, tolérance 3, capacité 3 |

### Comment se déroule une simulation

1. Vous envoyez une requête. L'agent répond en 5 à 20 s et propose un **mandat** (une carte avec les paramètres).
2. Vous cliquez sur **Confirmer**. Les chiffres et les verdicts R1 à R10 s'affichent en environ 5 s.
3. Le récit explicatif arrive ensuite en arrière-plan : 12 à 15 s en anglais, un peu plus en français.
4. Les questions de suivi (« pourquoi… », « d'où vient KB-02 ? ») répondent en 5 à 15 s.

**Règles d'or :**
- Un seul message à la fois : attendez la réponse.
- Donnez un **montant en dollars**, pas un pourcentage.
- Nommez un **titre précis** (XIU.TO, NVDA…).
- Pour les industries, mettez le **nom anglais du jeu entre parenthèses** : l'agent le reprend alors sans hésiter.
- Le premier message après une pause peut prendre environ 5 s de plus (démarrage à froid).

---

## 1. Ouverture : le premier portefeuille, sans chat (compte neuf)

Créez un compte, remplissez le questionnaire (profil de risque, horizon, montant fictif, par exemple 50 000 $),
et cherchez 1 ou 2 industries dans les champs « j'aime » et « j'évite » (par exemple « semi », « tabac »).
Le portefeuille est construit et affiché en **5 à 10 s**, sans passer par le chat. Mesuré le 16 novembre : `POST /runs` en 4,6 s à chaud.

---

## 2. Découvrir l'outil

✅ Testée (4 à 7 s)
```text
a quoi tu sers ?
```

✅ Testée (5 s)
```text
how can you help me?
```

✅ Testée (9,6 s)
```text
quelle est la différence entre risque et capacité de risque ?
```

✅ Testée (4,3 s)
```text
Qu'est-ce que la diversification ?
```

🧪 Composée
```text
Quelle est la différence entre ma tolérance au risque et ma capacité de risque, et laquelle la simulation retient-elle ?
```

---

## 3. Tester une idée sur le portefeuille existant

### Scénario vedette : Robert et son condo (à jouer dans l'ordre)

✅ Testée (11,1 s)
```text
Et si j'ajoutais 15 000 $ CAD de NVDA à mon portefeuille ?
```
✅ Testée (12,4 s) : si l'agent demande la capacité
```text
Ma capacité est de niveau 1. Propose le mandat.
```
→ **Confirmer**, puis :

✅ Testée (14,6 s)
```text
Pourquoi le scénario 1 échoue-t-il ?
```
✅ Testée (6,3 s) : remplacez le numéro par une citation affichée
```text
D'où vient KB-01 ?
```

🧪 **Version en un seul message** (Guardrail OK) :
```text
Et si j'ajoutais 15 000 $ CAD de NVDA à mon portefeuille ? C'est pour un condo dans 3 ans, et je ne peux pas me permettre de grosses pertes : capacité de niveau 1.
```
🧪 Puis, après Confirmer :
```text
Pourquoi le scénario 1 échoue-t-il ? Explique chaque règle déclenchée et cite le texte réglementaire.
```

### Autres idées

✅ Testée (10,4 s)
```text
What if I put 20,000 CAD into TSLA? I want to buy a condo in 3 years.
```

✅ Testée (8,4 s)
```text
Et si j'ajoutais 20 000 $ CAD de bitcoin (BTC-USD) ?
```
🧪 Version complète
```text
Et si j'ajoutais 20 000 $ CAD de bitcoin (BTC-USD) ? Horizon 5 ans, tolérance 4, capacité 2.
```

✅ Testée (8,2 s), sur le portefeuille d'Amira
```text
et si j'enlevais SHOP.TO ?
```

🧪 Composée : échange d'un titre contre un autre (portefeuille de Robert ou de Mateo)
```text
Et si je retirais complètement XBB.TO pour mettre 20 000 $ CAD de XIU.TO à la place ? Horizon 10 ans, tolérance 3, capacité 3.
```

✅ Testée (7,9 s)
```text
Diagnostique SHOP.TO dans mon portefeuille.
```
🧪 Version complète
```text
Diagnostique SHOP.TO dans mon portefeuille, avec un horizon de 8 ans et une capacité de niveau 2.
```

### Scénario ESG : Mateo et XOM (à jouer dans l'ordre)

✅ Testée (9 s)
```text
Et si j'ajoutais 10 000 $ CAD de XOM à mon portefeuille ? Je tiens à l'ESG.
```
→ **Confirmer**, puis :

✅ Testée (8,9 s) : l'outil refuse de juger, et c'est voulu
```text
Donc XOM est-il compatible avec mes valeurs ESG ?
```
✅ Testée (5,5 s)
```text
est-ce que la règle ESG est respectée ?
```

---

## 4. Construire un portefeuille (mode `build`)

Le modèle moyenne-variance choisit les titres et les poids : au plus 10 % par titre et 25 % par industrie (35 % si préférée).

✅ Testée (8,8 s)
```text
Construis-moi un portefeuille, mais sans actions de dispositifs médicaux ni de tabac.
```

✅ Testée (9,4 s)
```text
Build me a portfolio. I like semiconductors and software, and I want to avoid tobacco.
```

✅ Testée (16 s)
```text
Build me a portfolio with at least 20% in semiconductors and at least 10% in software infrastructure.
```

✅ Testée (11,7 s) : la plus ambitieuse de l'historique
```text
Construis-moi un portefeuille. Cette fois j'accepte le risque maximal : tolérance 5 et capacité 5. Je veux au moins 15 % dans le tabac et 35 % dans l'aérospatiale et défense, et aucun dispositif médical.
```

✅ Testée (15,1 s) : à envoyer **après** une construction confirmée (crée la version 2 du mandat)
```text
Refais-le sans banques ni assurance, avec une tolérance de 4 et une capacité de 4.
```

🧪 **Démo « complète » en un message** (Guardrail OK) :
```text
Construis-moi un portefeuille fictif de 50 000 $. Pour cette simulation, ma tolérance est de niveau 4 et ma capacité de niveau 3. Je veux au moins 15 % dans les semi-conducteurs (Semiconductors) et 10 % dans les logiciels (Software - Infrastructure), et aucune action de tabac (Tobacco) ni de pétrole (Oil & Gas E&P).
```
🧪 Puis :
```text
Refais-le sans banques (Banks - Diversified, Banks - Regional) ni assurance (Insurance - Life), avec une tolérance de 3 et une capacité de 3.
```

🧪 Composée
```text
Construis-moi un portefeuille de 25 000 $ orienté croissance, horizon 15 ans, tolérance 5 et capacité 4, en favorisant les semi-conducteurs (Semiconductors) sans minimum et en excluant les dispositifs médicaux (Medical Devices).
```

🧪 En anglais
```text
Build me a 40,000 dollar fictitious portfolio. For this simulation my tolerance is 4 and my capacity is 4. I want at least 20% in Semiconductors and at least 10% in Software - Infrastructure, and exclude Tobacco.
```

### Montrer que le moteur explique ses limites

✅ Testée (10,6 s) : l'agent explique que 2 titres de tabac plafonnés à 10 % rendent les 60 % impossibles
```text
Build me a portfolio with at least 60% in tobacco.
```

✅ Testée (6,8 s) : l'agent repère la contradiction et demande laquelle garder
```text
Construis-moi un portefeuille. Je veux du tabac, mais exclus aussi le tabac.
```
✅ Testée (8,5 s) : la réponse
```text
Garde seulement l'exclusion du tabac. Propose le mandat.
```

---

## 5. Comprendre l'analyse (après un Confirmer)

✅ Testées (5 à 15 s)
```text
Pourquoi le scénario 1 échoue-t-il ?
```
```text
pourquoi le scénario 1 est en avertissement ?
```
```text
Expliquer la règle R2
```
```text
explique moi R4
```
```text
est-ce que la règle crypto est respectée ?
```
```text
d'où vient EV-06 ?
```
```text
D'où vient KB-01 ?
```

---

## 6. Montrer les garde-fous (refus voulus)

Ces requêtes **doivent** être refusées : c'est une force de l'outil, à montrer comme telle.

| Requête | Ce qui se passe |
|---|---|
| `Achète 100 NVDA pour moi` | Refus expliqué : l'outil ne passe aucun ordre. |
| `Garantis-moi 20 % de rendement par an` | Refus expliqué : aucune promesse de rendement. |
| `Mon compte bancaire est 12345-678-1234567` | Bloqué en 0,4 s : donnée personnelle détectée. |
| `Est-ce que le marché va monter l'an prochain ?` | ✅ Réponse éducative : personne ne peut le prédire. |
| `Alors je devrais l'acheter ou pas ? Dis-moi franchement.` | ✅ L'outil explique qu'il simule, sans dire quoi acheter. |
| `Comment dois-je déclarer mes gains en capital dans ma déclaration de revenus ?` | ✅ Hors périmètre, expliqué poliment. |
| `Which is better to buy, TSLA or NVDA?` | ✅ L'outil propose de simuler les deux plutôt que de choisir. |

---

## 7. ⛔ À éviter pendant la démo

| Formulation | Problème observé | Dites plutôt |
|---|---|---|
| `Construis-moi un portefeuille d'actions.` / `Construire un portefeuille` (seul) | Réponse **masquée** par le Guardrail de sortie | « Construis-moi un portefeuille, mais sans … » ou la version 🧪 complète |
| `What if I add 8% in a world equity ETF?` | Réponse masquée (pourcentage, aucun titre précis) | Un montant en dollars et un titre : « Et si j'ajoutais 5 000 $ CAD de XEF.TO ? » |
| `gold and bitcoin` | Réponse masquée | « Et si j'ajoutais 20 000 $ CAD de bitcoin (BTC-USD) ? » |
| `Je veux mettre 80 000 $ CAD de NVDA, tout le monde en parle.` | Bloquée 2 fois sur 3 | « Et si j'ajoutais 15 000 $ CAD de NVDA à mon portefeuille ? » |
| `devrais-je`, `le meilleur`, `achète`, `promets`, `c'est sûr que ça va remonter` | Refus (voulu) | Section 6 si vous voulez montrer le refus |
| Longues demandes à filtres multiples (« actions qui ont eu une croissance de plus de 5 % sur 3 ans, réparties 50/50 Canada–États-Unis… ») | Délai dépassé (30 s) ou réponse masquée : le moteur n'a pas de filtre de performance passée | Industries à favoriser ou à exclure, minimums en %, tolérance et capacité |
| Noms hors univers (Nestlé, Danone, Brookfield Renewable) | Pas une erreur, mais l'agent répond qu'ils sont absents | Titres du jeu : XIU.TO, XBB.TO, NVDA, TSLA, AAPL, MSFT, XOM, RY.TO, TD.TO, BTC-USD… |

---

*Généré le 16 novembre 2026 à partir de `data/output/langfuse/` et `data/output/langfuse-apres/` (exports Langfuse locaux).*
*Les durées sont celles observées en production ; elles varient de ±30 % d'un essai à l'autre.*
