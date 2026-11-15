"""Tests de POST /v1/speech/session : signature locale, aucun appel AWS."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest
from botocore.credentials import ReadOnlyCredentials

from backend.api.app import handle_request
from backend.api.routes import speech

from .conftest import body_of, event

ROUTE = "POST /v1/speech/session"


@pytest.fixture(autouse=True)
def faux_identifiants(monkeypatch):
    monkeypatch.setattr(
        speech,
        "_credentials",
        lambda: ReadOnlyCredentials("AKIAFAKEFAKEFAKEFAKE", "secret-factice", "jeton-factice"),
    )
    monkeypatch.setenv("AWS_REGION", "us-east-1")


def _query(response):
    return parse_qs(urlsplit(body_of(response)["url"]).query)


def test_session_fr_par_defaut_sans_corps():
    response = handle_request(event(ROUTE))
    assert response["statusCode"] == 200
    body = body_of(response)
    assert body["languageCode"] == "fr-CA"
    assert body["languageOptions"] == ["fr-CA", "en-US"]
    assert body["sampleRate"] == 16000
    assert body["expiresIn"] == 300
    assert body["url"].startswith(
        "wss://transcribestreaming.us-east-1.amazonaws.com:8443/stream-transcription-websocket?"
    )


def test_url_signee_avec_les_parametres_attendus():
    response = handle_request(event(ROUTE, body={"lang": "en"}))
    assert response["statusCode"] == 200
    assert body_of(response)["languageCode"] == "en-US"
    q = _query(response)
    assert "language-code" not in q  # remplacé par la détection de la langue
    assert q["identify-language"] == ["true"]
    assert q["language-options"] == ["fr-CA,en-US"]
    assert q["preferred-language"] == ["en-US"]
    assert body_of(response)["languageOptions"] == ["fr-CA", "en-US"]
    assert q["media-encoding"] == ["pcm"]
    assert q["sample-rate"] == ["16000"]
    assert q["X-Amz-Expires"] == ["300"]
    assert q["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert q["X-Amz-Signature"][0]
    assert q["X-Amz-Security-Token"] == ["jeton-factice"]
    assert "transcribe/aws4_request" in q["X-Amz-Credential"][0]


def test_la_region_vient_de_l_environnement(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ca-central-1")
    url = body_of(handle_request(event(ROUTE)))["url"]
    assert "transcribestreaming.ca-central-1.amazonaws.com" in url
    assert "ca-central-1%2Ftranscribe" in url


@pytest.mark.parametrize("body", [{"lang": "de"}, {"lang": 3}, {"langue": "fr"}, {"lang": "fr", "x": 1}])
def test_corps_invalide_refuse(body):
    response = handle_request(event(ROUTE, body=body))
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"


def test_sans_jwt_refuse():
    assert handle_request(event(ROUTE, claims=None))["statusCode"] == 401
