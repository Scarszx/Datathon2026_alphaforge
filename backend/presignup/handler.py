"""Déclencheur Cognito « pre sign-up » : confirme le compte à l'inscription.

Aucun code de confirmation n'est envoyé par courriel : `SignUp` renvoie
`UserConfirmed: true` et le front connecte l'utilisateur tout de suite.
Le courriel n'est pas marqué comme vérifié (pas d'`autoVerifyEmail`).
"""


def handler(event, context):
    event["response"]["autoConfirmUser"] = True
    return event
