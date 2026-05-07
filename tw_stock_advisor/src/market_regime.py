from __future__ import annotations

import pandas as pd


class MarketRegimeDetector:
    """Detects broad Taiwan market risk posture from daily indicators."""

    def detect(self, market_indicators: pd.DataFrame) -> dict:
        if market_indicators.empty:
            return {"regime": "Neutral", "score": 0, "reasons": ["缺少市場指標資料，採中性判斷"]}

        row = market_indicators.sort_values("date").iloc[-1]
        score = 0
        reasons = []

        ma_checks = [
            ("20 日均線", row["twii_close"] > row["twii_ma20"]),
            ("60 日均線", row["twii_close"] > row["twii_ma60"]),
            ("120 日均線", row["twii_close"] > row["twii_ma120"]),
        ]
        above_ma_count = sum(1 for _, passed in ma_checks if passed)
        score += above_ma_count - (3 - above_ma_count)
        reasons.append(f"加權指數高於 {above_ma_count}/3 條重要均線")

        score += self._positive_negative(row["twii_return_20d"], 0.02, -0.04)
        score += self._positive_negative(row["foreign_buy_5d"], 0, 0)
        score += self._positive_negative(row["foreign_buy_20d"], 0, 0)
        score += self._positive_negative(row["nasdaq_return_20d"], 0.02, -0.04)
        score += self._positive_negative(row["sox_return_20d"], 0.02, -0.04)

        if row["volume_ratio_20d"] >= 1.1 and row["twii_return_20d"] > 0:
            score += 1
            reasons.append("成交量放大且大盤 20 日報酬為正")
        elif row["volume_ratio_20d"] < 0.85:
            score -= 1
            reasons.append("成交量低於近期均量")

        if row["vix"] >= 25:
            score -= 2
            reasons.append("VIX 偏高，全球風險情緒轉弱")
        elif row["vix"] <= 18:
            score += 1
            reasons.append("VIX 低於 18，全球風險情緒穩定")

        if row["twd_return_20d"] < -0.02:
            score -= 1
            reasons.append("台幣 20 日走弱，外資與匯率壓力升高")
        elif row["twd_return_20d"] > 0.01:
            score += 1
            reasons.append("台幣 20 日偏強，有利資金風險偏好")

        return {"regime": self._label(score), "score": score, "reasons": reasons}

    @staticmethod
    def _positive_negative(value: float, positive_threshold: float, negative_threshold: float) -> int:
        if value > positive_threshold:
            return 1
        if value < negative_threshold:
            return -1
        return 0

    @staticmethod
    def _label(score: int) -> str:
        if score >= 7:
            return "Risk-On"
        if score >= 3:
            return "Bullish"
        if score <= -5:
            return "Risk-Off"
        if score <= -2:
            return "Defensive"
        return "Neutral"
