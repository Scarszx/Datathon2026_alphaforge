"""The three reference personas of the AlphaForge brief (entirely fictional)."""

PERSONAS = {
    "amira": {
        "id": "amira",
        "displayName": "Amira, 26 ans",
        "summary": "Ingénieure logiciel. Risque élevé, horizon 15 ans et plus. Croissance, IA et technologies émergentes, "
                   "crypto, accepte la volatilité, mais veut rester diversifiée (pas 100 % techno).",
        "profile": {
            "riskLevel": "high", "horizonMinYears": 15, "horizonMaxYears": None,
            "objective": "Croissance à long terme",
            "constraints": ["Diversification : pas 100 % technologie"],
            "preferences": ["IA et technologies émergentes", "Crypto-actifs", "Croissance"],
            "excludedAssetClasses": [],
        },
        "demoQuestion": "Propose-moi une allocation fictive orientée croissance, IA et crypto.",
    },
    "mateo": {
        "id": "mateo",
        "displayName": "Mateo, 41 ans",
        "summary": "Gestionnaire des opérations, conjoint et deux enfants. Risque modéré, horizon 8 à 12 ans. Équilibre "
                   "croissance et stabilité, fortes préférences ESG, évite les controverses, ouvert aux technologies "
                   "émergentes mais pas à la spéculation.",
        "profile": {
            "riskLevel": "moderate", "horizonMinYears": 8, "horizonMaxYears": 12,
            "objective": "Équilibre croissance et stabilité",
            "constraints": ["Éviter les entreprises controversées", "Pas d'actifs spéculatifs"],
            "preferences": ["ESG", "Technologies émergentes (non spéculatives)"],
            "excludedAssetClasses": ["crypto"],
        },
        "demoQuestion": "Construis une allocation fictive équilibrée qui respecte mes critères ESG.",
    },
    "robert": {
        "id": "robert",
        "displayName": "Robert, 59 ans",
        "summary": "Professionnel de la santé, investisseur expérimenté. Risque faible à modéré, horizon 3 à 5 ans. "
                   "Préservation du capital avec un peu de croissance, entreprises établies et compréhensibles, peu "
                   "d'intérêt pour la crypto. Tenté par une entreprise très médiatisée plus risquée que son profil.",
        "profile": {
            "riskLevel": "low_moderate", "horizonMinYears": 3, "horizonMaxYears": 5,
            "objective": "Préservation du capital avec un peu de croissance",
            "constraints": ["Entreprises établies et compréhensibles"],
            "preferences": ["Dividendes", "Stabilité"],
            "excludedAssetClasses": ["crypto"],
        },
        "demoQuestion": "Tout le monde parle de NVIDIA. Je veux y mettre 40 % de mon portefeuille.",
    },
}
