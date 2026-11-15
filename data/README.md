# Jeu de données de marché Grow (`data/`, chantier WS3)

Ce dossier contient le pipeline d'ingestion reproductible (`job-ingestion`) qui produit le jeu de données élargi (~250 actifs sur 10 ans) au format de la section `storage` (`storage-dataset`) du contrat `contract/knowledge-graph.yaml`.

> **Règle git :** rien dans `data/output/` n'est commité (ignoré par `.gitignore`). Seuls le code d'ingestion (`data/ingestion/`), les mini-fixtures de test (`data/fixtures/`), les tests unitaires (`data/tests/`) et la documentation sont suivis par git.

---

## 1. Installation et régénération

### Créer l'environnement virtuel (Python 3.12)

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r data/requirements.txt
```

### Exécuter les tests unitaires (hors ligne, sans réseau ni AWS)

```bash
.venv/bin/pytest data/tests -v
```

### Mode hors ligne (à partir du jeu de départ `alphaforge_starter`)

Produit l'arborescence complète (`manifest.json`, `universe.parquet`, `prices/{ticker}.parquet`, `prices_all/year=YYYY/`, `fx/usdcad.parquet`, `macro/macro.parquet`, `corporate_actions.parquet`, `etf_enriched.json`) à partir des seuls fichiers CSV fournis par l'organisation, sans appel réseau :

```bash
.venv/bin/python -m data.ingestion.build_dataset \
    --mode offline \
    --version 2026-11-13-starter
```

### Mode complet (univers élargi ~250 actifs sur 10 ans)

Télécharge les prix journaliers, dividendes et fractionnements des candidats de `data/ingestion/universe.yaml` via `yfinance` par lots de 75 tickers (avec pause entre les lots, sauvegarde par lot dans `data/output/.cache/<version>/batches/` permettant la reprise, et réessai individuel des échecs), enrichit le secteur des actions depuis `yfinance`, et retélécharge sur 10 ans le taux USD/CAD et les 9 séries macro (API Valet de la Banque du Canada et FRED) :

```bash
.venv/bin/python -m data.ingestion.build_dataset --mode full
```

La sortie est écrite dans `data/output/<version>/` où `<version>` vaut la date d'extraction (`YYYY-MM-DD`).

---

## 2. Téléversement vers S3 et intégration (commandes documentées, non exécutées par le script)

Une fois le jeu généré dans `data/output/<version>/`, un humain disposant des identifiants du compte de l'événement (`.aws-local/`, compte `058264316309`) peut téléverser le jeu vers le bucket S3 privé (`storage-dataset`) :

```bash
# 1. Charger les identifiants du compte AWS de l'événement et vérifier le compte 058264316309
source scripts/aws-env.sh && \
aws s3 sync "data/output/<version>/" "s3://<bucket>/dataset/<version>/" \
    --region us-east-1 \
    --delete
```

Pour mettre à jour la liste embarquée de validation des tickers de la Lambda API (`WS4`) avant de reconstruire les zips Lambda :

```bash
.venv/bin/python -m backend.api.scripts.build_tickers \
    --input "data/output/<version>/universe.parquet" \
    --output backend/api/tickers.json \
    --source "universe.parquet@<version>"
