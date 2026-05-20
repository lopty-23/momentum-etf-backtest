"""
Performance metrics for backtest evaluation.

Pure functions that operate on daily return series. No dependencies on
other project modules — these are reusable across any backtest.

Typical usage:
    >>> from src.metrics import compute_all_metrics
    >>> stats = compute_all_metrics(strategy_returns, rf=rf_returns)
    >>> print(stats)

Conventions:
- Returns are expressed as decimals (0.01 = 1%, not 1).
- Annualization assumes 252 trading days per year.
- Risk-free rate (rf) is a daily returns Series, aligned (or alignable)
  to the strategy returns' date index. The project's standard source
  is Bloomberg's USGG3M Index, loaded via src.data_loader.load_risk_free_rate.
"""

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR: int = 252

def annualized_return(returns: pd.Series) -> float:
    total_return = (1 + returns.fillna(0)).prod()
    n_periods = len(returns.dropna())
    if n_periods == 0:
        return float("nan")
    return total_return ** (TRADING_DAYS_PER_YEAR / n_periods) - 1

def annualized_vol(returns: pd.Series) -> float:
    return returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

def sharpe_ratio(returns: pd.Series, rf: pd.Series) -> float:
    aligned_rf = rf.reindex(returns.index).fillna(0)
    excess = returns - aligned_rf
    sigma = excess.std()
    if sigma == 0 or np.isnan(sigma):
        return float("nan")
    return excess.mean() / sigma * np.sqrt(TRADING_DAYS_PER_YEAR)

def drawdown_series(returns: pd.Series) -> pd.Series:
    equity = (1 + returns.fillna(0)).cumprod()
    running_max = equity.cummax()
    return (equity - running_max) / running_max

def max_drawdown(returns: pd.Series) -> float:
    return drawdown_series(returns).min()

def avg_drawdown_depth(returns: pd.Series) -> float:
    dd = drawdown_series(returns)
    return dd[dd < 0].mean()

def time_underwater(returns: pd.Series) -> float:
    dd = drawdown_series(returns)
    return (dd < 0).mean()

def calmar_ratio(returns: pd.Series) -> float:
    cagr = annualized_return(returns)
    mdd = max_drawdown(returns)
    if mdd == 0 or np.isnan(mdd):
        return float("nan")
    return cagr / abs(mdd)

def drawdown_details(returns: pd.Series) -> dict:
    equity = (1 + returns.fillna(0)).cumprod()
    runing_max = equity.cummax()
    dd = (equity - runing_max) / runing_max

    worst_idx = dd.idxmin()
    worst_value = dd.min()

    peak_idx = equity[:worst_idx].idxmax()

    after_trough = equity.loc[worst_idx:]
    recovery_mask = after_trough >= equity[peak_idx]
    recovery_idx = after_trough[recovery_mask].index[0] if recovery_mask.any() else pd.NaT

    return {
        "max_drawdown":       worst_value,
        "peak_date":          peak_idx,
        "trough_date":        worst_idx,
        "recovery_date":      recovery_idx,
        "time_underwater":    time_underwater(returns),
        "avg_drawdown_depth": avg_drawdown_depth(returns),
    }

def compute_all_metrics(returns: pd.Series, rf: pd.Series) -> pd.Series:
    return pd.Series({
        "CAGR": annualized_return(returns),
        "Vol_Annualized": annualized_vol(returns),
        "Sharpe Ratio": sharpe_ratio(returns, rf),
        "Max DD": max_drawdown(returns),
        "Avg DD Depth":    avg_drawdown_depth(returns),
        "Calmar Ratio": calmar_ratio(returns),
        "Time Underwater": time_underwater(returns),
    })
    
# ---- Smoke test ----

if __name__ == "__main__":
    print("Running directly")
    # Synthetic test data: 3 years of normally-distributed daily returns
    np.random.seed(42)
    n_days = TRADING_DAYS_PER_YEAR * 3
    dates = pd.date_range("2020-01-01", periods=n_days, freq="B")

    fake_returns = pd.Series(
        np.random.normal(0.0005, 0.01, n_days),
        index=dates,
    )
    fake_rf = pd.Series(
        np.full(n_days, 0.02 / TRADING_DAYS_PER_YEAR),
        index=dates,
    )

    print("Smoke test on synthetic data (3 years, mean=0.05%/day, std=1%/day):")
    print(compute_all_metrics(fake_returns, fake_rf).to_string(float_format="{:.4f}".format))
