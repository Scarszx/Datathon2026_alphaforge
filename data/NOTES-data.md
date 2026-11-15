# NOTES WS3 (data) : précisions d'implémentation par rapport au contrat

Le contrat `contract/knowledge-graph.yaml` (v0.4.0, commit `ccb6e40`) fait foi. Voici les précisions techniques retenues pour l'implémentation de `job-ingestion` (`storage-dataset`) :

1. **Homogénéité des conventions de nommage (Parquet en `snake_case`, JSON en `camelCase`)** :
   - **Fichiers Parquet (`universe.parquet`, `prices/*.parquet`, `prices_all/year=YYYY/*.parquet`, `fx/usdcad.parquet`, `macro/macro.parquet`, `corporate_actions.parquet`)** : toutes les colonnes sont en `snake_case`, comme dans le jeu de départ :
     - `universe.parquet` : `asset_id, ticker, name, asset_class, market, currency, sector, sector_source, first_date, last_date, return_1y, volatility_1y, max_drawdown_1y`.
     - `macro/macro.parquet` : `date, series_id, value, unit, frequency, label, source, publication_date`.
     - `corporate_actions.parquet` : `ex_date, ticker, action, value, unit, anomaly_note`.
   - **Fichiers JSON (`manifest.json`, `etf_enriched.json`)** : toutes les clés sont en `camelCase` (`firstDate`, `firstDateByTicker`, `retainedTickers`, `excludedTickers`, `publicationDateRule`, `sectorWeights`, `topHoldings`, `countryWeights`, `merPct`, `sourceUrl`, `asOfDate`), conformément à `conventions.format` du contrat.

2. **Règle prudente de `publication_date` pour les séries macro mensuelles (R10)** :
   - Le contrat stipule que `macro.parquet` porte une colonne `publication_date` pour les séries mensuelles (`STATIC_TOTALCPICHANGE`, `CPIAUCSL`, `UNRATE`) afin qu'aucune valeur ne soit utilisée avant sa publication réelle.
   - Ces séries étant datées au 1er jour du mois de référence (`YYYY-MM-01`), nous fixons `publication_date` au **28 du mois suivant le mois de référence** (`YYYY-(MM+1)-28`).
   - Il s'agit d'une **approximation prudente** choisie pour couvrir les publications tardives de l'IPC canadien après le 20 du mois suivant (ex. IPC de mai 2024 publié le 25 juin 2024) ainsi que les retards de publication américains (ex. fermeture du gouvernement fédéral à l'automne 2025).
   - Les séries journalières et ouvrées (`V39079`, `BD.CDN.2YR.DQ.YLD`, `BD.CDN.10YR.DQ.YLD`, `DFF`, `DGS2`, `DGS10`) conservent `publication_date = date`.

3. **Gabarit et validation de `etf_enriched.json`** :
   - Conformément à la consigne « N'invente aucune valeur », `data/ingestion/etf_enriched.source.json` fournit le gabarit structuré pour les 15 FNB clés (`XIU.TO`, `SPY`, `QQQ`, `ESGV`, `XBB.TO`, `ZST.TO`, `AGG`, `TLT`, `GLD`, `XSP.TO`, `ZEQT.TO`, `XEQT.TO`, `VFV.TO`, `ZAG.TO`, `XIC.TO`).
   - Le validateur (`validate_etf_enriched`) contrôle la somme des poids (`sectorWeights` et `countryWeights` dans `[95 %, 105 %]`), le nombre de `topHoldings` (5 à 10), la présence de `sourceUrl` et `asOfDate` (`YYYY-MM-DD`), la présence d'`exclusions` pour `ESGV`, et interdit toute action (`equity`).
   - Tant qu'une fiche du gabarit n'a pas été remplie par un humain (ou pour tous les autres FNB de l'univers hors des 15 FNB clés), l'entrée produite dans `etf_enriched.json` porte `"compositionAvailable": false` et `"status": "composition non disponible"`.

4. **Couverture du taux de change (relevé à la vérification de WS3, 2026-11-14)** :
   - `fx/usdcad.parquet` commence le `2017-01-03` (début de la série `FXUSDCAD` de la Banque du Canada), alors que les prix commencent le `2016-11-12`. Environ 3 250 lignes en USD de novembre et décembre 2016 n'ont pas de taux pour la conversion en CAD.
   - Choix retenu : ne pas combler ni mélanger une autre source de taux. Le moteur de calcul (WS5) ne convertit en CAD qu'à partir du `2017-01-03`.
   - À faire lors de la prochaine exécution du mode complet (relance avec les fiches FNB et `--strict-etf`) : écrire ce début de couverture dans `manifest.json`, par exemple `fxCoverageStart: "2017-01-03"`.
