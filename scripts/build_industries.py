#!/usr/bin/env python3
"""Génère `frontend/src/lib/industries.json` : les industries proposées par la recherche du front.

Contenu : les industries des candidats de l'optimiseur (`optimizer.candidate_universe` :
actions avec industrie, cotées dans la devise de l'optimiseur), avec leur nom exact du jeu (`en`,
valeur stockée dans `preferences` et transmise à l'agent) et une traduction française (`fr`, affichage
et recherche). Lecture seule sur le jeu de données ; seul le JSON du front est écrit.

Usage (depuis la racine du dépôt, venv activé) :
    python scripts/build_industries.py
    python scripts/build_industries.py --universe /chemin/vers/universe.parquet

Le script échoue si une industrie n'a pas de traduction, ou si une traduction n'a plus d'industrie.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))

from backend.agents.engine import optimizer  # noqa: E402

DEFAULT_UNIVERSE = CODE_ROOT / "data" / "output" / "2026-11-15" / "universe.parquet"
OUTPUT = CODE_ROOT / "frontend" / "src" / "lib" / "industries.json"

FR = {
    "Advertising Agencies": "Agences de publicité",
    "Aerospace & Defense": "Aérospatiale et défense",
    "Airlines": "Compagnies aériennes",
    "Apparel Manufacturing": "Fabrication de vêtements",
    "Apparel Retail": "Commerce de détail de vêtements",
    "Asset Management": "Gestion d'actifs",
    "Auto & Truck Dealerships": "Concessionnaires automobiles et de camions",
    "Auto Manufacturers": "Constructeurs automobiles",
    "Auto Parts": "Pièces automobiles",
    "Banks - Diversified": "Banques diversifiées",
    "Banks - Regional": "Banques régionales",
    "Beverages - Brewers": "Boissons – brasseurs",
    "Beverages - Non-Alcoholic": "Boissons non alcoolisées",
    "Biotechnology": "Biotechnologie",
    "Building Materials": "Matériaux de construction",
    "Building Products & Equipment": "Produits et équipements de construction",
    "Capital Markets": "Marchés financiers",
    "Chemicals": "Produits chimiques",
    "Communication Equipment": "Équipements de communication",
    "Computer Hardware": "Matériel informatique",
    "Confectioners": "Confiserie",
    "Conglomerates": "Conglomérats",
    "Consulting Services": "Services de conseil",
    "Consumer Electronics": "Électronique grand public",
    "Copper": "Cuivre",
    "Credit Services": "Services de crédit",
    "Diagnostics & Research": "Diagnostics et recherche",
    "Discount Stores": "Magasins à prix réduit",
    "Drug Manufacturers - General": "Fabricants de médicaments – grandes sociétés",
    "Drug Manufacturers - Specialty & Generic": "Fabricants de médicaments – spécialité et génériques",
    "Electrical Equipment & Parts": "Équipements et pièces électriques",
    "Electronic Components": "Composants électroniques",
    "Electronic Gaming & Multimedia": "Jeux électroniques et multimédia",
    "Engineering & Construction": "Ingénierie et construction",
    "Entertainment": "Divertissement",
    "Farm & Heavy Construction Machinery": "Machinerie agricole et de construction lourde",
    "Farm Products": "Produits agricoles",
    "Financial Data & Stock Exchanges": "Données financières et bourses",
    "Food Distribution": "Distribution alimentaire",
    "Footwear & Accessories": "Chaussures et accessoires",
    "Gold": "Or",
    "Grocery Stores": "Épiceries",
    "Health Information Services": "Services d'information sur la santé",
    "Healthcare Plans": "Régimes de soins de santé",
    "Home Improvement Retail": "Rénovation domiciliaire (détail)",
    "Household & Personal Products": "Produits ménagers et de soins personnels",
    "Industrial Distribution": "Distribution industrielle",
    "Information Technology Services": "Services de technologies de l'information",
    "Insurance - Diversified": "Assurance diversifiée",
    "Insurance - Life": "Assurance vie",
    "Insurance - Property & Casualty": "Assurance de dommages",
    "Insurance Brokers": "Courtiers d'assurance",
    "Integrated Freight & Logistics": "Fret et logistique intégrés",
    "Internet Content & Information": "Contenu et information sur Internet",
    "Internet Retail": "Commerce de détail en ligne",
    "Lodging": "Hébergement",
    "Luxury Goods": "Produits de luxe",
    "Medical Care Facilities": "Établissements de soins médicaux",
    "Medical Devices": "Dispositifs médicaux",
    "Medical Distribution": "Distribution médicale",
    "Medical Instruments & Supplies": "Instruments et fournitures médicaux",
    "Oil & Gas E&P": "Pétrole et gaz – exploration et production",
    "Oil & Gas Equipment & Services": "Pétrole et gaz – équipements et services",
    "Oil & Gas Integrated": "Pétrole et gaz – intégrés",
    "Oil & Gas Midstream": "Pétrole et gaz – transport et stockage",
    "Oil & Gas Refining & Marketing": "Pétrole et gaz – raffinage et commercialisation",
    "Packaged Foods": "Aliments emballés",
    "Packaging & Containers": "Emballages et contenants",
    "Pollution & Treatment Controls": "Contrôle de la pollution et traitement",
    "REIT - Diversified": "FPI – diversifiés",
    "REIT - Healthcare Facilities": "FPI – établissements de santé",
    "REIT - Industrial": "FPI – industriels",
    "REIT - Residential": "FPI – résidentiels",
    "REIT - Retail": "FPI – commerciaux",
    "REIT - Specialty": "FPI – spécialisés",
    "Railroads": "Chemins de fer",
    "Real Estate Services": "Services immobiliers",
    "Rental & Leasing Services": "Services de location",
    "Residential Construction": "Construction résidentielle",
    "Resorts & Casinos": "Centres de villégiature et casinos",
    "Restaurants": "Restaurants",
    "Scientific & Technical Instruments": "Instruments scientifiques et techniques",
    "Semiconductor Equipment & Materials": "Équipements et matériaux pour semi-conducteurs",
    "Semiconductors": "Semi-conducteurs",
    "Software - Application": "Logiciels – applications",
    "Software - Infrastructure": "Logiciels – infrastructure",
    "Specialty Business Services": "Services aux entreprises spécialisés",
    "Specialty Chemicals": "Produits chimiques de spécialité",
    "Specialty Industrial Machinery": "Machinerie industrielle spécialisée",
    "Specialty Retail": "Commerce de détail spécialisé",
    "Steel": "Acier",
    "Telecom Services": "Services de télécommunications",
    "Tobacco": "Tabac",
    "Travel Services": "Services de voyage",
    "Trucking": "Camionnage",
    "Utilities - Diversified": "Services publics diversifiés",
    "Utilities - Independent Power Producers": "Services publics – producteurs d'électricité indépendants",
    "Utilities - Regulated Electric": "Services publics – électricité réglementée",
    "Utilities - Regulated Gas": "Services publics – gaz réglementé",
    "Utilities - Regulated Water": "Services publics – eau réglementée",
    "Waste Management": "Gestion des déchets",
}


def candidate_industries(universe_path: Path) -> list[str]:
    universe = pd.read_parquet(universe_path)
    candidates = optimizer.candidate_universe(universe, optimizer.load_config())
    return sorted(set(candidates["industry"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE, help="universe.parquet du jeu déployé")
    args = parser.parse_args()
    industries = candidate_industries(args.universe)
    missing = [i for i in industries if i not in FR]
    orphan = [i for i in FR if i not in industries]
    if missing or orphan:
        sys.exit(f"Traductions manquantes : {missing} ; traductions sans industrie : {orphan}")
    rows = [{"en": i, "fr": FR[i]} for i in industries]
    OUTPUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rows)} industries écrites dans {OUTPUT.relative_to(CODE_ROOT)}")


if __name__ == "__main__":
    main()