```

---

## 3. Disposition des fichiers produits (`data/output/<version>/`)

| Chemin | Format / Clés | Contenu |
|---|---|---|
| `manifest.json` | JSON (`camelCase`) | Version, date d'extraction, période demandée et réelle, nombre et liste des tickers retenus et écartés (avec raison), `firstDateByTicker`, `shortHistoryTickers`, `publicationDateRule`, sources, traitements et `qualityReport`. |
| `universe.parquet` | Parquet (`snake_case`) | `asset_id, symbol, name, asset_class, market, currency, sector, sector_source, industry, country, first_date, last_date, return_1y, volatility_1y, max_drawdown_1y`. |
| `prices/{symbol}.parquet` | Parquet (`snake_case`) | `date, symbol, open, high, low, close, adjclose, volume, currency` (un fichier par actif retenu). |
| `prices_all/year=YYYY/part-0.parquet` | Parquet (`snake_case`) | Mêmes colonnes que `prices/{ticker}.parquet`, regroupant tous les actifs retenus par année civile. |
| `fx/usdcad.parquet` | Parquet (`snake_case`) | `date, usdcad, cadusd` (taux journalier de la Banque du Canada et son inverse). |
| `macro/macro.parquet` | Parquet (`snake_case`) | `date, series_id, value, unit, frequency, label, source, publication_date`. |
| `corporate_actions.parquet` | Parquet (`snake_case`) | `ex_date, ticker, action, value, unit, anomaly_note` (dividendes et fractionnements). |
| `etf_enriched.json` | JSON (`camelCase`) | Pour les 15 FNB clés (`XIU.TO, SPY, QQQ, ESGV, XBB.TO, ZST.TO, AGG, TLT, GLD, XSP.TO, ZEQT.TO, XEQT.TO, VFV.TO, ZAG.TO, XIC.TO`) : `sectorWeights`, `topHoldings`, `countryWeights`, `merPct`, et `exclusions` (`ESGV`), chacun avec `sourceUrl` et `asOfDate`. Les autres FNB sont marqués `"composition non disponible"`. |

---

## 4. Sources et conditions d'utilisation

| Source | Données | Conditions d'utilisation |
|---|---|---|
| **Yahoo Finance** (via `yfinance`) | Prix journaliers (`open, high, low, close, adj_close, volume`), dividendes, fractionnements, métadonnées sectorielles des actions | Usage personnel, non commercial et pédagogique uniquement. Les données CSV/Parquet ne doivent pas être redistribuées publiquement : https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html |
| **Banque du Canada — API Valet** | Taux de change `FXUSDCAD`, taux cible du financement à un jour (`V39079`), rendements des obligations du gouvernement du Canada 2 ans (`BD.CDN.2YR.DQ.YLD`) et 10 ans (`BD.CDN.10YR.DQ.YLD`), IPC total canadien (`STATIC_TOTALCPICHANGE`) | https://www.bankofcanada.ca/terms/ |
| **FRED — Federal Reserve Bank of St. Louis** | Taux effectif des fonds fédéraux (`DFF`), rendements du Trésor américain 2 ans (`DGS2`) et 10 ans (`DGS10`), indice des prix à la consommation américain (`CPIAUCSL`), taux de chômage américain (`UNRATE`) | Sources originales d'agences fédérales américaines (Federal Reserve Board, BLS) : https://fred.stlouisfed.org/legal/ |
| **Fiches émetteurs des FNB** | Pondérations sectorielles, géographiques, principales positions, RFG (`merPct`) et exclusions ESG (`ESGV`) relevées manuellement dans `data/ingestion/etf_enriched.source.json` | Documentation publique des émetteurs (BlackRock iShares, Vanguard, State Street SPDR, Invesco, BMO). |

---

## 5. Méthodes, traitements et limites documentées

1. **Calendriers non alignés et absence de remplissage (*no forward-fill*)** :
   - Les lignes de prix n'existent que les jours où Yahoo Finance publie une cotation pour l'actif.
   - Les jours fériés diffèrent entre la Bourse de Toronto (`TSX`) et les marchés américains (`US`), et les cryptomonnaies (`BTC-USD`, `ETH-USD`, `SOL-USD`) cotent 7 jours sur 7 en jours civils UTC (00:00 à 24:00 UTC).
   - Aucun remplissage (*forward-fill*) n'est appliqué dans les fichiers Parquet : l'alignement des calendriers est effectué par le moteur de calcul au moment de l'analyse (calendrier natif par actif ; intersection des jours ouvrés nord-américains pour les portefeuilles et corrélations).
   - Le fichier `fx/usdcad.parquet` n'a pas de ligne les jours fériés canadiens ; le moteur reporte le dernier taux connu lors des conversions en CAD.
   - **Le taux USD/CAD ne commence que le `2017-01-03`**, date de début de la série `FXUSDCAD` de l'API Valet de la Banque du Canada. Les prix commencent le `2016-11-12`. Dans le jeu `2026-11-14`, environ 3 250 lignes en USD (novembre et décembre 2016) ne peuvent donc pas être converties en CAD. Les mesures en CAD commencent au `2017-01-03` ; les mesures dans la devise d'origine peuvent utiliser toute la fenêtre. Les périodes de stress (fin 2018, COVID 2020, 2022) restent couvertes.

2. **Ajustement rétroactif de `adj_close` et fractionnements (`splits`)** :
   - `adj_close` est ajusté rétroactivement par Yahoo Finance pour les fractionnements et les dividendes à partir de la date d'extraction. Si l'on retélécharge les données à une date ultérieure, les valeurs passées de `adj_close` changent.
   - `close` est déjà ajusté pour les fractionnements. **Il ne faut jamais réappliquer les lignes `split` de `corporate_actions.parquet` aux prix.**
   - Les indicateurs 1 an de `universe.parquet` (`return_1y`, `volatility_1y`, `max_drawdown_1y`) sont calculés sur la dernière année de `adj_close` avec une annualisation $\sqrt{252}$.

3. **Anomalie isolée `CNQ.TO` du `2022-08-22`** :
   - Yahoo Finance rapporte pour `CNQ.TO` un « fractionnement » (`split`) de ratio `1.021` le `2022-08-22`, le même jour qu'un dividende de `0.75 CAD` (il s'agit vraisemblablement d'un ajustement lié à une distribution spéciale et non d'un fractionnement d'actions).
   - Cette ligne est isolée dans `corporate_actions.parquet` via la colonne `anomaly_note` et documentée dans `manifest.json` (`qualityReport.isolatedAnomalies`). Aucun split n'est réappliqué aux prix.

4. **Biais du survivant amplifié par la fenêtre de 10 ans (2016–2026)** :
   - L'univers de ~250 actifs a été sélectionné en 2026 parmi des titres et FNB aujourd'hui importants et liquides (constituants actuels du S&P/TSX 60, grandes capitalisations américaines actuelles, FNB populaires).
   - Reculer la fenêtre à 10 ans permet d'inclure des périodes de stress historiques réelles (fin 2018, krach COVID de février-mars 2020, hausse des taux et baisse conjointe actions/obligations de 2022), mais **amplifie le biais du survivant** : les sociétés disparues, acquises ou sorties des indices entre 2016 et 2026 n'y figurent pas.

5. **Historiques courts de certains FNB et cryptomonnaies** :
   - Plusieurs FNB courants chez les investisseurs autonomes canadiens ainsi que certaines actions ou cryptos ont été lancés après novembre 2016 (ex. `ZEQT.TO` lancé en janvier 2022, `XEQT.TO` en août 2019, `VEQT.TO` en janvier 2019, `CASH.TO` en 2021, `SOL-USD` en 2020).
   - Tant qu'un candidat dispose d'au moins 1 an d'historique ($\ge 252$ observations), il est **conservé tel quel sans jamais combler ni extrapoler** les années antérieures à son lancement. Sa date de première cotation est enregistrée dans `universe.parquet` (`first_date`) et dans `manifest.json` (`firstDateByTicker` et `shortHistoryTickers`).
   - Les candidats sans données ou avec moins de 252 observations sont écartés et listés dans `manifest.json` (`excludedTickers`) avec la raison du rejet.

6. **Règle prudente de `publication_date` sur les séries macro mensuelles (R10)** :
   - Les séries mensuelles (`STATIC_TOTALCPICHANGE`, `CPIAUCSL`, `UNRATE`) sont datées au 1er jour du mois de référence (`YYYY-MM-01`), alors qu'elles sont publiées plusieurs semaines plus tard (et que les valeurs FRED sont les dernières valeurs révisées, non celles de première publication).
   - Pour éviter tout biais d'anticipation (*look-ahead bias*, règle R10), `publication_date` est fixée au **28 du mois suivant le mois de référence** (`YYYY-(MM+1)-28`). Cette approximation prudente couvre les publications de l'IPC canadien après le 20 du mois suivant (ex. mai 2024 publié le 25 juin) ainsi que les retards de publication américains (ex. automne 2025). Les séries journalières ont `publication_date = date`.

7. **Absence d'indicateurs ESG sur les actions** :
   - Aucun score ESG ni indicateur d'« exposition fossile » n'est inventé pour les actions : seul le secteur (`sector` et `sector_source`) est fourni. Pour les FNB, seules les 15 fiches clés peuvent contenir des données de composition sourcées et datées à partir des fiches émetteurs (`etf_enriched.source.json`) ; tous les autres FNB sont marqués `"composition non disponible"`.
