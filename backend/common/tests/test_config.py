"""Tests de backend/common/config.py : lecture à l'appel, valeurs manquantes."""

import pytest

import backend.common.config as config


def test_lecture_a_l_appel_et_non_a_l_import(monkeypatch):
    """Changer la variable d'environnement change le résultat : lecture à l'appel."""
    monkeypatch.setenv("USERS_TABLE", "Users-dev")
    assert config.users_table() == "Users-dev"
    monkeypatch.setenv("USERS_TABLE", "Users-prod")
    assert config.users_table() == "Users-prod"


@pytest.mark.parametrize(
    "fonction,nom",
    [
        (config.users_table, "USERS_TABLE"),
        (config.conversations_table, "CONVERSATIONS_TABLE"),
        (config.messages_table, "MESSAGES_TABLE"),
        (config.portfolios_table, "PORTFOLIOS_TABLE"),
        (config.analyses_table, "ANALYSES_TABLE"),
        (config.dataset_bucket, "DATASET_BUCKET"),
        (config.dataset_version, "DATASET_VERSION"),
    ],
)
def test_variables_requises_absentes(monkeypatch, fonction, nom):
    monkeypatch.delenv(nom, raising=False)
    with pytest.raises(config.MissingEnvVar, match=nom):
        fonction()


def test_variables_requises_presentes(monkeypatch):
    monkeypatch.setenv("CONVERSATIONS_TABLE", "Conversations-dev")
    monkeypatch.setenv("MESSAGES_TABLE", "Messages-dev")
    monkeypatch.setenv("PORTFOLIOS_TABLE", "Portfolios-dev")
    monkeypatch.setenv("ANALYSES_TABLE", "Analyses-dev")
    monkeypatch.setenv("DATASET_BUCKET", "bucket-dev")
    monkeypatch.setenv("DATASET_VERSION", "2026-11-12")
    assert config.conversations_table() == "Conversations-dev"
    assert config.messages_table() == "Messages-dev"
    assert config.portfolios_table() == "Portfolios-dev"
    assert config.analyses_table() == "Analyses-dev"
    assert config.dataset_bucket() == "bucket-dev"
    assert config.dataset_version() == "2026-11-12"


@pytest.mark.parametrize(
    "fonction,nom",
    [
        (config.model_orchestrator, "MODEL_ORCHESTRATOR"),
        (config.model_auditor, "MODEL_AUDITOR"),
        (config.model_writer, "MODEL_WRITER"),
        (config.kb_id, "KB_ID"),
        (config.guardrail_id, "GUARDRAIL_ID"),
        (config.guardrail_version, "GUARDRAIL_VERSION"),
        (config.rules_config_path, "RULES_CONFIG_PATH"),
    ],
)
def test_variables_optionnelles(monkeypatch, fonction, nom):
    """Modèles, KB, Guardrail, seuils : None tant que non configurés, lus à l'appel."""
    monkeypatch.delenv(nom, raising=False)
    assert fonction() is None
    monkeypatch.setenv(nom, "valeur-test")
    assert fonction() == "valeur-test"


def test_modele_par_agent(monkeypatch):
    """Contrat v0.4.0 : un modèle par agent, ex. Claude Sonnet 5.5 en us-east-1."""
    monkeypatch.setenv("MODEL_ORCHESTRATOR", "global.anthropic.claude-sonnet-5-5")
    monkeypatch.setenv("MODEL_AUDITOR", "global.anthropic.claude-sonnet-5-5")
    monkeypatch.setenv("MODEL_WRITER", "global.anthropic.claude-sonnet-5-5")
    assert config.model_orchestrator() == config.model_auditor() == config.model_writer()


def test_log_level_par_defaut(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert config.log_level() == "INFO"
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert config.log_level() == "DEBUG"
