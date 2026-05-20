import pandas as pd
import numpy as np

def sma_filter(prices: pd.DataFrame, window: int = 200) -> pd.DataFrame:
    sma = prices.rolling(window=window).mean()
    return prices > sma

def sma_crossover(prices: pd.DataFrame, fast: int = 10, slow: int = 30) -> pd.DataFrame:
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be less than slow ({slow})")
    
    sma_fast = prices.rolling(window=fast).mean()
    sma_slow = prices.rolling(window=slow).mean()
    return sma_fast > sma_slow

# ---- Smoke test ----

if __name__ == "__main__":
    # Synthetic prices: 500 business days, 3 fake ETFs, random walk with drift
    np.random.seed(42)
    n_days = 500
    fake_prices = pd.DataFrame(
        np.cumsum(np.random.normal(0.05, 1.0, (n_days, 3)), axis=0) + 100,
        index=pd.date_range("2020-01-01", periods=n_days, freq="B"),
        columns=["ETF_A", "ETF_B", "ETF_C"],
    )

    print("Smoke test on synthetic prices (500 days, 3 fake ETFs):")
    print(f"  Price range: {fake_prices.values.min():.1f} to {fake_prices.values.max():.1f}")
    print()

    # Test the Faber filter
    filter_signal = sma_filter(fake_prices, window=50)
    print("sma_filter(window=50) — 'on' rate per ETF:")
    print(filter_signal.mean().to_string(float_format="{:.1%}".format))
    print()

    # Test the crossover
    cross_signal = sma_crossover(fake_prices, fast=10, slow=30)
    print("sma_crossover(fast=10, slow=30) — 'on' rate per ETF:")
    print(cross_signal.mean().to_string(float_format="{:.1%}".format))