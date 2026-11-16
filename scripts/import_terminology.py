#!/usr/bin/env python3
"""Importe (ou remplace) la terminologie Amazon Translate « grow-finance-en-fr » dans le compte de l'événement.

À lancer par un humain, une fois, avec les identifiants du projet chargés dans la MÊME commande :

    source scripts/aws-env.sh && .venv/bin/python scripts/import_terminology.py

Sans cette terminologie, la traduction du run fonctionne quand même, avec un vocabulaire moins juste.
Nom différent : TRANSLATE_TERMINOLOGY=autre-nom (la même valeur doit être posée sur la Lambda agents).
Le script vérifie le compte avant d'écrire et s'arrête s'il n'est pas celui de l'événement.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import boto3

EVENT_ACCOUNT = "058264316309"
REGION = "us-east-1"
DEFAULT_NAME = "grow-finance-en-fr"
CSV = Path(__file__).resolve().parents[1] / "backend" / "agents" / "translate" / "terminology" / "grow-finance-en-fr.csv"


def main() -> int:
    name = (os.environ.get("TRANSLATE_TERMINOLOGY") or DEFAULT_NAME).strip()
    account = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
    if account != EVENT_ACCOUNT:
        print(f"Compte {account} : ce n'est pas le compte de l'événement ({EVENT_ACCOUNT}). Rien n'a été importé.", file=sys.stderr)
        return 1
    client = boto3.client("translate", region_name=REGION)
    response = client.import_terminology(
        Name=name,
        MergeStrategy="OVERWRITE",
        Description="Vocabulaire financier de Grow (en vers fr-CA), non relu par un spécialiste",
        TerminologyData={"File": CSV.read_bytes(), "Format": "CSV", "Directionality": "UNI"},
    )
    props = response["TerminologyProperties"]
    print(f"Terminologie {props['Name']} importée : {props.get('TermCount')} termes, "
          f"{props.get('SourceLanguageCode')} vers {props.get('TargetLanguageCodes')}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
