from __future__ import annotations

from datetime import date

import pandas as pd

from config import DAILY_REPORTS_DIR, WEEKLY_REPORTS_DIR


class ReportGenerator:
    def write_daily_reports(
        self,
        recommendations: pd.DataFrame,
        market_regime: dict,
        report_date: date | None = None,
    ) -> dict[str, str]:
        DAILY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_date = report_date or date.today()

        csv_path = DAILY_REPORTS_DIR / "daily_recommendation.csv"
        md_path = DAILY_REPORTS_DIR / "daily_report.md"

        csv_df = self._build_recommendation_csv(recommendations, report_date)
        csv_df.to_csv(csv_path, index=False)
        md_path.write_text(self._build_daily_markdown(recommendations, market_regime, report_date), encoding="utf-8")
        return {"csv": str(csv_path), "markdown": str(md_path)}

    def write_weekly_reports(
        self,
        recommendations: pd.DataFrame,
        rebalance_plan: pd.DataFrame,
        market_regime: dict,
        report_date: date | None = None,
    ) -> dict[str, str]:
        WEEKLY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_date = report_date or date.today()

        csv_path = WEEKLY_REPORTS_DIR / "weekly_rebalance_plan.csv"
        md_path = WEEKLY_REPORTS_DIR / "weekly_report.md"
        rebalance_plan.to_csv(csv_path, index=False)
        md_path.write_text(
            self._build_weekly_markdown(recommendations, rebalance_plan, market_regime, report_date),
            encoding="utf-8",
        )
        return {"csv": str(csv_path), "markdown": str(md_path)}

    def _build_recommendation_csv(self, recommendations: pd.DataFrame, report_date: date) -> pd.DataFrame:
        df = recommendations.copy()
        df["date"] = report_date.isoformat()
        df["current_shares"] = df.get("shares", 0).fillna(0).round(0).astype(int)
        df["target_shares"] = df.apply(self._estimate_target_shares, axis=1)
        df["trade_shares"] = df["target_shares"] - df["current_shares"]
        output_columns = [
            "date",
            "ticker",
            "name",
            "action",
            "current_shares",
            "target_shares",
            "trade_shares",
            "current_weight",
            "target_weight",
            "reason",
            "confidence",
        ]
        return df[output_columns].sort_values(["action", "ticker"])

    def _build_daily_markdown(self, recommendations: pd.DataFrame, market_regime: dict, report_date: date) -> str:
        held = recommendations[recommendations.get("shares", 0).fillna(0) > 0].copy()
        trades = recommendations[recommendations["action"].isin(["BUY", "ADD", "REDUCE", "SELL"])].copy()
        watch = recommendations[recommendations["action"].eq("WATCH")].copy()

        lines = [
            "# 台股投資日報",
            "",
            f"日期：{report_date.isoformat()}",
            "",
            "## 一、市場狀態",
            "",
            f"今日市場狀態：{market_regime['regime']}（分數 {market_regime['score']}）",
            "",
            self._bullet_list(market_regime.get("reasons", [])),
            "",
            "## 二、目前持股",
            "",
            self._markdown_table(
                held,
                ["ticker", "name", "shares", "lots", "current_price", "market_value", "unrealized_pnl_pct", "current_weight", "target_weight", "action"],
            ),
            "",
            "## 三、本日建議交易",
            "",
            self._markdown_table(trades, ["ticker", "name", "action", "total_score", "current_weight", "target_weight", "reason"]),
            "",
            "## 四、新候選股票",
            "",
            self._markdown_table(watch, ["ticker", "name", "asset_type", "sector", "total_score", "reason"]),
            "",
            "## 五、主要風險",
            "",
            "- 第一版以價格與均線為主，尚未納入法人籌碼、月營收與完整估值資料。",
            "- 建議結果只作為投資決策輔助，不代表自動下單訊號。",
            "- 衛星股需嚴格控管單一持股比例與停損紀律。",
            "",
            "## 六、下週觀察重點",
            "",
            "- 補上 TWSE OpenAPI 或其他穩定資料源。",
            "- 加入市場狀態判斷與週報再平衡模型。",
            "- 連續追蹤 4 到 8 週，檢查建議穩定度。",
            "",
        ]
        return "\n".join(lines)

    def _build_weekly_markdown(
        self,
        recommendations: pd.DataFrame,
        rebalance_plan: pd.DataFrame,
        market_regime: dict,
        report_date: date,
    ) -> str:
        held = recommendations[recommendations.get("shares", 0).fillna(0) > 0].copy()
        new_candidates = recommendations[recommendations["action"].isin(["BUY", "WATCH"])].copy()
        risk_items = recommendations[recommendations["action"].isin(["REDUCE", "SELL"])].copy()

        lines = [
            "# 台股投資週報",
            "",
            f"日期：{report_date.isoformat()}",
            "",
            "## 一、本週投資結論",
            "",
            self._weekly_summary(recommendations, market_regime),
            "",
            "## 二、市場狀態",
            "",
            f"{market_regime['regime']}（分數 {market_regime['score']}）",
            "",
            self._bullet_list(market_regime.get("reasons", [])),
            "",
            "## 三、持股檢查",
            "",
            self._markdown_table(
                held,
                ["ticker", "name", "asset_type", "current_weight", "target_weight", "max_weight", "total_score", "action", "reason"],
            ),
            "",
            "## 四、建議交易清單",
            "",
            self._markdown_table(
                rebalance_plan,
                ["ticker", "name", "action", "current_shares", "target_shares", "trade_shares", "estimated_trade_value", "reason"],
            ),
            "",
            "## 五、新候選股票",
            "",
            self._markdown_table(new_candidates, ["ticker", "name", "asset_type", "sector", "total_score", "action", "reason"]),
            "",
            "## 六、主要風險",
            "",
            self._markdown_table(risk_items, ["ticker", "name", "asset_type", "current_weight", "max_weight", "total_score", "action", "reason"]),
            "",
            "## 七、下週觀察重點",
            "",
            "- 檢查市場狀態是否從偏多轉向中性或防禦。",
            "- 優先處理超過風控上限的持股，再考慮新增衛星股。",
            "- 若連續兩週出現 SELL / REDUCE，應回頭檢查基本面與產業邏輯。",
            "",
        ]
        return "\n".join(lines)

    def _estimate_target_shares(self, row: pd.Series) -> int:
        current_price = float(row.get("current_price", 0) or 0)
        total_value = float(row.get("portfolio_total_value", 0) or 0)
        target_weight = float(row.get("target_weight", 0) or 0)
        if pd.isna(current_price) or current_price <= 0 or total_value <= 0:
            return 0
        return int((total_value * target_weight) // current_price)

    @staticmethod
    def _markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
        if df.empty:
            return "_無_"
        table = df.copy()
        for col in columns:
            if col not in table.columns:
                table[col] = ""
        table = table[columns].copy()
        for col in ["current_weight", "target_weight", "unrealized_pnl_pct", "max_weight"]:
            if col in table.columns:
                table[col] = table[col].apply(lambda value: f"{float(value):.2%}" if value != "" else "")
        for col in ["market_value", "current_price", "estimated_trade_value"]:
            if col in table.columns:
                table[col] = table[col].apply(lambda value: f"{float(value):,.2f}" if value != "" else "")
        for col in ["lots", "total_score"]:
            if col in table.columns:
                table[col] = table[col].apply(lambda value: f"{float(value):.2f}" if value != "" else "")
        table = table.fillna("")
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in table.to_numpy()]
        return "\n".join([header, separator, *rows])

    @staticmethod
    def _bullet_list(items: list[str]) -> str:
        if not items:
            return "- 無額外說明"
        return "\n".join(f"- {item}" for item in items)

    @staticmethod
    def _weekly_summary(recommendations: pd.DataFrame, market_regime: dict) -> str:
        counts = recommendations["action"].value_counts().to_dict()
        buy_count = counts.get("BUY", 0)
        add_count = counts.get("ADD", 0)
        reduce_count = counts.get("REDUCE", 0)
        sell_count = counts.get("SELL", 0)
        return (
            f"本週市場狀態為 {market_regime['regime']}。"
            f"系統建議 BUY {buy_count} 檔、ADD {add_count} 檔、"
            f"REDUCE {reduce_count} 檔、SELL {sell_count} 檔。"
        )
