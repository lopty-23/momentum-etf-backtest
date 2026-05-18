from pathlib import Path
from typing import Iterable
 
import pandas as pd
import yfinance as yf

DEFAULT_TICKERS: list[str] = ["SPY", "EFA", "AGG", "GLD", "DBC", "VNQ", "BIL"]
DEFAULT_START_DATE: str = "2000-01-01"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_PATH = REPO_ROOT / "data" / "processed" / "prices.parquet"

def download_prices(
    tickers: Iterable[str] = DEFAULT_TICKERS,
    start_date: str = DEFAULT_START_DATE,
) -> pd.DataFrame:
    """Download historical price data for the specified tickers and date range."""
    prices = yf.download(list(tickers), start=start_date, auto_adjust=True, progress=False)
    return prices["Close"].sort_index(axis=1)

def load_prices(
    tickers: Iterable[str] = DEFAULT_TICKERS,
    start_date: str = DEFAULT_START_DATE,
    cache_path: Path = DEFAULT_CACHE_PATH,
    force_refresh: bool = False,
) -> pd.DataFrame: 
    if cache_path.exists() and not force_refresh:
        return pd.read_parquet(cache_path)
 
    prices = download_prices(tickers, start_date)
 
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(cache_path)
 
    return prices

if __name__ == "__main__":
    print(f"Downloading prices for {DEFAULT_TICKERS} from {DEFAULT_START_DATE}...")
    prices = load_prices(force_refresh=True)
    print(f"Saved {prices.shape[0]} rows x {prices.shape[1]} columns to {DEFAULT_CACHE_PATH}")
    print(f"Date range: {prices.index.min().date()} to {prices.index.max().date()}")
 
 