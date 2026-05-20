from pathlib import Path
from typing import Iterable
 
import pandas as pd
import yfinance as yf

DEFAULT_TICKERS: list[str] = ["SPY", "EFA", "AGG", "GLD", "DBC", "VNQ", "BIL"]
DEFAULT_START_DATE: str = "2000-01-01"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_PATH = REPO_ROOT / "data" / "processed" / "prices.parquet"
DEFAULT_RISK_FREE_PATH = REPO_ROOT / "data" / "raw" / "risk_free_rate.xlsx"

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

def load_risk_free_rate(path: Path = DEFAULT_RISK_FREE_PATH) -> pd.Series:
    if not path.exists():
        raise FileNotFoundError(
            f"Risk-free rate file not found at {path}.\n"
            f"This project uses Bloomberg's USGG3M Index daily yield series, "
            f"which must be exported manually from a Bloomberg terminal. "
            f"The file is excluded from version control because Bloomberg "
            f"data is licensed and cannot be redistributed."
        )

    if path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path, sheet_name=0)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path, parse_dates=["Date"])
    else:
        raise ValueError(
            f"Unsupported file extension: {path.suffix}. Expected .xlsx or .csv."
        )

    if pd.api.types.is_numeric_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], unit="D", origin="1899-12-30")

    df = df.set_index("Date").sort_index()

    annual_yield_decimal = df["PX_LAST"] / 100.0
    daily_rf_returns = annual_yield_decimal / 252
    daily_rf_returns.name = "risk_free_return"

    return daily_rf_returns

if __name__ == "__main__":
    print(f"Downloading prices for {DEFAULT_TICKERS} from {DEFAULT_START_DATE}...")
    prices = load_prices(force_refresh=True)
    print(f"Saved {prices.shape[0]} rows x {prices.shape[1]} columns to {DEFAULT_CACHE_PATH}")
    print(f"Date range: {prices.index.min().date()} to {prices.index.max().date()}")

    # Test the risk-free loader if the file is available
    if DEFAULT_RISK_FREE_PATH.exists():
        rf = load_risk_free_rate()
        print(f"\nRisk-free rate loaded: {len(rf)} rows")
        print(f"Date range: {rf.index.min().date()} to {rf.index.max().date()}")
        print(f"Most recent annual yield: {rf.iloc[-1] * 252:.2%}")
    else:
        print(f"\nNo risk-free rate file at {DEFAULT_RISK_FREE_PATH} — skipping.")
 
 