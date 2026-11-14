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
    monkeypatch.setenv("DATASET_BUCKET", "bucket-dev")
    monkeypatch.setenv("DATASET_VERSION", "2026-11-12")
    assert config.conversations_table() == "Conversations-dev"
    assert config.messages_table() == "Messages-dev"
    assert config.portfolios_table() == "Portfolios-dev"
    assert config.dataset_bucket() == "bucket-dev"
    assert config.dataset_version() == "2026-11-12"


def test_modeles_optionnels(monkeypatch):
    """Modèles Bedrock : A_CHOISIR dans le contrat, None tant que non configuré."""
    for nom in ("MODEL_ORCHESTRATOR", "MODEL_ANALYST", "MODEL_GOVERNANCE"):
        monkeypatch.delenv(nom, raising=False)
    assert config.model_orchestrator() is None
    assert config.model_analyst() is None
    assert config.model_governance() is None
    monkeypatch.setenv("MODEL_ANALYST", "anthropic.claude-3-5-sonnet-20241022")
    assert config.model_analyst() == "anthropic.claude-3-5-sonnet-20241022"


def test_log_level_par_defaut(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert config.log_level() == "INFO"
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert config.log_level() == "DEBUG"
