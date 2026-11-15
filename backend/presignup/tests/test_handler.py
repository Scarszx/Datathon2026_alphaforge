from backend.presignup.handler import handler


def test_auto_confirme_sans_verifier_le_courriel():
    event = {
        "triggerSource": "PreSignUp_SignUp",
        "request": {"userAttributes": {"email": "a@b.ca"}},
        "response": {"autoConfirmUser": False, "autoVerifyEmail": False},
    }
    out = handler(event, None)
    assert out["response"]["autoConfirmUser"] is True
    assert out["response"]["autoVerifyEmail"] is False
