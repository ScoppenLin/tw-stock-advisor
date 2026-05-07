from __future__ import annotations

import pandas as pd


class FeatureBuilder:
    """Turns raw portfolio, universe, and market data into model-ready features."""

    def build(self, universe: pd.DataFrame, price_history: pd.DataFrame) -> pd.DataFrame:
        technical = self._technical_features(price_history)
        features = universe.merge(technical, on="ticker", how="left")
        defaults = {
            "return_20d": 0.0,
            "return_60d": 0.0,
            "ma20": 0.0,
            "ma60": 0.0,
            "ma120": 0.0,
            "above_ma20": False,
            "above_ma60": False,
            "above_ma120": False,
            "volume_ratio": 1.0,
            "distance_ma20": 0.0,
            "distance_ma60": 0.0,
            "price_drawdown": 0.0,
        }
        return features.fillna(defaults)

    def _technical_features(self, price_history: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for ticker, ticker_rows in price_history.sort_values(["ticker", "date"]).groupby("ticker"):
            closes = ticker_rows["close"].astype(float)
            latest = closes.iloc[-1]
            ma20 = closes.tail(min(20, len(closes))).mean()
            ma60 = closes.tail(min(60, len(closes))).mean()
            ma120 = closes.tail(min(120, len(closes))).mean()
            high = closes.max()
            volume_ratio = self._volume_ratio(ticker_rows)

            rows.append(
                {
                    "ticker": ticker,
                    "return_20d": self._period_return(closes, 20),
                    "return_60d": self._period_return(closes, 60),
                    "ma20": round(ma20, 2),
                    "ma60": round(ma60, 2),
                    "ma120": round(ma120, 2),
                    "above_ma20": latest > ma20,
                    "above_ma60": latest > ma60,
                    "above_ma120": latest > ma120,
                    "volume_ratio": round(volume_ratio, 4),
                    "distance_ma20": self._safe_ratio(latest, ma20) - 1,
                    "distance_ma60": self._safe_ratio(latest, ma60) - 1,
                    "price_drawdown": self._safe_ratio(latest, high) - 1,
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _period_return(closes: pd.Series, period: int) -> float:
        if closes.empty:
            return 0.0
        start = closes.iloc[0] if len(closes) <= period else closes.iloc[-period]
        return (closes.iloc[-1] / start) - 1 if start else 0.0

    @staticmethod
    def _volume_ratio(rows: pd.DataFrame) -> float:
        if "volume" not in rows.columns:
            return 1.0
        volumes = rows["volume"].astype(float)
        if len(volumes) < 2:
            return 1.0
        recent = volumes.tail(min(5, len(volumes))).mean()
        baseline = volumes.mean()
        return recent / baseline if baseline else 1.0

    @staticmethod
    def _safe_ratio(numerator: float, denominator: float) -> float:
        return numerator / denominator if denominator else 1.0
