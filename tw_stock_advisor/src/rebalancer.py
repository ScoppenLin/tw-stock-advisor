from __future__ import annotations

import pandas as pd


class Rebalancer:
    """Creates practical rebalance suggestions from recommendation results."""

    def build_plan(self, recommendations: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for _, row in recommendations.iterrows():
            if row["action"] not in {"BUY", "ADD", "REDUCE", "SELL"}:
                continue
            current_price = float(row.get("current_price", 0) or 0)
            portfolio_value = float(row.get("portfolio_total_value", 0) or 0)
            target_weight = float(row.get("target_weight", 0) or 0)
            current_shares = int(float(row.get("shares", 0) or 0))
            if pd.isna(current_price) or current_price <= 0:
                continue
            target_shares = 0 if row["action"] == "SELL" else int((portfolio_value * target_weight) // current_price) if current_price > 0 else 0
            trade_shares = target_shares - current_shares
            if row["action"] in {"BUY", "ADD"} and trade_shares <= 0:
                trade_shares = max(1, target_shares)
            if row["action"] == "REDUCE" and trade_shares >= 0:
                max_weight = float(row.get("max_weight", target_weight) or target_weight)
                reduced_weight = min(target_weight, max_weight)
                target_shares = int((portfolio_value * reduced_weight) // current_price) if current_price > 0 else 0
                trade_shares = target_shares - current_shares

            rows.append(
                {
                    "ticker": row["ticker"],
                    "name": row["name"],
                    "action": row["action"],
                    "current_shares": current_shares,
                    "target_shares": target_shares,
                    "trade_shares": trade_shares,
                    "estimated_trade_value": round(abs(trade_shares) * current_price, 2),
                    "reason": row["reason"],
                }
            )
        return pd.DataFrame(rows)
