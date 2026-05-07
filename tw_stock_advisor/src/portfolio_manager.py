from __future__ import annotations

import pandas as pd

from config import TAIWAN_LOT_SIZE


class PortfolioManager:
    def build_portfolio(self, portfolio: pd.DataFrame, latest_prices: pd.DataFrame) -> pd.DataFrame:
        enriched = portfolio.merge(latest_prices, on="ticker", how="left")
        if enriched["current_price"].isna().any():
            missing = enriched.loc[enriched["current_price"].isna(), "ticker"].tolist()
            raise ValueError(f"Missing latest prices for portfolio tickers: {missing}")

        enriched["shares"] = enriched["shares"].astype(float)
        enriched["avg_cost"] = enriched["avg_cost"].astype(float)
        enriched["target_weight"] = enriched["target_weight"].astype(float)
        enriched["current_price"] = enriched["current_price"].astype(float)

        enriched["market_value"] = enriched["shares"] * enriched["current_price"]
        enriched["cost_basis"] = enriched["shares"] * enriched["avg_cost"]
        enriched["unrealized_pnl"] = enriched["market_value"] - enriched["cost_basis"]
        enriched["unrealized_pnl_pct"] = self._safe_divide(enriched["unrealized_pnl"], enriched["cost_basis"])
        total_value = enriched["market_value"].sum()
        enriched["current_weight"] = self._safe_divide(enriched["market_value"], total_value)
        enriched["lots"] = enriched["shares"] / TAIWAN_LOT_SIZE
        return enriched

    @staticmethod
    def _safe_divide(numerator, denominator):
        if isinstance(denominator, (int, float)) and denominator == 0:
            return 0
        if isinstance(denominator, pd.Series):
            return numerator.divide(denominator.where(denominator != 0)).fillna(0)
        return numerator / denominator
