from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from config import ACCOUNT_FILE, LATEST_PRICES_FILE, MARKET_INDICATORS_FILE, PORTFOLIO_FILE, PRICE_HISTORY_FILE, TOTAL_CAPITAL_FALLBACK, WATCHLIST_FILE
from twse_client import TwseClient

if TYPE_CHECKING:
    from google_sheets import GoogleSheetsClient


@dataclass
class MarketData:
    latest_prices: pd.DataFrame
    price_history: pd.DataFrame
    market_indicators: pd.DataFrame


class DataLoader:
    """Loads portfolio, watchlist, and market data from local files.

    This class is intentionally source-agnostic. TWSE OpenAPI, ETFortune, or broker
    feeds can later be added behind the same public methods.
    """

    def load_portfolio(self, source: str = "local", sheet_client: "GoogleSheetsClient | None" = None) -> pd.DataFrame:
        if source == "google":
            if sheet_client is None:
                raise RuntimeError("sheet_client is required when portfolio source is google")
            df = sheet_client.read_dataframe("portfolio")
            if "ticker" in df.columns:
                df["ticker"] = df["ticker"].astype(str).str.zfill(4)
        else:
            df = pd.read_csv(PORTFOLIO_FILE, dtype={"ticker": str})
        required = {"ticker", "name", "asset_type", "shares", "avg_cost", "target_weight"}
        self._validate_columns(df, required, PORTFOLIO_FILE.name)
        return df

    def load_watchlist(self, source: str = "local", sheet_client: "GoogleSheetsClient | None" = None) -> pd.DataFrame:
        if source == "google":
            if sheet_client is None:
                raise RuntimeError("sheet_client is required when watchlist source is google")
            df = sheet_client.read_dataframe("watchlist")
            if "ticker" in df.columns:
                df["ticker"] = df["ticker"].astype(str).str.zfill(4)
        else:
            df = pd.read_csv(WATCHLIST_FILE, dtype={"ticker": str})
        required = {"ticker", "name", "asset_type", "sector"}
        self._validate_columns(df, required, WATCHLIST_FILE.name)
        return df

    def load_account(self, source: str = "local", sheet_client: "GoogleSheetsClient | None" = None) -> dict:
        if source == "google":
            if sheet_client is None:
                raise RuntimeError("sheet_client is required when account source is google")
            df = sheet_client.read_dataframe("account")
        elif not ACCOUNT_FILE.exists():
            return {"total_capital": TOTAL_CAPITAL_FALLBACK, "reserve_cash_weight": 0.05}
        else:
            df = pd.read_csv(ACCOUNT_FILE)
        required = {"total_capital", "reserve_cash_weight"}
        self._validate_columns(df, required, ACCOUNT_FILE.name)
        row = df.iloc[0]
        return {
            "total_capital": float(row["total_capital"]),
            "reserve_cash_weight": float(row["reserve_cash_weight"]),
        }

    def load_market_data(self, tickers: list[str], source: str = "local") -> MarketData:
        latest_prices = self._load_latest_prices(tickers, source)
        price_history = self._load_price_history(tickers, latest_prices)
        market_indicators = self._load_market_indicators()
        return MarketData(latest_prices=latest_prices, price_history=price_history, market_indicators=market_indicators)

    def _load_latest_prices(self, tickers: list[str], source: str) -> pd.DataFrame:
        if source == "twse":
            try:
                return TwseClient().fetch_latest_prices(tickers)
            except RuntimeError as exc:
                print(f"TWSE fetch failed, falling back to local latest prices: {exc}")

        if LATEST_PRICES_FILE.exists():
            df = pd.read_csv(LATEST_PRICES_FILE, dtype={"ticker": str})
            self._validate_columns(df, {"ticker", "current_price"}, LATEST_PRICES_FILE.name)
            return df[df["ticker"].isin(tickers)].copy()

        rows = [{"ticker": ticker, "current_price": 100 + index * 10} for index, ticker in enumerate(tickers)]
        return pd.DataFrame(rows)

    def _load_price_history(self, tickers: list[str], latest_prices: pd.DataFrame) -> pd.DataFrame:
        if PRICE_HISTORY_FILE.exists():
            df = pd.read_csv(PRICE_HISTORY_FILE, dtype={"ticker": str}, parse_dates=["date"])
            self._validate_columns(df, {"date", "ticker", "close"}, PRICE_HISTORY_FILE.name)
            return df[df["ticker"].isin(tickers)].copy()

        rows = []
        for _, price_row in latest_prices.iterrows():
            current_price = float(price_row["current_price"])
            for day in range(1, 6):
                rows.append(
                    {
                        "date": pd.Timestamp.today().normalize() - pd.Timedelta(days=(5 - day) * 7),
                        "ticker": price_row["ticker"],
                        "close": current_price * (0.94 + day * 0.012),
                        "volume": 1_000_000 + day * 100_000,
                    }
                )
        return pd.DataFrame(rows)

    def _load_market_indicators(self) -> pd.DataFrame:
        required = {
            "date",
            "twii_close",
            "twii_ma20",
            "twii_ma60",
            "twii_ma120",
            "twii_return_20d",
            "foreign_buy_5d",
            "foreign_buy_20d",
            "twd_return_20d",
            "nasdaq_return_20d",
            "sox_return_20d",
            "volume_ratio_20d",
            "vix",
        }
        if MARKET_INDICATORS_FILE.exists():
            df = pd.read_csv(MARKET_INDICATORS_FILE)
            self._validate_columns(df, required, MARKET_INDICATORS_FILE.name)
            return df

        return pd.DataFrame(
            [
                {
                    "date": pd.Timestamp.today().normalize(),
                    "twii_close": 20_000,
                    "twii_ma20": 19_800,
                    "twii_ma60": 19_500,
                    "twii_ma120": 19_200,
                    "twii_return_20d": 0.03,
                    "foreign_buy_5d": 0,
                    "foreign_buy_20d": 0,
                    "twd_return_20d": 0,
                    "nasdaq_return_20d": 0.02,
                    "sox_return_20d": 0.02,
                    "volume_ratio_20d": 1.0,
                    "vix": 18,
                }
            ]
        )

    @staticmethod
    def _validate_columns(df: pd.DataFrame, required: set[str], source_name: str) -> None:
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"{source_name} missing required columns: {sorted(missing)}")
