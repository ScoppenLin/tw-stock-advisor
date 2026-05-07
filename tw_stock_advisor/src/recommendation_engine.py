from __future__ import annotations

import pandas as pd

from risk_manager import RiskManager


class RecommendationEngine:
    def __init__(self, risk_manager: RiskManager) -> None:
        self.risk_manager = risk_manager
        self.max_weekly_new_buys = 3

    def generate(self, scored_universe: pd.DataFrame, market_regime: str = "Neutral") -> pd.DataFrame:
        df = self.risk_manager.annotate_limits(scored_universe)
        df["market_regime"] = market_regime
        recommendations = df.apply(self._recommend_row, axis=1, result_type="expand")
        recommended = pd.concat([df, recommendations], axis=1)
        return self._apply_portfolio_constraints(recommended)

    def _recommend_row(self, row: pd.Series) -> dict:
        if pd.isna(row.get("current_price")):
            return self._result("WATCH", "本地尚無價格資料，先保留觀察；待 TWSE 或價格 CSV 更新後再評分", 0.5)

        held = float(row.get("shares", 0) or 0) > 0
        score = float(row.get("total_score", 50) or 50)
        current_weight = float(row.get("current_weight", 0) or 0)
        target_weight = float(row.get("target_weight", 0) or 0)
        over_limit = bool(row.get("over_weight_limit", False))
        can_add = self.risk_manager.can_add(row)
        market_regime = row.get("market_regime", "Neutral")
        is_satellite = row.get("asset_type") in {"satellite", "small_mid"}

        if held:
            if score < 50:
                return self._result("SELL", "總分低於 50，建議賣出或大幅降低曝險", 0.82)
            if market_regime == "Risk-Off" and is_satellite:
                return self._result("REDUCE", "市場進入 Risk-Off，衛星與中小型部位優先降低曝險", 0.84)
            if market_regime == "Defensive" and is_satellite and score < 75:
                return self._result("REDUCE", "市場偏弱且衛星股分數未達強勢門檻，建議降風險", 0.76)
            if over_limit:
                return self._result("REDUCE", "目前權重超過風控上限，建議部分獲利了結或降風險", 0.78)
            if score < 60:
                return self._result("REDUCE", "總分低於 60，動能或風險條件轉弱", 0.72)
            if score >= 80 and can_add and market_regime != "Risk-Off":
                return self._result("ADD", "分數高且目前權重低於目標與風控上限", 0.76)
            if current_weight < target_weight * 0.85 and score >= 70 and can_add and market_regime not in {"Defensive", "Risk-Off"}:
                return self._result("ADD", "權重低於目標且趨勢仍健康", 0.7)
            return self._result("HOLD", "分數與權重位於可接受區間，續抱觀察", 0.68)

        if market_regime == "Risk-Off" and is_satellite:
            return self._result("WATCH", "Risk-Off 狀態禁止新增衛星股，先保留觀察", 0.72)
        if market_regime == "Defensive" and is_satellite:
            return self._result("WATCH", "市場偏弱，暫不新增衛星股", 0.66)
        if score >= 75 and can_add:
            return self._result("BUY", "候選標的分數達買進門檻且未觸及風控限制", 0.7)
        return self._result("WATCH", "尚未達買進條件，保留於觀察清單", 0.58)

    @staticmethod
    def _result(action: str, reason: str, confidence: float) -> dict:
        return {"action": action, "reason": reason, "confidence": confidence}

    def _apply_portfolio_constraints(self, recommendations: pd.DataFrame) -> pd.DataFrame:
        constrained = recommendations.copy()
        buy_candidates = constrained[constrained["action"].eq("BUY")].sort_values("total_score", ascending=False)
        if len(buy_candidates) <= self.max_weekly_new_buys:
            return constrained

        keep_indexes = set(buy_candidates.head(self.max_weekly_new_buys).index)
        downgrade_indexes = [idx for idx in buy_candidates.index if idx not in keep_indexes]
        constrained.loc[downgrade_indexes, "action"] = "WATCH"
        constrained.loc[downgrade_indexes, "reason"] = "符合買進分數，但受單週新增標的不超過 3 檔限制，先保留觀察"
        constrained.loc[downgrade_indexes, "confidence"] = 0.62
        return constrained
