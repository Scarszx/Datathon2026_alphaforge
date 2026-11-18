# Graph Report - Datathon2026_alphaforge  (2026-11-18)

## Corpus Check
- 328 files · ~247,015 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 30 file(s) not represented in the graph (top: .parquet 17, .csv 6, .example 3)

## Summary
- 3081 nodes · 8242 edges · 172 communities (140 shown, 32 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 447 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Evidence & Rule Verdicts
- Investor Profile UI
- Frontend API Client
- Analyses/Runs Repositories
- API Lambda & Agents Registry
- Portfolio Optimizer
- Rules Engine (R1-R10)
- Frontend App & Account
- Agents Lambda & Store
- Dependencies & Packages
- French Fixed Texts
- Evidence Registry
- Charts & Mandate Column
- Demo Data (frontend)
- Runs Routes
- Request Handlers
- Market DataStore
- KB Corpus Builder
- Conversations Repository
- Auditor & Bedrock Converse
- Project Docs & Rules
- Translation of Run
- DynamoDB Utilities
- Dataset Loading
- Tickers Builder
- Agent Prompts
- CIRO OEO Guidance
- Cognito Auth
- Langfuse Telemetry
- Langfuse Skill Docs
- Users Routes
- Smoke & Translate Tests
- Test Fixtures & Repos
- Strands Agent Base
- Writer Agent
- Tools Tests
- API Errors & Auth Claims
- Messages Route & Explanation
- Contract Services
- Scenarios Engine
- test_optimize_portfolio_outil( group
- llm/__init__.py group
- fetcher.py group
- config.py group
- agents/__init__.py group
- ModelScripts group
- guardrails.py group
- infer_subjects() group
- Amazon API Gateway (HTTP API,  group
- auditor/agent.py group
- normalize() group
- common/mandates.py group
- apis group
- orchestrator/__init__.py group
- kb.py group
- event() group
- _country_fallback() group
- handle_request() group
- Injecte un magasin (tests, ban group
- api/routes/__init__.py group
- body_of() group
- test_routes_mandates.py group
- categories.py group
- build_dataset.py group
- test_un_motif_reformule_par_l_ group
- analyses_table() group
- asset_class group
- argparse group
- provider group
- .__init__() group
- Any group
- FakeTranslate group
- error_codes group
- build_dataset() group
- validators.py group
- tsconfig.json group
- _norm_ok() group
- application group
- Grow: documentation technique group
- e2e_runs.py group
- Oublie la ressource en cache ( group
- Couverture des exigences du Da group
- R1 volatility bands (risk prof group
- quality.py group
- Amazon Translate fr-CA avec gl group
- Limite: faux positifs du Guard group
- agent-auditor (KB, citations) group
- knowledge-graph.yaml group
- universe.yaml group
- asset_class group
- Scénario vedette Robert + NVDA group
- Bedrock Guardrail (variante B, group
- NOTES WS5 Lambda agents group
- test_version_de_corpus_differe group
- _new_corpus_result() group
- _check_build_preferences() group
- fake_conversations() group
- model_auditor() group
- identifiers group
- agent-orchestrator group
- agent-writer group
- Banc scripts/e2e_runs.py (15 c group
- kb_sync.sh group
- manifest.json group
- FakeGuardrail group
- test_app.py group
- fake_mandate_repos() group
- fake_portfolios() group
- query_params group
- DataFrame group
- Grow Architecture AWS (dossier group
- Bedrock Guardrail group
- Asynchronous run completion vi group
- citable filter and fixed citat group
- Synthetic test fixtures (no Ya group
- ctx() group
- NOTES WS4 api assumptions group
- fixture group
- language_policy group
- load_universe_candidates() group
- build_lambdas.sh group
- fake_users() group
- handler.py group
- NOTES WS1b infra v0.4 group
- Lambda agents README (srv-agen group
- test_read_evidence() group
- parametrize group
- fixture group
- asset_class group
- asset_class group
- tsx_equities_communications group
- tsx_equities_consumer_discreti group
- tsx_equities_consumer_staples group
- tsx_equities_energy group
- tsx_equities_financials group
- tsx_equities_industrials group
- tsx_equities_materials group
- tsx_equities_real_estate group
- tsx_equities_technology group
- tsx_equities_utilities group
- us_equities_communications group
- us_equities_consumer_discretio group
- us_equities_consumer_staples group
- us_equities_financials group
- us_equities_healthcare group
- us_equities_technology group
- pcm-worklet.js group
- ambient-node.d.ts group
- langfuse_base_url() group
- id group
- workstreams.md (découpage du t group
- Shared mandate logic in backen group
- ctx() group
- Series group
- USD/CAD coverage starts 2017-0 group
- adj_close retroactive adjustme group
- Demo mode (src/api/demo.ts) si group
- vite-env.d.ts group
- Jeu de donnees 2026-11-15 (582 group
- Saisie vocale (Amazon Transcri group
- alphaforge-backend group

## God Nodes (most connected - your core abstractions)
1. `ApiError` - 95 edges
2. `DataStore` - 81 edges
3. `handle_request()` - 69 edges
4. `RequestContext` - 68 edges
5. `event()` - 63 edges
6. `body_of()` - 57 edges
7. `useT()` - 52 edges
8. `EvidenceRegistry` - 50 edges
9. `t()` - 49 edges
10. `run_engine()` - 40 edges

## Surprising Connections (you probably didn't know these)
- `Provenance panel (explanation of conclusion)` --shares_data_with--> `Run chain (engine, rules, auditor, writer, translation, verifier, guardrail)`  [INFERRED]
  frontend/NOTES-frontend.md → backend/agents/README.md
- `Registre de preuves EV-nn / KB-nn` --semantically_similar_to--> `Registre de preuves et emplacements EV-nn / KB-nn`  [INFERRED] [semantically similar]
  docs/for_building/architecture-aws-grow.html → docs/for_building/documentation-technique.md
- `Guardrail false positives to test early` --references--> `NOTES WS5 Lambda agents`  [INFERRED]
  infra/NOTES-infra.md → backend/agents/NOTES-agents.md
- `Conversations updatedAt-index LSI` --references--> `Infrastructure Grow (Terraform) README`  [EXTRACTED]
  backend/common/repositories/NOTES-db.md → infra/README.md
- `S3 upload to storage-dataset (documented, not executed)` --references--> `Infrastructure Grow (Terraform) README`  [EXTRACTED]
  data/README.md → infra/README.md

## Import Cycles
- 2-file cycle: `backend/common/repositories/__init__.py -> backend/common/repositories/analyses.py -> backend/common/repositories/__init__.py`
- 2-file cycle: `backend/common/repositories/__init__.py -> backend/common/repositories/conversations.py -> backend/common/repositories/__init__.py`
- 2-file cycle: `backend/common/repositories/__init__.py -> backend/common/repositories/messages.py -> backend/common/repositories/__init__.py`
- 2-file cycle: `backend/common/repositories/__init__.py -> backend/common/repositories/portfolios.py -> backend/common/repositories/__init__.py`
- 2-file cycle: `backend/common/repositories/__init__.py -> backend/common/repositories/users.py -> backend/common/repositories/__init__.py`

## Hyperedges (group relationships)
- **Grow session pipeline components** — solution_orchestrator, solution_compute_engine, solution_auditor, solution_writer, solution_verifier [EXTRACTED 1.00]
- **Explainability chain (registry, writer placeholders, verifier)** — solution_evidence_registry, solution_writer, solution_verifier [EXTRACTED 1.00]
- **Project orientation documents** — agents, solution, readme, solution_contract [INFERRED 0.85]
- **Composants du pipeline agentique de Grow** — docs_for_building_documentation_technique_orchestrator, docs_for_building_documentation_technique_auditor, docs_for_building_documentation_technique_writer, docs_for_building_documentation_technique_engine, docs_for_building_documentation_technique_verifier [EXTRACTED 1.00]
- **Optimisations de latence guidees par les traces** — docs_for_building_architecture_aws_grow_engine_latency_fix, docs_for_building_architecture_aws_grow_amazon_translate, docs_for_building_architecture_aws_grow_writer_parallel, docs_for_building_architecture_aws_grow_sonnet_5_5_choice [EXTRACTED 1.00]
- **Options pour le filtre d'entree du Guardrail** — docs_for_building_guardrail_etat_et_pistes_context_prefix, docs_for_building_guardrail_etat_et_pistes_variant_a, docs_for_building_jev_classifieur_intention_jev_model [INFERRED 0.85]
- **Pipeline d'une session v0.4** — docs_for_building_workstreams_agent_orchestrator, docs_for_building_workstreams_module_engine, docs_for_building_workstreams_module_rules, docs_for_building_workstreams_agent_auditor, docs_for_building_workstreams_agent_writer, docs_for_building_workstreams_module_verifier [EXTRACTED 1.00]
- **Leviers de réduction de latence de l'analyse** — profiling_2026_11_15_session_01_latence_agents_amazon_translate, profiling_2026_11_15_session_01_latence_agents_writer_parallel, profiling_2026_11_15_session_01_latence_agents_prices_many, profiling_2026_11_15_session_01_latence_agents_prompt_caching [INFERRED 0.85]
- **Run completion pipeline (engine, rules, auditor, writer, verifier, guardrail)** — backend_agents_readme_run_chain, backend_agents_notes_agents_code_driven_auditor, backend_agents_notes_agents_verifier_masking, backend_agents_notes_agents_async_run_completion [EXTRACTED 0.95]
- **Regulatory KB stack (corpus, S3 Vectors, Bedrock KB, citable filter)** — backend_agents_notes_agents_kb_corpus_by_section, infra_readme_s3_vectors, infra_readme_bedrock_kb, backend_agents_notes_agents_citable_filter [INFERRED 0.85]
- **Dataset limitations (no forward-fill, FX start, survivorship bias, short histories)** — data_readme_no_forward_fill, data_notes_data_fx_coverage, data_readme_survivorship_bias, data_readme_adjclose_splits [INFERRED 0.75]
- **Langfuse evaluation workflow (evals, datasets, judge calibration, error analysis)** — _agents_skills_langfuse_references_setting_up_evals, _agents_skills_langfuse_references_create_dataset, _agents_skills_langfuse_references_judge_calibration, _agents_skills_langfuse_references_error_analysis, _agents_skills_langfuse_references_ci_cd [INFERRED 0.85]
- **OEO self-help tools (filtering, sample portfolios, self-assessment, rebalancing)** — docs_for_kb_ca_ciro_gn_3200_26_001_oeo_guidance_2026_03_12_en_filtering_tools, docs_for_kb_ca_ciro_gn_3200_26_001_oeo_guidance_2026_03_12_en_sample_portfolios, docs_for_kb_ca_ciro_gn_3200_26_001_oeo_guidance_2026_03_12_en_self_assessment_tools, docs_for_kb_ca_ciro_gn_3200_26_001_oeo_guidance_2026_03_12_en_rebalancing_tools [EXTRACTED 0.95]
- **OEO permitted decision-making supports under recommendation prohibition** — docs_for_kb_ca_ciro_gn_3200_26_001_oeo_guidance_2026_03_12_en_recommendation_prohibition, docs_for_kb_ca_ciro_gn_3200_26_001_oeo_guidance_2026_03_12_en_decision_making_supports, docs_for_kb_ca_ciro_gn_3200_26_001_oeo_guidance_2026_03_12_en_safeguards, docs_for_kb_ca_ciro_gn_3200_26_001_oeo_guidance_2026_03_12_en_conflicts_of_interest [EXTRACTED 0.95]
- **Bedrock AI stack used by agents Lambda** — docs_grow_infra_guardrails, docs_grow_infra_claude_sonnet, docs_grow_infra_knowledge_base, docs_grow_infra_lambda_agents [EXTRACTED 1.00]
- **Front delivery chain** — docs_grow_infra_s3_front, docs_grow_infra_cloudfront, docs_grow_infra_spa_react [EXTRACTED 1.00]

## Communities (172 total, 32 thin omitted)

### Community 0 - "Evidence & Rule Verdicts"
Cohesion: 0.05
Nodes (84): Evidence, RuleVerdict, CONFIRMED, DONE, DRAFT, PARTIAL, CompareCategory(), CompareCategoryButton() (+76 more)

### Community 1 - "Investor Profile UI"
Cohesion: 0.06
Nodes (78): InvestorProfile, Jurisdiction, IndustrySearch(), Side(), Answers, PersonalQuestionnaire(), submit(), AMOUNT_CHOICES (+70 more)

### Community 2 - "Frontend API Client"
Cohesion: 0.06
Nodes (76): request(), createConversation(), createMandate(), createRun(), deleteConversation(), getAgentsRegistry(), getAssetDetail(), getRun() (+68 more)

### Community 3 - "Analyses/Runs Repositories"
Cohesion: 0.07
Nodes (42): delete_analyses(), _get_item(), get_latest_mandate(), get_latest_run(), get_mandate(), get_run(), _latest_mandate_item(), list_mandates() (+34 more)

### Community 4 - "API Lambda & Agents Registry"
Cohesion: 0.06
Nodes (23): get_registry(), _registry(), create_conversation(), delete_conversation(), _ensure_owner(), list_conversations(), list_messages(), _no_content() (+15 more)

### Community 5 - "Portfolio Optimizer"
Cohesion: 0.06
Nodes (32): candidate_universe(), check_preferences(), _check_reachable(), _clean_preferences(), Holding, ledoit_wolf_covariance(), load_config(), OptimizationResult (+24 more)

### Community 6 - "Rules Engine (R1-R10)"
Cohesion: 0.08
Nodes (47): _crypto_refused(), ScenarioAnalysis, check_rules(), _contains_ticker(), _ev(), needs_regulation(), r1(), r2() (+39 more)

### Community 7 - "Frontend App & Account"
Cohesion: 0.09
Nodes (44): signUp(), App(), Private(), AppHeader(), AssetClassPicker(), Avatar(), ICONS, TINTS (+36 more)

### Community 8 - "Agents Lambda & Store"
Cohesion: 0.06
Nodes (24): default_store(), aligned_cad_prices(), AlignedPrices, annualized_volatility(), asset_metrics(), bootstrap_ranges(), correlation_matrix(), is_crypto() (+16 more)

### Community 9 - "Dependencies & Packages"
Cohesion: 0.05
Nodes (51): dependencies, react@^18.3.1, react-dom@^18.3.1, react-router-dom@^6.28.0, @smithy/eventstream-codec@4.5.2, @smithy/util-utf8@4.5.2, devDependencies, jsdom@^29.1.1 (+43 more)

### Community 10 - "French Fixed Texts"
Cohesion: 0.07
Nodes (38): fixed_message(), fixed_notice(), _default_messages(), test_aucune_entree_orpheline_dans_la_table(), test_chaque_mention_de_la_configuration_a_sa_version_francaise(), test_chaque_motif_par_defaut_a_sa_version_francaise(), test_la_table_garde_les_memes_emplacements_et_aucune_approbation(), test_le_suffixe_de_transparence_est_traduit() (+30 more)

### Community 11 - "Evidence Registry"
Cohesion: 0.09
Nodes (24): EvidenceRegistry, format_number(), apply_operations(), comparison_operations(), holding_values_cad(), _record_asset_metrics(), run_engine(), convert() (+16 more)

### Community 12 - "Charts & Mandate Column"
Cohesion: 0.09
Nodes (44): AssetDetail, Chart(), clamp(), MandateColumn(), InfoTip(), P, PriceChart(), ts() (+36 more)

### Community 13 - "Demo Data (frontend)"
Cohesion: 0.08
Nodes (49): Analyses, applyOps(), asset(), ASSETS, bandProfile(), buildRun(), changedFields(), completeRun() (+41 more)

### Community 14 - "Runs Routes"
Cohesion: 0.11
Nodes (28): create_run(), _ensure_owner(), get_run(), put_holdings(), _array_of_strings(), _integer(), _number(), parse_json_body() (+20 more)

### Community 15 - "Request Handlers"
Cohesion: 0.12
Nodes (40): handle_internal(), handle_request(), handler(), body_of(), event(), call(), _complete(), _script_completion() (+32 more)

### Community 16 - "Market DataStore"
Cohesion: 0.08
Nodes (25): DataStore, load(), fx_rate_on(), listing_currency(), to_cad(), by_asset_class(), concentration(), _country_of() (+17 more)

### Community 17 - "KB Corpus Builder"
Cohesion: 0.10
Nodes (29): build_document(), build_fixed_citations(), build_metadata(), clean_lines(), doc_key_of(), extract_pages(), file_stem(), Line (+21 more)

### Community 18 - "Conversations Repository"
Cohesion: 0.10
Nodes (27): conversations_table(), create_conversation(), delete_conversation(), get_conversation(), list_conversations(), _raise_not_found(), rename_conversation(), set_user_language() (+19 more)

### Community 19 - "Auditor & Bedrock Converse"
Cohesion: 0.11
Nodes (31): audit(), AgentFailure, converse(), output(), test_aucune_citation_ni_recherche_pour_pass_et_not_verified(), test_auditeur_cite_seulement_les_passages_des_candidats(), test_auditeur_en_echec_garde_les_verdicts(), test_auditeur_ne_cherche_pas_les_verdicts_sans_objet() (+23 more)

### Community 20 - "Project Docs & Rules"
Cohesion: 0.07
Nodes (40): AGENTS.md (project instructions), AWS/Terraform rules (event account 058264316309), Langfuse observability rules (fictional data only), README.md (Grow project readme), Section for AI agents (reading order, rules, code map), Data sources (Yahoo, BoC Valet, FRED, issuer sheets), Guardrail state and leads doc, Assumptions and limits (survivor bias, ETF look-through, latency) (+32 more)

### Community 21 - "Translation of Run"
Cohesion: 0.14
Nodes (22): _apply_translations(), complete_run(), _ctx(), _flag_two(), test_anglais_aucun_appel_translate(), test_aucune_permission_translate_le_run_s_affiche_en_anglais(), test_autre_langue_l_anglais_est_affiche_et_signale(), test_chaque_section_est_traduite_sans_attendre_la_plus_lente() (+14 more)

### Community 22 - "DynamoDB Utilities"
Cohesion: 0.09
Nodes (21): clamp_limit(), decode_cursor(), encode_cursor(), from_dynamo(), _resource(), delete_messages(), list_messages(), put_message() (+13 more)

### Community 23 - "Dataset Loading"
Cohesion: 0.08
Nodes (12): _clean_prices(), DatasetError, load(), load(), load(), load(), load(), load() (+4 more)

### Community 24 - "Tickers Builder"
Cohesion: 0.09
Nodes (18): build_payload(), main(), _read_csv(), _read_parquet(), _read_tickers(), _symbol_column(), test_build_payload_trie_et_refuse_les_doublons(), test_build_tickers_lit_un_csv() (+10 more)

### Community 25 - "Agent Prompts"
Cohesion: 0.08
Nodes (13): audit_prompt(), translate_fix_prompt(), turn_prompt(), test_description_non_vide_pour_chaque_outil_et_parametre(), test_droits_conformes_au_contrat(), test_les_15_outils_du_contrat_sont_enregistres(), test_outils_strands_par_agent(), test_prompts_et_descriptions_sans_francais() (+5 more)

### Community 26 - "CIRO OEO Guidance"
Cohesion: 0.06
Nodes (35): CIRO Bulletin 26-0059 (New OEO guidance), Method of delivery not determinative (push vs pull), Meaningful continuous disclosure for DIY investors, Phase 2 consultation (15 comment letters), Decision: sample portfolios without specific securities, CIRO GN-3200-26-001 OEO Guidance, Account appropriateness and written disclosures, Alerts and notifications (+27 more)

### Community 27 - "Cognito Auth"
Cohesion: 0.13
Nodes (32): cognito(), COGNITO_ERRORS, deleteOwnAccount(), getAccessToken(), hasSession(), read(), signIn(), signOut() (+24 more)

### Community 28 - "Langfuse Telemetry"
Cohesion: 0.09
Nodes (12): _fetch_secret_from_ssm(), flush_telemetry(), inject_trace_context(), _is_placeholder(), _load_dotenv_if_local(), reset_for_tests(), resolve_credentials(), start_telemetry() (+4 more)

### Community 29 - "Langfuse Skill Docs"
Cohesion: 0.08
Nodes (28): Langfuse CI/CD experiment gates, langfuse/experiment-action, Langfuse CLI reference, Langfuse Topics (closed beta), Observations API preferred over traces, Langfuse cost optimization, Langfuse dataset construction, Langfuse error analysis (+20 more)

### Community 30 - "Users Routes"
Cohesion: 0.14
Nodes (16): _claims(), _display_name(), get_me(), put_profile(), _username(), users_table(), get_user(), put_user_if_absent() (+8 more)

### Community 31 - "Smoke & Translate Tests"
Cohesion: 0.08
Nodes (16): main(), run_guardrail_cases(), test_la_requete_envoie_du_html_vers_fr_ca_avec_la_terminologie(), test_les_defauts_de_traduction_sont_signales(), test_sans_terminologie_configuree_la_requete_n_en_cite_aucune(), test_terminologie_absente_du_compte_un_deuxieme_essai_sans_elle(), test_une_autre_erreur_de_translate_n_est_pas_rattrapee(), test_une_bonne_traduction_passe_les_controles() (+8 more)

### Community 32 - "Test Fixtures & Repos"
Cohesion: 0.14
Nodes (16): robert_session(), is_conditional_failure(), ensure_main_portfolio(), get_portfolio(), list_portfolios(), replace_holdings(), _to_portfolio(), test_ensure_main_portfolio_cree_main_vide() (+8 more)

### Community 33 - "Strands Agent Base"
Cohesion: 0.09
Nodes (7): build_agent(), run_agent(), ToolCallLimit, AgentSpec, create_model(), model_id(), test_un_appel_par_section_nomme_dans_la_trace()

### Community 34 - "Writer Agent"
Cohesion: 0.10
Nodes (11): analysis_record(), collect(), SectionCalls, submit(), write(), _write_section(), section_system_prompt(), write_section_prompt() (+3 more)

### Community 35 - "Tools Tests"
Cohesion: 0.12
Nodes (25): _build_draft(), _size(), test_compute_metrics_sans_lignes_brutes(), test_extrait_coupe_a_une_fin_de_phrase(), test_extrait_ne_coupe_ni_apres_une_abreviation_ni_sur_un_point_virgule(), test_filtre_citable_strict_seulement_une_fois_le_nouveau_corpus_ingere(), test_get_macro(), test_get_prices_erreurs_qui_disent_quoi_corriger() (+17 more)

### Community 36 - "API Errors & Auth Claims"
Cohesion: 0.11
Nodes (13): _not_found(), get_user_id(), ApiError, error_response(), evenement(), test_evenement_sans_jwt(), test_jwt_sans_claim_sub(), test_user_id_depuis_le_claim_sub() (+5 more)

### Community 37 - "Messages Route & Explanation"
Cohesion: 0.13
Nodes (12): build_explanation(), post_message(), refusal_message(), _session_context(), _validate_content(), new_message_id(), new_run_id(), new_session_id() (+4 more)

### Community 38 - "Contract Services"
Cohesion: 0.08
Nodes (26): id, mode, srv-agent-runtime, srv-api-light, services, access_to_dbs, consumes_apis, contains_agents (+18 more)

### Community 39 - "Scenarios Engine"
Cohesion: 0.13
Nodes (15): _asset_band(), _build_scenario(), Comparison, EngineResult, _fmt2(), _idea_assets(), public_scenarios(), resolve_comparison() (+7 more)

### Community 40 - "test_optimize_portfolio_outil( group"
Cohesion: 0.27
Nodes (19): test_optimize_portfolio_outil(), test_outils_du_portefeuille_lisent_l_utilisateur_du_contexte(), check_rules(), compute_metrics(), concentration(), _current_weights(), _error(), get_macro() (+11 more)

### Community 41 - "llm/__init__.py group"
Cohesion: 0.14
Nodes (11): completion_payload(), default_dispatcher(), _held_tickers(), _lambda_invoke(), _now(), start_run(), team_assumptions(), jurisdiction_notices() (+3 more)

### Community 42 - "fetcher.py group"
Cohesion: 0.15
Nodes (8): download_fx_and_macro(), download_prices_in_batches(), _extract_ticker_frames(), fetch_boc_series(), fetch_fred_series(), fetch_sp500_top(), fetch_yfinance_info(), _http_get_bytes()

### Community 43 - "config.py group"
Cohesion: 0.12
Nodes (10): guardrail_id(), guardrail_version(), kb_id(), langfuse_public_key(), langfuse_secret_key(), langfuse_secret_param(), log_level(), rules_config_path() (+2 more)

### Community 44 - "agents/__init__.py group"
Cohesion: 0.13
Nodes (12): explain_refusal(), fix_translations(), history_messages(), placeholders_preserved(), refusal_prompt(), OrchestratorTurn, Refusal, TranslationEdit (+4 more)

### Community 45 - "ModelScripts group"
Cohesion: 0.13
Nodes (5): ModelScripts, add_section_writers(), ScriptedModel, SectionWriter, test_redacteur_une_section_en_echec_fait_echouer_l_ensemble()

### Community 46 - "guardrails.py group"
Cohesion: 0.20
Nodes (13): apply(), _blocked_topic_names(), _client(), GuardrailResult, _has_blocked_action(), _policy_blocked(), _configure(), Recorder (+5 more)

### Community 47 - "infer_subjects() group"
Cohesion: 0.21
Nodes (9): infer_subjects(), _call(), get_portfolio(), get_profile(), propose_mandate(), read_evidence(), search_assets(), search_regulation() (+1 more)

### Community 48 - "Amazon API Gateway (HTTP API,  group"
Cohesion: 0.12
Nodes (21): Amazon API Gateway (HTTP API, 19 routes /v1), Amazon Bedrock, Claude Sonnet 5.5 (orchestrateur, auditeur, rédacteur), Amazon CloudFront, Amazon Cognito (alphaforge-users), Architecture AWS Grow (diagramme), Amazon DynamoDB (5 tables, à la demande), Bedrock Guardrails (alphaforge-guardrail v4) (+13 more)

### Community 49 - "auditor/agent.py group"
Cohesion: 0.15
Nodes (10): _candidates_for(), run(), merge_passages(), _passage_key(), _prompt_groups(), rule_query(), _safe_message(), verdict_groups() (+2 more)

### Community 50 - "normalize() group"
Cohesion: 0.13
Nodes (13): normalize(), _metadata(), test_apostrophes_normalisees_pour_les_controles(), test_citable_statut_et_sections_cles(), test_citations_fixees_embarquees_sont_celles_du_corpus_construit(), test_manifeste_et_rapport(), test_metadonnees_courtes_sujets_connus_et_noms_compatibles_avec_la_kb(), test_notes_de_bas_de_page_dans_un_fichier_non_citable_sans_sujet_de_recherche() (+5 more)

### Community 51 - "common/mandates.py group"
Cohesion: 0.18
Nodes (11): compute_warnings(), default_max_loss_pct(), _embedded_defaults(), evaluate_mandate(), _extract_project_years(), _load_defaults(), _warning(), _mandate() (+3 more)

### Community 52 - "apis group"
Cohesion: 0.10
Nodes (20): apis, auth, description, errors, id, method, notes, optional (+12 more)

### Community 53 - "orchestrator/__init__.py group"
Cohesion: 0.15
Nodes (6): _emit(), log_agent_usage(), log_event(), log_tool_call(), test_nom_de_terminologie_par_defaut_vide_ou_surcharge(), translate_terminology()

### Community 54 - "kb.py group"
Cohesion: 0.17
Nodes (9): build_filter(), _client(), document_title(), excerpt_of(), is_citable(), _is_sentence_end(), retrieve(), section_label() (+1 more)

### Community 55 - "event() group"
Cohesion: 0.16
Nodes (12): event(), test_get_agents_renvoie_le_registre_public_v04(), test_le_registre_respecte_les_droits_et_limites_du_contrat(), test_delete_conversation_supprime_messages_analyses_puis_conversation(), test_list_messages_d_une_conversation_etrangere(), _profile(), test_get_me_cree_le_profil_au_premier_appel(), test_get_me_sans_claim_username_replie_sur_sub() (+4 more)

### Community 56 - "_country_fallback() group"
Cohesion: 0.15
Nodes (11): _country_fallback(), _merge_candidates(), add(), deduce_market_and_currency(), _make_valid_etf_entry(), test_compute_1y_indicators_edge_cases(), test_deduce_market_and_currency(), test_deduce_market_and_currency_index() (+3 more)

### Community 57 - "handle_request() group"
Cohesion: 0.18
Nodes (11): handle_request(), handler(), test_deux_404_successifs_recoivent_leur_request_id(), request_for(), test_list_portfolios_cree_main_et_retourne_items(), test_put_holdings_accepte_une_liste_vide(), test_put_holdings_d_un_portefeuille_etranger_est_invisible(), test_put_holdings_refuse_les_corps_invalides() (+3 more)

### Community 58 - "Injecte un magasin (tests, ban group"
Cohesion: 0.12
Nodes (11): set_default_store(), market_stats(), daily_returns(), aws(), _create_tables(), scripts(), store(), translate_fake() (+3 more)

### Community 59 - "api/routes/__init__.py group"
Cohesion: 0.13
Nodes (7): faux_identifiants(), _query(), test_corps_invalide_refuse(), test_la_region_vient_de_l_environnement(), test_sans_jwt_refuse(), test_session_fr_par_defaut_sans_corps(), test_url_signee_avec_les_parametres_attendus()

### Community 60 - "body_of() group"
Cohesion: 0.22
Nodes (13): body_of(), test_create_conversation_refuse_champ_inconnu(), test_create_conversation_renvoie_201(), test_create_conversation_sans_corps_est_acceptee(), test_delete_conversation_etrangere_est_invisible(), test_deux_404_successifs_recoivent_leur_request_id(), test_list_conversations_envoie_limit_et_cursor(), test_list_conversations_refuse_limit_invalide() (+5 more)

### Community 61 - "test_routes_mandates.py group"
Cohesion: 0.21
Nodes (12): test_create_et_list_mandates_verifient_la_propriete_de_la_conversation(), test_create_mandate_calcule_risk_profile_et_perte_par_defaut(), test_create_mandate_conserve_max_acceptable_loss_saisi(), test_create_mandate_detecte_les_incoherences_dans_warnings(), test_create_mandate_mode_diagnose_valide_subject_ticker(), test_create_mandate_refuse_les_corps_invalides(), test_create_mandate_refuse_ticker_inconnu_en_validation_error(), test_create_mandate_versions_successives_et_changed_fields() (+4 more)

### Community 62 - "categories.py group"
Cohesion: 0.21
Nodes (11): categories(), category_ids(), get_category(), _build_body(), _mandate_body(), _op(), test_build_amount_facultatif_positif_et_reserve_au_mode_build(), test_categories_sans_symbole_dans_les_libelles_et_triees_par_niveau() (+3 more)

### Community 63 - "build_dataset.py group"
Cohesion: 0.15
Nodes (6): main(), add_macro_publication_date(), compute_1y_indicators(), compute_monthly_publication_date(), test_add_macro_publication_date_on_fixtures(), test_compute_monthly_publication_date_rule_28th_next_month()

### Community 64 - "test_un_motif_reformule_par_l_ group"
Cohesion: 0.18
Nodes (8): test_un_motif_reformule_par_l_auditeur_passe_par_translate(), _complete(), SlowAuditor, test_les_sections_precoces_demarrent_avant_la_fin_de_l_auditeur(), test_plafond_de_quatre_lectures_dans_toute_la_chaine(), test_registre_fige_pour_les_sections_precoces(), test_sections_precoces_sans_citation_tardives_avec(), test_une_section_en_echec_donne_status_error_sans_recit()

### Community 65 - "analyses_table() group"
Cohesion: 0.16
Nodes (8): analyses_table(), dataset_bucket(), dataset_version(), messages_table(), MissingEnvVar, portfolios_table(), _required(), test_variables_requises_presentes()

### Community 66 - "asset_class group"
Cohesion: 0.15
Nodes (16): asset_class, candidates, default_sector, asset_class, candidates, default_sector, candidates, asset_class (+8 more)

### Community 67 - "argparse group"
Cohesion: 0.21
Nodes (4): candidate_industries(), main(), main(), main()

### Community 68 - "provider group"
Cohesion: 0.13
Nodes (15): provider, public_routes, scheme, user_identity, conventions, amounts, api_base_path, authentication (+7 more)

### Community 69 - ".__init__() group"
Cohesion: 0.23
Nodes (8): call(), ensure_account(), holdings_from_amounts(), id_token(), main(), password_for(), read_env(), terraform_outputs()

### Community 70 - "Any group"
Cohesion: 0.21
Nodes (4): _serialize_io(), set_span_output(), trace_span(), Item

### Community 71 - "FakeTranslate group"
Cohesion: 0.15
Nodes (7): FakeTranslate, test_au_retour_les_balises_sont_retirees_et_les_entites_decodees(), test_les_emplacements_et_les_citations_sont_proteges_en_html(), test_un_passage_cite_contenant_un_emplacement_est_protege_d_un_bloc(), test_une_espace_supprimee_autour_d_un_emplacement_est_restituee(), protect(), unprotect()

### Community 72 - "error_codes group"
Cohesion: 0.15
Nodes (13): error_codes, AGENT_TIMEOUT, ASSET_NOT_FOUND, CONVERSATION_NOT_FOUND, FORBIDDEN, GUARDRAIL_BLOCKED, INTERNAL, MANDATE_NOT_CONFIRMED (+5 more)

### Community 73 - "build_dataset() group"
Cohesion: 0.18
Nodes (4): build_dataset(), _load_offline_inputs(), test_build_dataset_offline_on_fixtures(), test_build_dataset_offline_on_starter_pack()

### Community 74 - "validators.py group"
Cohesion: 0.27
Nodes (6): _is_entry_populated(), _is_valid_iso_date(), _is_valid_url(), validate_candidate_prices(), validate_etf_enriched(), validate_etf_entry()

### Community 75 - "tsconfig.json group"
Cohesion: 0.15
Nodes (12): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, resolveJsonModule (+4 more)

### Community 76 - "_norm_ok() group"
Cohesion: 0.18
Nodes (9): _norm_ok(), test_search_assets(), test_search_assets_accents_ponctuation_et_alias(), test_search_assets_exclut_les_indices(), test_search_assets_plusieurs_noms_en_un_appel(), _matches(), _norm(), search_assets() (+1 more)

### Community 77 - "application group"
Cohesion: 0.17
Nodes (12): application, changelog, description, name, solution_ref, status, version, date (+4 more)

### Community 78 - "Grow: documentation technique group"
Cohesion: 0.21
Nodes (12): Grow: documentation technique, Sources de donnees (Yahoo Finance, Banque du Canada, FRED), Moteur de calcul (scenarios 0, 1, 2), Registre de preuves et emplacements EV-nn / KB-nn, Champ explanation construit des evenements tool.call, Principe: le code calcule, le modele cadre et cite, le verificateur controle, Agent Orchestrateur, Validations (tests, smoke, essai bout en bout) (+4 more)

### Community 79 - "e2e_runs.py group"
Cohesion: 0.39
Nodes (8): check_draft(), check_run(), Client, execute(), frame(), main(), run_case(), check()

### Community 80 - "Oublie la ressource en cache ( group"
Cohesion: 0.20
Nodes (3): reset_client(), _create_tables(), dynamo()

### Community 81 - "Couverture des exigences du Da group"
Cohesion: 0.20
Nodes (11): Couverture des exigences du Datathon, Livrable manquant: video de 5 minutes, Nouvelles classes d'actifs (matieres premieres, obligations reel, privilegiees, infrastructures), Tests des personas Amira, Mateo, Robert, R4 not_verified ALTERNATIVE_NOT_APPLICABLE en mode rebalancement, Alerte de concentration sectorielle (R6, 40 %), Fourchettes d'incertitude par bootstrap par blocs (exigence 7), Personas Robert, Mateo, Amira (+3 more)

### Community 82 - "R1 volatility bands (risk prof group"
Cohesion: 0.22
Nodes (10): R1 volatility bands (risk profile from annualized volatility), R6 WARN in all scenarios (flagship alternative is WARN not PASS), Single risk scale: riskTolerance and riskCapacity, Investor profile requires riskTolerance and riskCapacity (Lot C), NOTES WS6 front, Provenance panel (explanation of conclusion), Front SPA README, /chat three-column session page (+2 more)

### Community 83 - "quality.py group"
Cohesion: 0.27
Nodes (3): isolate_cnq_anomaly_and_check_actions(), run_quality_checks(), test_cnq_2022_08_22_anomaly_isolated()

### Community 84 - "Amazon Translate fr-CA avec gl group"
Cohesion: 0.20
Nodes (9): Amazon Translate fr-CA avec glossaire de 54 termes, Correctif moteur: lectures S3 groupees prices_all (34-38 s a 4,2 s), Registre de preuves EV-nn / KB-nn, Kiro conseille, traces vers services AWS, Observabilite Langfuse (OpenTelemetry Strands, fail-open), Boucle d'optimisation (exporter traces, hypothese, worktree, redeployer), Pipeline Guardrail-Orchestrateur-Moteur-Regles-KB-Auditeur-Redacteur-Translate-Verificateur, Redacteur en 4 appels paralleles (+1 more)

### Community 85 - "Limite: faux positifs du Guard group"
Cohesion: 0.29
Nodes (10): Limite: faux positifs du Guardrail et prefixe de contexte, Limites (survivant, FNB non renseignes, fenetre R2, Guardrail), Guardrail: etat, limites et pistes, Prefixe de contexte "In the simulator: ", Faux positifs du Guardrail (tournure vs ticker), Pistes a-f (phrases de video, definition de sujet, banc elargi, Jev, variante A, plan B), Variante A (sujets en sortie seulement, bloquee par provider hashicorp/aws), Piste Jev (TypeSafe) pour le filtre d'entree (+2 more)

### Community 86 - "agent-auditor (KB, citations) group"
Cohesion: 0.20
Nodes (10): agent-auditor (KB, citations), Table DynamoDB Analyses (mandats et runs), Bedrock Knowledge Base réglementaire (S3 Vectors, Titan V2), Langfuse (traçabilité de développement), WS0 / WS0b socle commun, WS1 / WS1b infra Terraform, WS2 / WS2b repositories DynamoDB, WS4 / WS4b Lambda API (+2 more)

### Community 87 - "knowledge-graph.yaml group"
Cohesion: 0.22
Nodes (8): data_schemas, description, fields, id, description, name, required, type

### Community 88 - "universe.yaml group"
Cohesion: 0.22
Nodes (8): asset_class, default_sector, asset_class, candidates, default_sector, categories, canadian_etfs_gold, canadian_etfs_reit

### Community 89 - "asset_class group"
Cohesion: 0.22
Nodes (9): asset_class, candidates, default_sector, asset_class, candidates, default_sector, ticker, canadian_etfs_cash (+1 more)

### Community 90 - "Scénario vedette Robert + NVDA group"
Cohesion: 0.22
Nodes (9): Scénario vedette Robert + NVDA, module-rules (R1-R10), Bandes de volatilité de R1 (hypothèse d'équipe), R2 ne voit pas le krach COVID, Guide de démo : requêtes qui fonctionnent, Scénario ESG Mateo et XOM, Personas de démo robert, amira, mateo, Scénario Robert et son condo (+1 more)

### Community 91 - "Bedrock Guardrail (variante B, group"
Cohesion: 0.22
Nodes (8): Bedrock Guardrail (variante B, version 3 puis 4), Refus de Guardrail expliqué (explain_refusal), Refus voulus du Guardrail à montrer, Formulations à éviter pendant la démo, Profilage session 01 : latence des agents, Le goulot est le LLM (89 % d'un tour de chat), Prompt caching Bedrock (non activé), Piste : profil et portefeuille dans session_context

### Community 92 - "NOTES WS5 Lambda agents group"
Cohesion: 0.25
Nodes (7): NOTES WS5 Lambda agents, Conversation deletion cascade (messages, analyses, conversation), NOTES WS2 db repository assumptions, Analyses table (mandates and runs, sessionId/itemKey), Contract gaps: quickReplies, mandateDraft, runId, userLanguage, Conversations updatedAt-index LSI, etf_enriched.json (15 key ETFs template and validator)

### Community 93 - "test_version_de_corpus_differe group"
Cohesion: 0.39
Nodes (4): test_version_de_corpus_differente_aucune_citation_fixee(), _data(), pinned_for(), register()

### Community 94 - "_new_corpus_result() group"
Cohesion: 0.29
Nodes (5): _new_corpus_result(), test_retrieve_jette_les_passages_non_citables_et_revérifie_citable(), test_section_affichee_et_champs_transportes(), search_regulation(), neutralize()

### Community 95 - "_check_build_preferences() group"
Cohesion: 0.29
Nodes (4): _check_build_preferences(), resolve(), _fix_industry_name(), _industry_key()

### Community 97 - "model_auditor() group"
Cohesion: 0.25
Nodes (4): model_auditor(), model_orchestrator(), model_writer(), test_modele_par_agent()

### Community 98 - "identifiers group"
Cohesion: 0.25
Nodes (8): identifiers, evidenceId, mandateVersion, messageId, portfolioId, runId, sessionId, ticker

### Community 99 - "agent-orchestrator group"
Cohesion: 0.29
Nodes (8): agent-orchestrator, Outil market_stats (modèle à un facteur), module-engine, Flux v0.4 : cadrage, mandat, calcul, règles R1-R10, citations, explication, vérification, WS3 jeu de données élargi, WS5 Lambda agents, Démarrages à froid de la Lambda agents (~5 s), Correctif prices_many (lecture S3 en bloc, moteur 4,2 s)

### Community 100 - "agent-writer group"
Cohesion: 0.25
Nodes (8): agent-writer, Registre de preuves EV-nn et citations KB-nn, module-verifier, Amazon Translate avec terminologie (grow-finance-en-fr), Traduction du run : 2 appels LLM en série (~16 s), Rédacteur en 4 appels parallèles (ws/writer-parallel), Rédacteur : 60 % de raisonnement caché (thinking), Rédacteur : 2 cycles par section dans 8 cas sur 16

### Community 101 - "Banc scripts/e2e_runs.py (15 c group"
Cohesion: 0.25
Nodes (8): Banc scripts/e2e_runs.py (15 cas), Recherche d'industries (101 industries du jeu), Onboarding sans chat (premier portefeuille fictif), Constructeur de portefeuille moyenne-variance (mode build, ws/optimizer), Requêtes de construction de portefeuille (mode build), Profils des comptes de démo supprimés (15 novembre), Libellés d'industrie du front (21 catégories, covers), Échecs de validation des noms d'industrie (propose_mandate)

### Community 102 - "kb_sync.sh group"
Cohesion: 0.29
Nodes (6): kb_sync.sh script, tf_out(), AWS_CONFIG_FILE, AWS_PROFILE, AWS_SHARED_CREDENTIALS_FILE, aws-env.sh script

### Community 103 - "manifest.json group"
Cohesion: 0.29
Nodes (6): periodEnd, periodStart, source, synthetic, tickers, version

### Community 104 - "FakeGuardrail group"
Cohesion: 0.29
Nodes (3): FakeGuardrail, _french_sections(), guard()

### Community 105 - "test_app.py group"
Cohesion: 0.29
Nodes (3): test_corps_json_invalide_est_une_erreur_de_validation(), test_requete_sans_jwt_est_refusee(), test_route_inconnue_recoit_une_erreur_de_validation()

### Community 108 - "query_params group"
Cohesion: 0.29
Nodes (7): query_params, default, description, enum, name, required, type

### Community 109 - "DataFrame group"
Cohesion: 0.29
Nodes (3): _read_prices(), test_compute_1y_indicators_on_fixtures(), test_validate_candidate_prices_rejects_empty_and_short_and_bad_prices()

### Community 110 - "Grow Architecture AWS (dossier group"
Cohesion: 0.33
Nodes (7): Grow Architecture AWS (dossier), Production d'une citation KB (verdicts, recherche en code, selection auditeur, inscription KB-nn), Knowledge Base reglementaire (13 textes, S3 Vectors, passages de 300 tokens), Regles R1 a R10 (annexe), Architecture serverless us-east-1 (CloudFront, Cognito, API Gateway, 2 Lambdas, DynamoDB), Agent Auditeur de convenance, Knowledge Base Bedrock (13 documents reglementaires)

### Community 111 - "Bedrock Guardrail group"
Cohesion: 0.29
Nodes (7): Bedrock Guardrail, Guardrail alphaforge-guardrail version 3 (tier STANDARD, 3 sujets), Defauts reveles par le filtre de sortie (approbation, style adapte au profil), Esquisse d'integration de Jev dans messages.py (remplace sujets sur english_request), Primitives Noul, Choice, Score, Box, Seuils recommandes (0,7 / 0,3) et calibration sur 100-200 exemples, Plan d'essai minimal (banc etiquete de 100 phrases)

### Community 112 - "Asynchronous run completion vi group"
Cohesion: 0.33
Nodes (5): Scenario 2 category comparison (compareCategory, no visible symbol), Verifier: masks numbers and judgement vocabulary, Run chain (engine, rules, auditor, writer, translation, verifier, guardrail), i18n applied to /chat only, SelfInvokeCompleteRun IAM statement and 180s timeout

### Community 113 - "citable filter and fixed citat group"
Cohesion: 0.40
Nodes (4): citable filter and fixed citations for R5 and R9, Code-driven auditor KB searches, KB corpus split by section (build_kb_corpus.py), Bedrock Knowledge Base regulatory (bedrock_kb.tf)

### Community 114 - "Synthetic test fixtures (no Ya group"
Cohesion: 0.33
Nodes (6): Synthetic test fixtures (no Yahoo prices redistributed), NOTES WS3 data implementation precisions, Grow market dataset README (job-ingestion), Data sources: Yahoo Finance, Bank of Canada Valet, FRED, issuer fact sheets, S3 upload to storage-dataset (documented, not executed), Survivorship bias amplified by 10-year window

### Community 115 - "ctx() group"
Cohesion: 0.33
Nodes (3): ctx(), ctx_industries(), relaxed_optimizer()

### Community 116 - "NOTES WS4 api assumptions group"
Cohesion: 0.33
Nodes (5): NOTES WS4 api assumptions, Embedded tickers.json universe validation, Lambda API README (srv-api-light), build_tickers.py regenerate tickers.json, Dataset output layout (manifest, universe, prices, fx, macro, corporate_actions)

### Community 117 - "fixture group"
Cohesion: 0.33
Nodes (4): ticker_validator(), validate(), test_create_mandate_compare_category_choisie_par_l_utilisateur(), post()

### Community 118 - "language_policy group"
Cohesion: 0.33
Nodes (6): language_policy, input, internal_language, output, rule, ui_labels

### Community 120 - "build_lambdas.sh group"
Cohesion: 0.60
Nodes (5): build_lambda(), build_presignup(), check_tickers_json(), pip_install_arm(), build_lambdas.sh script

### Community 123 - "NOTES WS1b infra v0.4 group"
Cohesion: 0.40
Nodes (5): NOTES WS1b infra v0.4, Guardrail false positives to test early, Infrastructure Grow (Terraform) README, Bedrock Guardrail (guardrail.tf), Bedrock inference profile required (global.anthropic.claude-sonnet-5-5)

### Community 124 - "Lambda agents README (srv-agen group"
Cohesion: 0.50
Nodes (4): Lambda agents README (srv-agent-runtime), build_lambdas.sh agents.zip packaging, Static agents registry.json (GET /v1/agents), Terraform workflow (plan by human, apply by one person)

### Community 125 - "test_read_evidence() group"
Cohesion: 0.50
Nodes (3): test_read_evidence(), test_read_evidence_expose_les_verdicts(), read_evidence()

### Community 128 - "asset_class group"
Cohesion: 0.50
Nodes (4): asset_class, candidates, default_sector, canadian_etfs_broad

### Community 129 - "asset_class group"
Cohesion: 0.50
Nodes (4): asset_class, candidates, default_sector, canadian_etfs_esg

### Community 130 - "tsx_equities_communications group"
Cohesion: 0.50
Nodes (4): tsx_equities_communications, asset_class, candidates, default_sector

### Community 131 - "tsx_equities_consumer_discreti group"
Cohesion: 0.50
Nodes (4): tsx_equities_consumer_discretionary, asset_class, candidates, default_sector

### Community 132 - "tsx_equities_consumer_staples group"
Cohesion: 0.50
Nodes (4): tsx_equities_consumer_staples, asset_class, candidates, default_sector

### Community 133 - "tsx_equities_energy group"
Cohesion: 0.50
Nodes (4): tsx_equities_energy, asset_class, candidates, default_sector

### Community 134 - "tsx_equities_financials group"
Cohesion: 0.50
Nodes (4): tsx_equities_financials, asset_class, candidates, default_sector

### Community 135 - "tsx_equities_industrials group"
Cohesion: 0.50
Nodes (4): tsx_equities_industrials, asset_class, candidates, default_sector

### Community 136 - "tsx_equities_materials group"
Cohesion: 0.50
Nodes (4): tsx_equities_materials, asset_class, candidates, default_sector

### Community 137 - "tsx_equities_real_estate group"
Cohesion: 0.50
Nodes (4): tsx_equities_real_estate, asset_class, candidates, default_sector

### Community 138 - "tsx_equities_technology group"
Cohesion: 0.50
Nodes (4): tsx_equities_technology, asset_class, candidates, default_sector

### Community 139 - "tsx_equities_utilities group"
Cohesion: 0.50
Nodes (4): tsx_equities_utilities, asset_class, candidates, default_sector

### Community 140 - "us_equities_communications group"
Cohesion: 0.50
Nodes (4): us_equities_communications, asset_class, candidates, default_sector

### Community 141 - "us_equities_consumer_discretio group"
Cohesion: 0.50
Nodes (4): us_equities_consumer_discretionary, asset_class, candidates, default_sector

### Community 142 - "us_equities_consumer_staples group"
Cohesion: 0.50
Nodes (4): us_equities_consumer_staples, asset_class, candidates, default_sector

### Community 143 - "us_equities_financials group"
Cohesion: 0.50
Nodes (4): us_equities_financials, asset_class, candidates, default_sector

### Community 144 - "us_equities_healthcare group"
Cohesion: 0.50
Nodes (4): us_equities_healthcare, asset_class, candidates, default_sector

### Community 145 - "us_equities_technology group"
Cohesion: 0.50
Nodes (4): us_equities_technology, asset_class, candidates, default_sector

### Community 149 - "id group"
Cohesion: 0.67
Nodes (3): id, mode, access_to_storage

### Community 150 - "workstreams.md (découpage du t group"
Cohesion: 0.67
Nodes (3): workstreams.md (découpage du travail en worktrees), Préambule commun des prompts de chantier, Contrat knowledge-graph.yaml v0.4.x

## Knowledge Gaps
- **117 isolated node(s):** `alphaforge-backend`, `AWS_CONFIG_FILE`, `AWS_SHARED_CREDENTIALS_FILE`, `AWS_PROFILE`, `Datathon PolyFinances 2026 AlphaForge AI` (+112 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1085 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DataStore` connect `Market DataStore` to `Portfolio Optimizer`, `Messages Route & Explanation`, `Scenarios Engine`, `Agents Lambda & Store`, `llm/__init__.py group`, `test_optimize_portfolio_outil( group`, `Evidence Registry`, `.__init__() group`, `Runs Routes`, `Request Handlers`, `Translation of Run`, `Dataset Loading`, `Injecte un magasin (tests, ban group`, `Smoke & Translate Tests`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `ApiError` (e.g. with `propose_mandate()` and `test_le_validateur_reel_refuse_un_ticker_inconnu()`) actually correct?**
  _`ApiError` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `alphaforge-backend`, `AWS_CONFIG_FILE`, `AWS_SHARED_CREDENTIALS_FILE` to the rest of the system?**
  _117 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Evidence & Rule Verdicts` be split into smaller, more focused modules?**
  _Cohesion score 0.04945054945054945 - nodes in this community are weakly interconnected._
- **Why does `ApiError` connect `API Errors & Auth Claims` to `Analyses/Runs Repositories`, `API Lambda & Agents Registry`, `Agents Lambda & Store`, `Runs Routes`, `Request Handlers`, `Market DataStore`, `Conversations Repository`, `Translation of Run`, `DynamoDB Utilities`, `Tickers Builder`, `Users Routes`, `Test Fixtures & Repos`, `Tools Tests`, `Messages Route & Explanation`, `test_optimize_portfolio_outil( group`, `llm/__init__.py group`, `handle_request() group`, `api/routes/__init__.py group`, `body_of() group`, `categories.py group`, `fixture group`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `DataStore` (e.g. with `handle_internal()` and `handle_request()`) actually correct?**
  _`DataStore` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Should `Investor Profile UI` be split into smaller, more focused modules?**
  _Cohesion score 0.06335204490777867 - nodes in this community are weakly interconnected._