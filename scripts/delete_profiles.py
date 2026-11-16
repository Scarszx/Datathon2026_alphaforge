#!/usr/bin/env python3
"""Supprime le profil investisseur (attribut `investorProfile`) de tous les utilisateurs de la table Users.

Usage (depuis la racine du dépôt, venv activé) :
    source scripts/aws-env.sh && python scripts/delete_profiles.py            # simulation : liste seulement
    source scripts/aws-env.sh && python scripts/delete_profiles.py --apply    # supprime

- Seul `investorProfile` est retiré : les comptes (Cognito, lignes Users), les portefeuilles, les conversations
  et les mandats ne sont pas touchés. L'utilisateur revoit le questionnaire à sa prochaine connexion.
- Sert à la migration des industries (les anciens libellés français ne sont plus reconnus).
- Affiche le nombre de profils par utilisateur, jamais leur contenu.
"""

from __future__ import annotations

import argparse

import boto3

REGION = "us-east-1"
TABLE = "Users"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="supprimer réellement (sinon simulation)")
    args = parser.parse_args()
    table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)
    items, kwargs = [], {"ProjectionExpression": "userId, username, investorProfile"}
    while True:
        page = table.scan(**kwargs)
        items += page["Items"]
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    with_profile = [i for i in items if i.get("investorProfile")]
    print(f"{len(items)} utilisateurs, {len(with_profile)} avec un profil.")
    for item in with_profile:
        print(f"  - {item.get('username')} ({item['userId']})")
        if args.apply:
            table.update_item(Key={"userId": item["userId"]}, UpdateExpression="REMOVE investorProfile",
                              ConditionExpression="attribute_exists(userId)")
    print("Profils supprimés." if args.apply and with_profile else "Simulation : rien n'a été modifié." if not args.apply else "Rien à supprimer.")


if __name__ == "__main__":
    main()
