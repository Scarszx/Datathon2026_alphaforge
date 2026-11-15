# AlphaForge AI

**Tester une idée d'investissement sans conseiller, et comprendre exactement ce qui soutient la réponse.** · Datathon PolyFinances 2026 · Simulation pédagogique : aucune transaction, aucun conseil financier personnalisé.

## Problématique
Sur une plateforme de courtage autonome, l'investisseur voit ce qu'il possède, mais il est seul au moment de tester une idée (« et si j'ajoute 15 000 $ de NVDA ? »). Aucun outil ne mesure l'effet sur l'ensemble de son portefeuille, ni ne dit si l'idée tient face à son objectif, son horizon et sa capacité à encaisser une perte, tout en restant neutre et en citant ses sources.

## Approche agentique
Le code calcule, le modèle cadre et cite, un vérificateur contrôle.
- **Orchestrateur** (Claude Sonnet 5.5, Bedrock) : comprend la demande dans la langue de l'utilisateur, lit son profil, pose au plus une étape de questions et propose un *mandat* que l'utilisateur confirme.
- **Moteur de calcul** (code) : trois scénarios (actuel, idée, alternative par catégorie d'actifs), volatilité, pire baisse, tests de résistance dérivés des données (2022, COVID 2020, hausse des taux, krach crypto), concentration.
- **Règles R1 à R10** (code) : les verdicts viennent du code, pas du modèle.
- **Auditeur** (agent) : retrouve dans la Knowledge Base réglementaire (ACVM, OCRI, province) le passage qui fonde chaque verdict. **Rédacteur** (agent) : écrit sans jamais écrire un chiffre. **Vérificateur** (code) : masque toute phrase qui déborde.
- Un **Guardrail** filtre ordres, promesses de rendement, conseil personnalisé et renseignements bancaires. 3 agents, 3 modules en code, 13 outils aux droits fermés.

## Originalité
- **Aucun chiffre n'est écrit par un modèle** : le texte porte des emplacements (`{EV-07}`, `{KB-03}`) que l'interface remplace par des preuves cliquables. Un emplacement inconnu n'affiche jamais de chiffre.
- **Les verdicts sont citables** : chaque règle renvoie à un texte réglementaire canadien réel, filtré par la province de l'utilisateur.
- **Neutre par construction** : alternatives par catégorie d'actifs, jamais par titre, dans l'esprit de la note de l'OCRI sur les comptes sans conseil.
- **Un seul moteur, trois personas** : Robert voit son idée audacieuse remise en question, Mateo voit ce que l'outil ne peut pas affirmer sur l'ESG, Amira voit sa diversification mesurée.

## Sources de données
Yahoo Finance (241 actifs, 10 ans), Banque du Canada, FRED, 13 documents réglementaires publics. Sources, dates, traitements et limites documentés ; jeu versionné (`2026-11-14`). Hypothèses d'équipe (fenêtre, seuils) affichées comme telles.

## Capacité d'explication
Chaque réponse porte ses **sources** (version du jeu de données, date), ses **étapes réellement exécutées** (agent, outil, durée), ses **hypothèses** et ses **limites**, construites à partir du journal d'exécution, jamais rédigées après coup. Exemple : le verdict « idée refusée » pour Robert renvoie à la volatilité de NVDA (51,9 %, formule et fenêtre visibles), à la bande de risque qui en découle, puis à l'instruction 31-103CP qui fonde la règle.

## Bénéfices concrets
L'investisseur sait **pourquoi** une idée passe ou échoue, voit **ce qui changerait** la réponse (curseurs d'horizon et de perte acceptée), lit ses limites sans jargon et peut tout vérifier. La plateforme obtient un outil d'aide à la décision neutre, auditable et déployable sur AWS (Bedrock, Lambda, Cognito, DynamoDB, S3, CloudFront).

*Limites : composition des FNB non renseignée, biais du survivant, hypothèses d'équipe non officielles, filtre d'entrée qui refuse encore certaines formulations. Détail dans la documentation technique.*
