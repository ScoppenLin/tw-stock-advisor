from __future__ import annotations

import numpy as np
import pandas as pd


class ScoringModel:
    def score_universe(self, features: pd.DataFrame, market_regime: str = "Neutral") -> pd.DataFrame:
        scored = features.copy()
        scored["momentum_score"] = scored.apply(self._momentum_score, axis=1)
        scored["valuation_score"] = scored.apply(self._valuation_proxy_score, axis=1)
        scored["risk_score"] = scored.apply(self._risk_score, axis=1)
        weights = self._weights_for_regime(market_regime)
        scored["total_score"] = (
            scored["momentum_score"] * weights["momentum"]
            + scored["valuation_score"] * weights["valuation"]
            + scored["risk_score"] * weights["risk"]
        ).round(2)
        return scored

    def _momentum_score(self, row: pd.Series) -> float:
        score = 50 + float(row["return_20d"]) * 220 + float(row["return_60d"]) * 80
        score += 8 if row["above_ma20"] else -8
        score += 10 if row["above_ma60"] else -10
        score += 6 if row["above_ma120"] else -6
        if float(row["volume_ratio"]) > 1.15 and float(row["return_20d"]) > 0:
            score += 6
        return self._clip(score)

    def _valuation_proxy_score(self, row: pd.Series) -> float:
        distance_ma60 = float(row["distance_ma60"])
        score = 68
        if distance_ma60 > 0:
            score -= distance_ma60 * 130
        else:
            score += min(abs(distance_ma60) * 80, 12)
        if float(row["return_20d"]) > 0.18:
            score -= 10
        return self._clip(score)

    def _risk_score(self, row: pd.Series) -> float:
        score = 78
        if not row["above_ma20"]:
            score -= 10
        if not row["above_ma60"]:
            score -= 16
        if float(row["return_20d"]) > 0.22:
            score -= 12
        if float(row["price_drawdown"]) < -0.12:
            score -= 16
        if float(row.get("current_weight", 0) or 0) > float(row.get("target_weight", 0) or 0) * 1.3:
            score -= 8
        return self._clip(score)

    @staticmethod
    def _weights_for_regime(market_regime: str) -> dict[str, float]:
        if market_regime == "Risk-On":
            return {"momentum": 0.58, "valuation": 0.12, "risk": 0.30}
        if market_regime == "Bullish":
            return {"momentum": 0.52, "valuation": 0.16, "risk": 0.32}
        if market_regime == "Defensive":
            return {"momentum": 0.38, "valuation": 0.17, "risk": 0.45}
        if market_regime == "Risk-Off":
            return {"momentum": 0.28, "valuation": 0.12, "risk": 0.60}
        return {"momentum": 0.45, "valuation": 0.18, "risk": 0.37}

    @staticmethod
    def _clip(value: float) -> float:
        return round(float(np.clip(value, 0, 100)), 2)
