from __future__ import annotations

import pandas as pd


class StockUniverseBuilder:
    candidate_target_weights = {
        "etf": 0.10,
        "core_stock": 0.05,
        "large_cap": 0.05,
        "satellite": 0.03,
        "small_mid": 0.02,
    }

    def build(
        self,
        portfolio: pd.DataFrame,
        watchlist: pd.DataFrame,
        latest_prices: pd.DataFrame,
        planning_capital: float | None = None,
    ) -> pd.DataFrame:
        watchlist_base = watchlist.merge(latest_prices, on="ticker", how="left")
        portfolio_columns = [
            "ticker",
            "shares",
            "avg_cost",
            "target_weight",
            "market_value",
            "unrealized_pnl",
            "unrealized_pnl_pct",
            "current_weight",
            "lots",
        ]
        universe = watchlist_base.merge(portfolio[portfolio_columns], on="ticker", how="left")
        universe["shares"] = universe["shares"].fillna(0)
        universe["target_weight"] = universe.apply(self._target_weight, axis=1)
        universe["current_weight"] = universe["current_weight"].fillna(0)
        portfolio_value = float(portfolio["market_value"].sum())
        universe["portfolio_total_value"] = planning_capital if planning_capital and planning_capital > portfolio_value else portfolio_value
        return universe

    def _target_weight(self, row: pd.Series) -> float:
        if pd.notna(row.get("target_weight")):
            return float(row["target_weight"])
        return self.candidate_target_weights.get(row["asset_type"], 0.02)
