# Lambda agents (srv-agent-runtime)

Chantier WS5. Implémente les 5 routes du contrat dont le provider est `srv-agent-runtime`, les 3 agents Strands (`agent-orchestrator`, `agent-auditor`, `agent-writer`), les 3 modules de code (`module-engine`, `module-rules`, `module-verifier`) et les 13 outils. Les décisions et les écarts avec le contrat sont dans [`NOTES-agents.md`](NOTES-agents.md).

## Routes

| Route | Module | Modèle |
|---|---|---|
| `POST /v1/conversations/{sessionId}/messages` | `routes/messages.py` | orchestrateur |
| `POST /v1/conversations/{sessionId}/runs` | `routes/runs.py` → `pipeline.start_run` | aucun (partial) |
| `GET /v1/conversations/{sessionId}/runs/{runId}` | `routes/runs.py` | aucun |
| `GET /v1/portfolios/{portfolioId}/summary` | `routes/portfolio_summary.py` | aucun |
| `GET /v1/market/search` | `routes/market_search.py` | aucun |
| événement interne `complete_run` | `pipeline.complete_run` | auditeur, rédacteur, orchestrateur (traduction) |

## Chaîne d'un run

```
POST runs ─► module-engine (scénarios 0/1/2, EV-nn) ─► module-rules (R1-R10) ─► run partial (201)
                └─ auto-invocation asynchrone ─► agent-auditor (KB, KB-nn) ─► agent-writer (textEn)
                   ─► traduction (orchestrateur) ─► module-verifier ─► Guardrail sortie ─► run done
```

## Arborescence

```
app.py               handler : routes HTTP v2 + événement interne
pipeline.py          start_run / complete_run / explanation
data/store.py        Parquet local ou S3, colonnes utiles, cache du conteneur
engine/              analytics (calculs purs), stress, concentration, scenarios, registry (EV/KB)
rules/               rules.py (R1-R10), rules_config.json (hypothèses d'équipe), settings.py
verifier/            verifier.py
tools/               catalog.py (15 outils purs), agent_tools.py (outils Strands, docstrings = consignes),
                     context.py (contexte hors modèle), kb.py (Retrieve filtré)
toolbox.py           droits agent/module → outils, vérifiés au chargement ; journal tool.call
llm/                 base.py (Agent Strands, limites, délai, usage) ; orchestrator/, auditor/, writer/
                     (prompts.py en anglais, schemas.py Pydantic, agent.py)
models.py            un modèle Bedrock par agent (max_tokens toujours fixé)
guardrails.py        ApplyGuardrail : fail-closed sur un blocage, fail-open sur une panne
observability.py     agent.usage et tool.call (JSON, compteurs seulement)
scripts/             starter_to_dataset.py (jeu de départ → disposition du contrat), smoke.py (vrais services)
tests/               pytest sans AWS ni modèle ; fixtures/ = jeu SYNTHÉTIQUE
```

## Tests

```bash
pip install -e ".[dev]" strands-agents==1.65.0 pandas pyarrow moto
pytest                                  # backend/common + backend/agents
pytest backend/api/tests                # à part (voir NOTES-agents.md, point 24)
ALPHAFORGE_STARTER_DIR=.../alphaforge_starter pytest backend/agents/tests/test_starter_dataset.py
python -m backend.agents.tests.fixtures.make_fixtures   # régénérer le jeu synthétique
```

## Banc contre les vrais services (coûte des appels Bedrock)

Voir l'en-tête de `scripts/smoke.py` : Guardrail (faux positifs), Retrieve filtré, un vrai tour de l'orchestrateur. Le script n'écrit rien dans DynamoDB.

## Empaquetage

`infra/scripts/build_lambdas.sh` construit `agents.zip` : `backend/agents`, `backend/common` et les dépendances de `requirements.txt`, sans pandas, pyarrow ni numpy (couche AWS SDK for pandas) et sans les paquets que strands n'importe jamais. Ce zip fait 24 Mo compressé et 46,8 Mo décompressé.
