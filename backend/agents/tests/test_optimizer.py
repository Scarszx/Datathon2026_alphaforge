"""Constructeur de portefeuille moyenne-variance : fidélité au script de l'équipe et contraintes."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.agents.engine import analytics as an
from backend.agents.engine import optimizer as opt
from backend.agents.engine.optimizer import OptimizerError, optimize_portfolio

INDUSTRIES = ["Software", "Banks", "Tobacco", "Aerospace & Defense", "Drugs", "Retail", "Oil", "Utilities"]


class FakeStore:
    """Univers synthétique : 8 industries x 6 titres US, un marché ^GSPC."""

    def __init__(self, seed: int = 7, days: int = 1400):
        rng = np.random.default_rng(seed)
        self.index = pd.bdate_range(end="2026-11-13", periods=days)
        market = rng.normal(0.0004, 0.01, days)
        rows, prices = [], {}
        for i, industry in enumerate(INDUSTRIES):
            sector_factor = rng.normal(0, 0.005, days)
            for j in range(6):
                symbol = f"{industry[:3].upper()}{j}"
                beta = 0.5 + 0.15 * j + 0.05 * i
                daily = beta * market + sector_factor * 0.8 + rng.normal(0.0002 * (j + 1), 0.012, days)
                prices[symbol] = pd.Series(100 * np.cumprod(1 + daily), index=self.index)
                rows.append({"symbol": symbol, "name": f"{industry} {j}", "asset_class": "equity", "market": "US",
                             "currency": "USD", "sector": "S", "industry": industry, "country": "United States"})
        prices["^GSPC"] = pd.Series(1000 * np.cumprod(1 + market), index=self.index)
        rows.append({"symbol": "^GSPC", "name": "S&P 500", "asset_class": "index", "market": "US",
                     "currency": "USD", "sector": "Unknown", "industry": None, "country": "United States"})
        self.prices = prices
        self._universe = pd.DataFrame(rows).set_index("symbol", drop=False)

    def universe(self):
        return self._universe

    def last_date(self):
        return self.index[-1]


@pytest.fixture
def fake(monkeypatch):
    store = FakeStore()
    monkeypatch.setattr(opt, "native_series", lambda s, symbol: s.prices[symbol])
    return store


def test_ledoit_wolf_numpy_identique_a_scikit_learn():
    from sklearn.covariance import LedoitWolf

    returns = np.random.default_rng(1).normal(0, 0.01, (300, 25)) @ np.random.default_rng(2).normal(size=(25, 25))
    assert np.allclose(opt.ledoit_wolf_covariance(returns), LedoitWolf().fit(returns).covariance_, rtol=1e-10, atol=1e-14)


def test_qp_identique_au_slsqp_du_script():
    from scipy.optimize import minimize

    rng = np.random.default_rng(3)
    p = 30
    factors = rng.normal(size=(p, 4))
    sigma = factors @ factors.T * 0.01 + np.eye(p) * 0.02
    mu = rng.normal(0.08, 0.04, p)
    industry = np.repeat(np.arange(6), 5)
    cap, wmax, aversion = 0.25, 0.10, 4.0
    groups = [(industry == k, cap, None) for k in range(6)]
    w_qp = opt.solve_mean_variance(sigma, mu, aversion, np.full(p, wmax), groups)
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1}] + [
        {"type": "ineq", "fun": lambda w, k=k: cap - w[industry == k].sum()} for k in range(6)
    ]
    res = minimize(lambda w: -(w @ mu - aversion / 2 * w @ sigma @ w), np.full(p, 1 / p),
                   jac=lambda w: -(mu - aversion * sigma @ w), bounds=[(0, wmax)] * p,
                   constraints=constraints, method="SLSQP", options={"maxiter": 500, "ftol": 1e-12})
    utility = lambda w: w @ mu - aversion / 2 * w @ sigma @ w
    assert utility(w_qp) == pytest.approx(utility(res.x), abs=1e-6)
    assert np.allclose(w_qp, res.x, atol=2e-3)


def test_aversion_selon_le_profil_jamais_en_dur():
    assert opt.risk_aversion(1) > opt.risk_aversion(3) > opt.risk_aversion(5)
    with pytest.raises(OptimizerError):
        opt.risk_aversion(6)


def test_contraintes_respectees_sans_preferences(fake):
    result = optimize_portfolio(fake, risk_profile=3)
    weights = np.array([h.weight for h in result.holdings])
    assert weights.sum() == pytest.approx(1.0) and (weights <= 0.10 + 1e-6).all()
    assert all(w <= 0.25 + 1e-6 for w in result.by_industry.values())
    assert result.excluded_industries == [] and result.preferred_industries == []
    assert result.aversion == opt.risk_aversion(3) and result.preferred_share == 0.0


def test_exclusions_planchers_et_plafond_releve(fake):
    result = optimize_portfolio(
        fake, risk_profile=5, excluded_industries=["Oil"],
        preferred_industries=[{"industry": "Tobacco", "minWeight": 0.15}, {"industry": "Aerospace & Defense", "minWeight": None}],
    )
    assert "Oil" not in result.by_industry
    assert result.by_industry["Tobacco"] >= 0.15 - 1e-6
    assert result.by_industry.get("Aerospace & Defense", 0) <= 0.35 + 1e-6
    assert result.preferred_share == pytest.approx(result.by_industry["Tobacco"] + result.by_industry.get("Aerospace & Defense", 0))


def test_une_aversion_plus_forte_reduit_le_risque(fake):
    bold = optimize_portfolio(fake, risk_profile=5)
    prudent = optimize_portfolio(fake, risk_profile=1)
    assert prudent.volatility < bold.volatility


@pytest.mark.parametrize("excluded,preferred,message", [
    (None, [{"industry": "Tobacco", "minWeight": 0.6}, {"industry": "Banks", "minWeight": 0.6}], "more than 100"),
    (["Tobacco"], [{"industry": "Tobacco", "minWeight": 0.1}], "both preferred and excluded"),
    (None, [{"industry": "Tobacco", "minWeight": 0.5}], "not reachable"),
    (["Atlantis"], None, "Unknown industry"),
    (None, [{"industry": "Banks", "minWeight": 0.1}, {"industry": "Banks", "minWeight": 0.2}], "twice"),
])
def test_erreurs_de_faisabilite_explicites(fake, excluded, preferred, message):
    with pytest.raises(OptimizerError, match=message):
        optimize_portfolio(fake, risk_profile=3, excluded_industries=excluded, preferred_industries=preferred)


def test_trop_peu_de_titres_apres_exclusions(fake):
    with pytest.raises(OptimizerError, match="Too few eligible"):
        optimize_portfolio(fake, risk_profile=3, excluded_industries=INDUSTRIES[:-1])


def test_identique_au_script_de_l_equipe(fake):
    """Mêmes données, mêmes paramètres : mêmes poids que le script (SLSQP + scikit-learn)."""
    from scipy.optimize import minimize
    from sklearn.covariance import LedoitWolf

    prefer = {"Tobacco": 0.15, "Aerospace & Defense": 0.20}
    exclude = ["Oil"]
    prix = pd.DataFrame(fake.prices)
    fen = prix.loc[prix.index.max() - pd.DateOffset(years=5):]
    fen = fen.loc[:, fen.notna().mean() >= 0.95]
    r = fen.pct_change(fill_method=None).iloc[1:].dropna()
    rm_d = r.pop("^GSPC")
    rm = rm_d.mean() * 252
    beta = r.apply(lambda x: x.cov(rm_d)) / rm_d.var()
    mu = 0.03 + beta * (rm - 0.03)
    sigma = pd.DataFrame(LedoitWolf().fit(r.values).covariance_ * 252, index=r.columns, columns=r.columns)
    m = fake.universe().loc[r.columns]
    exclu = m["industry"].isin(exclude).values
    pref = m["industry"].isin(prefer).values
    A = 4.0
    contraintes = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    for ind in m["industry"].unique():
        k = (m["industry"] == ind).values
        contraintes.append({"type": "ineq", "fun": lambda w, k=k, c=(0.35 if ind in prefer else 0.25): c - w[k].sum()})
        if prefer.get(ind, 0) > 0:
            contraintes.append({"type": "ineq", "fun": lambda w, k=k, f=prefer[ind]: w[k].sum() - f})
    S, mu_opt = sigma.values, mu.values + 0.02 * pref
    res = minimize(lambda w: -(w @ mu_opt - A / 2 * w @ S @ w), np.where(exclu, 0, 1 / (~exclu).sum()),
                   jac=lambda w: -(mu_opt - A * S @ w), bounds=[(0, 0) if e else (0, 0.10) for e in exclu],
                   constraints=contraintes, method="SLSQP", options={"maxiter": 500, "ftol": 1e-12})
    w = pd.Series(res.x.round(6), index=r.columns)
    w = w.where(w >= 0.005, 0)
    w /= w.sum()

    result = optimize_portfolio(
        fake, risk_profile=3, excluded_industries=exclude,
        preferred_industries=[{"industry": k, "minWeight": v} for k, v in prefer.items()],
        config={"aversionByProfile": {"3": A}},
    )
    mine = pd.Series({h.symbol: h.weight for h in result.holdings}).reindex(w.index).fillna(0)
    assert np.abs(mine - w).max() < 5e-3
    assert result.expected_return == pytest.approx(float(w @ mu), abs=2e-3)
    assert result.volatility == pytest.approx(float((w @ sigma @ w) ** 0.5), abs=2e-3)
