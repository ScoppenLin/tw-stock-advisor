from __future__ import annotations

import argparse

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


def run(mode: str, source: str = "local") -> dict[str, dict[str, str]]:
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

    portfolio_input = data_loader.load_portfolio()
    account = data_loader.load_account()
    watchlist = data_loader.load_watchlist()
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
    return outputs


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = run(args.mode, args.data_source)
    print("Reports generated:")
    for report_type, paths in outputs.items():
        print(f"- {report_type} CSV: {paths['csv']}")
        print(f"- {report_type} Markdown: {paths['markdown']}")


if __name__ == "__main__":
    main()
