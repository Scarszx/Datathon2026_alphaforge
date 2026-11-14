# Corpus de la Knowledge Base

Documents réglementaires et publics pour l'auditeur. Récupérés le 2026-11-14.

Chaque fichier a un `<fichier>.metadata.json` au format des métadonnées de Bedrock Knowledge Bases. Le champ `juridiction` (`CA`, `QC`, `ON`, `SK`) permet de filtrer sur `CA` plus la province de l'utilisateur.

| Fichier | Juridiction | Régulateur | Sujets | Version | Langue | Source |
|---|---|---|---|---|---|---|
| `CA_31-368_avis-ACVM-OCRI_2025-12-10_fr.pdf` | CA | ACVM-OCRI | kyc, profil_risque, convenance | 2025-12-10 | fr | [lien](https://fcnb.ca/sites/default/files/2025-12/2025-12-10-Avis%20conjoint%20des%20ACVM-OCRI-31-368.pdf) |
| `CA_31-368_notice-CSA-CIRO_2025-12-10_en.pdf` | CA | ACVM-OCRI | kyc, profil_risque, convenance | 2025-12-10 | en | [lien](https://www.asc.ca/-/media/ASC-Documents-part-1/Regulatory-Instruments/2025/12/6255537-CSA-CIRO-Notice-31-368-Client-Focused-Reforms.pdf) |
| `CA_31-103_reglement-officiel-consolide_2026-07-04_fr.pdf` | CA | ACVM-AMF | kyc, convenance, reglement | 2026-07-04 | fr | [lien](https://lautorite.qc.ca/fileadmin/lautorite/reglementation/valeurs-mobilieres/31-103/2026-07-04/2026juil04-31-103-vofficielle-fr.pdf) |
| `CA_31-103CP_instruction-consolidee_2026-01-01_en.pdf` | CA | ACVM | kyc, convenance, instruction | 2026-01-01 | en | [lien](https://fcnb.ca/sites/default/files/2026-01/31-103-CONS-CP-2026-01-01_0.pdf) |
| `CA_CIRO_GN-3200-26-001_guidance-OEO_2026-03-12_en.txt` | CA | OCRI | oeo, aide_decision, recommandation | 2026-03-12 | en | [lien](https://www.ciro.ca/newsroom/publications/guidance-order-execution-only-account-services-and-activities) |
| `CA_OCRI_GN-3200-26-001_note-orientation-OEO_2026-03-12_fr.txt` | CA | OCRI | oeo, aide_decision, recommandation | 2026-03-12 | fr | [lien](https://www.ocri.ca/salle-de-presse/publications/note-dorientation-sur-les-services-et-les-activites-dexecution-dordres-sans-conseils-2) |
| `CA_CIRO_bulletin-26-0059_OEO_2026-03-12_en.txt` | CA | OCRI | oeo | 2026-03-12 | en | [lien](https://www.ciro.ca/newsroom/publications/new-guidance-order-execution-only-account-services-and-activities) |
| `CA_81-334_avis-ESG-fonds_2024-03-07_en.pdf` | CA | ACVM | esg, fonds | 2024-03-07 | en | [lien](https://OSC.gov.on.ca/sites/default/files/2024-03/20240307_81-334_sn-related-investment-fund-disclosure.pdf) |
| `CA_21-329_avis-plateformes-crypto_2021-03-29_en.pdf` | CA | ACVM-OCRI | crypto | 2021-03-29 | en | [lien](https://www.bcsc.bc.ca/-/media/PWS/New-Resources/Securities-Law/Instruments-and-Policies/Policy-2/21329-CSA-and--IIROC-Staff-Notice-March-29-2021.pdf) |
| `CA_21-332_avis-plateformes-crypto-PRU_2023-02-22_en.pdf` | CA | ACVM | crypto | 2023-02-22 | en | [lien](https://www.asc.ca/en/securities-law-and-policy/-/media/81AC364F57D44E2CABF1A5B6F4519E33.ashx) |
| `ON_FSRA_regle-2020-001-protection-titres_en.pdf` | ON | FSRA | titres_proteges | 2022-03-28 | en | [lien](https://fsrao.ca/media/11436/download) |
| `SK_FCAA_reglement-FPFA-avis_en.pdf` | SK | FCAA | titres_proteges | 2022 | en | [lien](https://fcaa.gov.sk.ca/public/CKeditorUpload/Notice_of_Proposed_Reg_and_Request_for_Comment_for_FPFA_Regulations_FINAL.v2.pdf) |
| `QC_AMF_planification-financiere-titre_fr.txt` | QC | AMF | titres_proteges | 2026-11-14 | fr | [lien](https://lautorite.qc.ca/devenir-professionnel/planification-financiere) |
| `QC_BNCD_questions-avant-investir_fr.txt` | QC | BNCD | cadrage, questions_investisseur | 2020-12-16 | fr | [lien](https://www.nbc.ca/fr/courtage-direct/centre-educatif/debuter-investissement-autonome/creer-plan-investissement/questions-avant-investir.html) |
| `QC_BNCD_info-relation-clients_fr.pdf` | QC | BNCD | oeo, relation_client | 2025-09 | fr | [lien](https://www.nbc.ca/content/dam/shared/pdf/brokerage/17230-7-bncd-info-relation-clients.pdf) |

## Notes

- Les fichiers `.txt` de l'OCRI, de l'AMF et de BNCD sont le texte des pages web, extrait par navigateur. La source et la date sont en tête de chaque fichier.
- `CA_31-103CP_instruction-consolidee_2026-01-01_en.pdf` est une consolidation non officielle (FCNB). Le règlement 31-103 en français est la version officielle de l'AMF.
- Pour 31-103, n'indexer que les articles 13.2 (connaissance du client) et 13.3 (convenance) si la recherche est trop bruitée.
- Saskatchewan : seul l'avis de projet de règlement a été trouvé. Le statut final reste à vérifier sur le site de la FCAA.
- Conditions de réutilisation à vérifier pour chaque site avant toute redistribution.
