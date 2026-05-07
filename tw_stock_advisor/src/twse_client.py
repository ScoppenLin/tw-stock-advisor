from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd


@dataclass
class TwseClient:
    """Small TWSE data client with conservative fallbacks.

    Network calls are optional. The rest of the app should keep working from
    local CSV files when TWSE is unavailable or a schema changes.
    """

    timeout_seconds: int = 20
    base_url: str = "https://openapi.twse.com.tw/v1"
    stock_day_all_url: str = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"

    def fetch_latest_prices(self, tickers: list[str]) -> pd.DataFrame:
        try:
            df = self._fetch_stock_day_all_open_data()
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            raise RuntimeError(f"Unable to fetch TWSE latest prices: {exc}") from exc

        df = df[df["ticker"].isin(tickers)].copy()
        if df.empty:
            raise RuntimeError("TWSE latest price response did not contain requested tickers")
        return df[["ticker", "current_price"]]

    def fetch_openapi_catalog(self) -> dict[str, Any]:
        with urlopen(f"{self.base_url}/swagger.json", timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _fetch_stock_day_all_open_data(self) -> pd.DataFrame:
        with urlopen(self.stock_day_all_url, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8-sig")

        rows = list(csv.DictReader(io.StringIO(raw)))
        if not rows:
            raise ValueError("empty TWSE STOCK_DAY_ALL response")

        normalized = []
        for row in rows:
            ticker = row.get("證券代號") or row.get("Code")
            close = row.get("收盤價") or row.get("Closing Price")
            if not ticker or not close:
                continue
            normalized.append({"ticker": str(ticker).strip(), "current_price": self._parse_number(close)})

        if not normalized:
            raise ValueError("TWSE STOCK_DAY_ALL schema is not recognized")
        return pd.DataFrame(normalized)

    @staticmethod
    def _parse_number(value: str) -> float:
        cleaned = str(value).replace(",", "").replace("--", "").strip()
        return float(cleaned) if cleaned else 0.0
