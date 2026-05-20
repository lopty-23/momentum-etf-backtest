"""
Backtest engine for the macro ETF trend-following strategy.

The strategy:
  - Universe: 6 macro ETFs (SPY, EFA, AGG, GLD, DBC, VNQ) + BIL (defensive sleeve).
  - Per-asset signal: if 'on', hold the ETF at 1/N portfolio weight;
    if 'off', that slot routes to BIL instead of cash.
  - Rebalancing: first trading day of each calendar month.
  - Look-ahead protection: the rebalance on day T uses the signal as of
    day T-1. No same-day information can influence trades.
  - Execution: yesterday's weights earn today's returns (next-day-open
    convention — we trade against tomorrow's prices, not today's close).
  - Transaction costs: a round-trip commission rate is applied as a
    return drag on rebalance days, proportional to portfolio turnover.
"""

from typing import Iterable, Optional

import pandas as pd

DEFAULT_RISK_ASSETS: list[str] = ["SPY", "EFA", "AGG", "GLD", "DBC", "VNQ"]
DEFAULT_DEFENSIVE: str = "BIL"
DEFAULT_COST_RT: float = 0.0005

def monthly_rebalance_dates(prices: pd.DataFrame) -> pd.DatetimeIndex:
    return prices.groupby(prices.index.to_period('M')).head(1).index

def run_backtest(
        prices: pd.DataFrame,
        signal: pd.DataFrame,
        risk_assets: Iterable[str] = DEFAULT_RISK_ASSETS,
        defensive: str = DEFAULT_DEFENSIVE,
        cost_rt: float = DEFAULT_COST_RT,
) -> dict:
    # Step 1: setup
    risk_assets = list(risk_assets)
    n_risk = len(risk_assets)
    asset_weight = 1.0 / n_risk

    # Step 2: rebalance dates
    month_starts = monthly_rebalance_dates(prices)

    # Step 3: lagged signal at rebalance dates (look-ahead protection)
    signal_lagged = signal.shift(1)
    rebalance_signals = signal_lagged.loc[month_starts]
    risk_signals = rebalance_signals[risk_assets].fillna(False).astype(bool)

    # Step 4: build weights at each rebalance
    weights = pd.DataFrame(0.0, index=risk_signals.index, columns=prices.columns)
    for asset in risk_assets:
        weights[asset] = risk_signals[asset].astype(float) * asset_weight
    weights[defensive] = (~risk_signals).sum(axis=1) * asset_weight

    # Step 5: forward-fill to daily; compute portfolio returns
    daily_weights = weights.reindex(prices.index, method="ffill")
    asset_returns = prices.pct_change()
    returns_gross = (daily_weights.shift(1) * asset_returns).sum(axis=1)

    # Step 6: turnover and costs
    turnover = weights.diff().abs().sum(axis=1) / 2
    daily_costs = (turnover * cost_rt).reindex(prices.index, fill_value=0)
    returns_net = returns_gross - daily_costs

    return {
        "returns_gross": returns_gross,
        "returns_net":   returns_net,
        "weights":       weights,
        "turnover":      turnover,
    }

def compute_benchmark_returns(
    prices: pd.DataFrame,
    weights: Optional[dict] = None,
) -> pd.Series:
    """..."""
    if weights is None:
        weights = {"SPY": 0.6, "AGG": 0.4}

    asset_returns = prices.pct_change()
    return sum(w * asset_returns[ticker] for ticker, w in weights.items())

# ---- Smoke test ----

if __name__ == "__main__":
    # Allow running this file directly: python src/backtest.py
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from src.data_loader import load_prices, load_risk_free_rate
    from src.signals import sma_filter
    from src.metrics import compute_all_metrics

    prices = load_prices()
    rf = load_risk_free_rate()
    signal = sma_filter(prices, window=200)

    result = run_backtest(prices, signal)
    benchmark = compute_benchmark_returns(prices)

    summary = pd.DataFrame({
        "Strategy (net)":  compute_all_metrics(result["returns_net"], rf=rf),
        "60/40 Benchmark": compute_all_metrics(benchmark, rf=rf),
    })

    print("End-to-end smoke test — 200-day filter strategy vs 60/40 benchmark:")
    print()
    print(summary.to_string(float_format="{:.3f}".format))
    print()
    print(f"Annualized turnover: {result['turnover'].iloc[1:].mean() * 12:.1%}")