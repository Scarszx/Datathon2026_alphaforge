# Corpus de la Knowledge Base

Documents réglementaires et publics utilisés par l'auditeur. **Tout le corpus est en anglais**, pour avoir une seule langue. Récupérés le 2026-11-14.

Chaque fichier a un `<fichier>.metadata.json` au format des métadonnées de Bedrock Knowledge Bases. Le champ `juridiction` (`CA`, `QC`, `ON`, `SK`) permet de filtrer sur `CA` plus la province de l'utilisateur. Les valeurs de `sujets` restent les clés convenues dans le contrat (`profil_risque`, `convenance`, `oeo`, `esg`, `crypto`, `titres_proteges`…).

| Fichier | Juridiction | Régulateur | Sujets | Version | Source |
|---|---|---|---|---|---|
| `CA_31-368_staff-notice-CSA-CIRO_2025-12-10_en.pdf` | CA | CSA-CIRO | kyc, profil_risque, convenance | 2025-12-10 | [lien](https://www.asc.ca/-/media/ASC-Documents-part-1/Regulatory-Instruments/2025/12/6255537-CSA-CIRO-Notice-31-368-Client-Focused-Reforms.pdf) |
| `CA_31-103_regulation-official-consolidated_2026-07-04_en.pdf` | CA | CSA-AMF | kyc, convenance, reglement | 2026-07-04 | [lien](https://lautorite.qc.ca/fileadmin/lautorite/reglementation/valeurs-mobilieres/31-103/2026-07-04/2026juil04-31-103-vofficielle-en.pdf) |
| `CA_31-103CP_companion-policy-consolidated_2026-01-01_en.pdf` | CA | CSA | kyc, convenance, instruction | 2026-01-01 | [lien](https://fcnb.ca/sites/default/files/2026-01/31-103-CONS-CP-2026-01-01_0.pdf) |
| `CA_CIRO_GN-3200-26-001_OEO-guidance_2026-03-12_en.txt` | CA | CIRO | oeo, aide_decision, recommandation | 2026-03-12 | [lien](https://www.ciro.ca/newsroom/publications/guidance-order-execution-only-account-services-and-activities) |
| `CA_CIRO_bulletin-26-0059_OEO_2026-03-12_en.txt` | CA | CIRO | oeo | 2026-03-12 | [lien](https://www.ciro.ca/newsroom/publications/new-guidance-order-execution-only-account-services-and-activities) |
| `CA_81-334_staff-notice-ESG-funds_2024-03-07_en.pdf` | CA | CSA | esg, fonds | 2024-03-07 | [lien](https://OSC.gov.on.ca/sites/default/files/2024-03/20240307_81-334_sn-related-investment-fund-disclosure.pdf) |
| `CA_21-329_staff-notice-crypto-platforms_2021-03-29_en.pdf` | CA | CSA-IIROC | crypto | 2021-03-29 | [lien](https://www.bcsc.bc.ca/-/media/PWS/New-Resources/Securities-Law/Instruments-and-Policies/Policy-2/21329-CSA-and--IIROC-Staff-Notice-March-29-2021.pdf) |
| `CA_21-332_staff-notice-crypto-platforms-PRU_2023-02-22_en.pdf` | CA | CSA | crypto | 2023-02-22 | [lien](https://www.asc.ca/en/securities-law-and-policy/-/media/81AC364F57D44E2CABF1A5B6F4519E33.ashx) |
| `ON_FSRA_rule-2020-001-title-protection_en.pdf` | ON | FSRA | titres_proteges | 2022-03-28 | [lien](https://fsrao.ca/media/11436/download) |
| `SK_FCAA_FPFA-proposed-regulations-notice_en.pdf` | SK | FCAA | titres_proteges | 2022 | [lien](https://fcaa.gov.sk.ca/public/CKeditorUpload/Notice_of_Proposed_Reg_and_Request_for_Comment_for_FPFA_Regulations_FINAL.v2.pdf) |
| `QC_AMF_financial-planner-title_en.txt` | QC | AMF | titres_proteges | 2026-11-14 | [lien](https://lautorite.qc.ca/en/becoming-a-professional/financial-planning) |
| `QC_NBDB_tips-better-investment-decisions_en.txt` | QC | NBDB | cadrage, questions_investisseur | 2018-10-01 | [lien](https://www.nbc.ca/en/direct-brokerage/learning-centre/start-self-directed-investment/creating-investment-plan/tips-for-making-better-investment-decisions.html) |
| `QC_NBDB_relationship-disclosure-information_2025-09_en.pdf` | QC | NBDB | oeo, relation_client | 2025-09-02 | [lien](https://www.nbc.ca/content/dam/shared/pdf/brokerage/17230-7-nbdb-relationship-disclosure-information.pdf) |

## Notes

- Les fichiers `.txt` (CIRO, AMF, NBDB) sont le texte des pages web, extrait avec un navigateur. La source et la date sont en tête de chaque fichier.
- `CA_31-103_regulation-official-consolidated_2026-07-04_en.pdf` est la version anglaise publiée par l'AMF (« official status »). `CA_31-103CP_…` est une consolidation non officielle (FCNB).
- `QC_NBDB_tips-better-investment-decisions_en.txt` remplace la page française « Les questions à se poser avant d'investir ». Sa page anglaise jumelle (« How to start investing ») traite d'un autre sujet. Celle-ci liste les questions de cadrage : objectifs, horizon, confort avec le risque, diversification, fréquence des transactions.
- Pour 31-103 (165 pages), n'indexer que les articles 13.2 (connaissance du client) et 13.3 (convenance) si la recherche est trop bruitée.
- Saskatchewan : seul l'avis de projet de règlement a été trouvé. Le statut final reste à vérifier sur le site de la FCAA.
- Conditions de réutilisation à vérifier pour chaque site avant toute redistribution.
