from __future__ import annotations

import pandas as pd


class RiskManager:
    def __init__(self) -> None:
        self.default_limits = {
            "etf": 0.30,
            "core_stock": 0.10,
            "large_cap": 0.10,
            "satellite": 0.05,
            "small_mid": 0.03,
        }
        self.ticker_limits = {"2330": 0.25}

    def max_weight_for(self, ticker: str, asset_type: str) -> float:
        return self.ticker_limits.get(str(ticker), self.default_limits.get(asset_type, 0.05))

    def annotate_limits(self, df: pd.DataFrame) -> pd.DataFrame:
        annotated = df.copy()
        annotated["max_weight"] = annotated.apply(
            lambda row: self.max_weight_for(row["ticker"], row["asset_type"]),
            axis=1,
        )
        annotated["over_weight_limit"] = annotated.get("current_weight", 0) > annotated["max_weight"]
        return annotated

    def can_add(self, row: pd.Series) -> bool:
        current_weight = float(row.get("current_weight", 0) or 0)
        target_weight = float(row.get("target_weight", 0) or 0)
        max_weight = float(row.get("max_weight", self.max_weight_for(row["ticker"], row["asset_type"])))
        return current_weight < min(target_weight, max_weight)
