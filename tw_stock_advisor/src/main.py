from __future__ import annotations

import argparse
from datetime import date

from config import ACCOUNT_FILE
from data_loader import DataLoader
from feature_builder import FeatureBuilder
from market_regime import MarketRegimeDetector
from portfolio_manager import PortfolioManager
from rebalancer import Rebalancer
from recommendation_engine import RecommendationEngine
from report_generator import ReportGenerator
from risk_manager import RiskManager
from scoring_model import ScoringModel
from stock_universe import StockUniverseBuilder


def run(
    mode: str,
    source: str = "local",
    input_source: str = "local",
    output_sink: str = "local",
) -> dict[str, dict[str, str]]:
    data_loader = DataLoader()
    portfolio_manager = PortfolioManager()
    universe_builder = StockUniverseBuilder()
    feature_builder = FeatureBuilder()
    scoring_model = ScoringModel()
    risk_manager = RiskManager()
    recommendation_engine = RecommendationEngine(risk_manager)
    report_generator = ReportGenerator()
    market_regime_detector = MarketRegimeDetector()
    rebalancer = Rebalancer()

    sheet_client = None
    if input_source == "google" or output_sink == "google":
        from google_sheets import GoogleSheetsClient

        sheet_client = GoogleSheetsClient.from_env()

    portfolio_input = data_loader.load_portfolio(source=input_source, sheet_client=sheet_client)
    account = data_loader.load_account(source=input_source, sheet_client=sheet_client)
    watchlist = data_loader.load_watchlist(source=input_source, sheet_client=sheet_client)
    tickers = sorted(set(portfolio_input["ticker"]).union(set(watchlist["ticker"])))
    market_data = data_loader.load_market_data(tickers, source=source)

    market_regime = market_regime_detector.detect(market_data.market_indicators)
    portfolio = portfolio_manager.build_portfolio(portfolio_input, market_data.latest_prices)
    planning_capital = account["total_capital"] * (1 - account["reserve_cash_weight"])
    universe = universe_builder.build(portfolio, watchlist, market_data.latest_prices, planning_capital=planning_capital)
    features = feature_builder.build(universe, market_data.price_history)
    scored = scoring_model.score_universe(features, market_regime["regime"])
    recommendations = recommendation_engine.generate(scored, market_regime["regime"])
    rebalance_plan = rebalancer.build_plan(recommendations)

    outputs = {}
    if mode in {"daily", "all"}:
        outputs["daily"] = report_generator.write_daily_reports(recommendations, market_regime)
    if mode in {"weekly", "all"}:
        outputs["weekly"] = report_generator.write_weekly_reports(recommendations, rebalance_plan, market_regime)
    if output_sink == "google":
        today = date.today()
        daily_df = report_generator._build_recommendation_csv(recommendations, today)
        sheet_client.write_dataframe("daily_recommendation", daily_df)
        sheet_client.write_dataframe("weekly_rebalance_plan", rebalance_plan)
        sheet_client.write_sections(
            "daily_report",
            report_generator.build_daily_sheet_sections(recommendations, market_regime, today),
        )
        sheet_client.write_sections(
            "weekly_report",
            report_generator.build_weekly_sheet_sections(recommendations, rebalance_plan, market_regime, today),
        )
        outputs["google_sheets"] = {"spreadsheet_id": sheet_client.spreadsheet_id, "status": "updated"}
    return outputs


def bootstrap_google_sheets() -> None:
    from google_sheets import GoogleSheetsClient

    data_loader = DataLoader()
    sheet_client = GoogleSheetsClient.from_env()
    account = pd_read_csv_safe(ACCOUNT_FILE)
    portfolio = data_loader.load_portfolio()
    watchlist = data_loader.load_watchlist()
    sheet_client.bootstrap_from_csv(account, portfolio, watchlist)
    print("Google Sheet template initialized:")
    print(f"- spreadsheet_id: {sheet_client.spreadsheet_id}")


def pd_read_csv_safe(path):
    import pandas as pd

    return pd.read_csv(path, dtype={"ticker": str})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Taiwan stock advisory recommendation engine")
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly", "all"],
        default="all",
        help="Report workflow to run. Default: all",
    )
    parser.add_argument(
        "--data-source",
        choices=["local", "twse"],
        default="local",
        help="Latest price source. TWSE falls back to local CSV if unavailable. Default: local",
    )
    parser.add_argument(
        "--input-source",
        choices=["local", "google"],
        default="local",
        help="Where account, portfolio, and watchlist are read from. Default: local",
    )
    parser.add_argument(
        "--output-sink",
        choices=["local", "google"],
        default="local",
        help="Where reports are written in addition to local files. Default: local",
    )
    parser.add_argument(
        "--bootstrap-google-sheets",
        action="store_true",
        help="Create/update account, portfolio, and watchlist worksheets from local CSV files, then exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.bootstrap_google_sheets:
        bootstrap_google_sheets()
        return
    outputs = run(args.mode, args.data_source, args.input_source, args.output_sink)
    print("Reports generated:")
    for report_type, paths in outputs.items():
        if "csv" in paths and "markdown" in paths:
            print(f"- {report_type} CSV: {paths['csv']}")
            print(f"- {report_type} Markdown: {paths['markdown']}")
        else:
            details = ", ".join(f"{key}={value}" for key, value in paths.items())
            print(f"- {report_type}: {details}")


if __name__ == "__main__":
    main()
