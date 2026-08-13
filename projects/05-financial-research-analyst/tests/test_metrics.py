"""Behavior tests for deterministic financial research metrics."""

from __future__ import annotations

from datetime import date

import pytest

from financial_research import metrics
from financial_research.metrics import (
    PricePoint,
    load_price_history,
    render_research_brief,
    summarize_price_history,
)


def test_summarize_price_history_calculates_key_return_and_risk_metrics() -> None:
    prices = [
        PricePoint(date(2026, 1, 2), "NOVA", 100.0, 1_200_000),
        PricePoint(date(2026, 1, 3), "NOVA", 102.0, 1_300_000),
        PricePoint(date(2026, 1, 4), "NOVA", 101.0, 1_100_000),
        PricePoint(date(2026, 1, 5), "NOVA", 106.0, 1_500_000),
        PricePoint(date(2026, 1, 6), "NOVA", 104.0, 1_400_000),
        PricePoint(date(2026, 1, 7), "NOVA", 110.0, 1_800_000),
    ]

    summary = summarize_price_history(prices)

    assert summary.ticker == "NOVA"
    assert summary.observation_count == 6
    assert summary.start_date == date(2026, 1, 2)
    assert summary.end_date == date(2026, 1, 7)
    assert summary.start_close == 100.0
    assert summary.end_close == 110.0
    assert summary.cumulative_return_pct == pytest.approx(10.0)
    assert summary.average_return_pct == pytest.approx(1.970508, abs=0.000001)
    assert summary.annualized_volatility_pct == pytest.approx(54.356031, abs=0.000001)
    assert summary.max_drawdown_pct == pytest.approx(-1.886792, abs=0.000001)


def test_summarize_price_history_rejects_non_positive_annualization_periods() -> None:
    prices = [
        PricePoint(date(2026, 1, 2), "NOVA", 100.0, 1_200_000),
        PricePoint(date(2026, 1, 3), "NOVA", 102.0, 1_300_000),
    ]

    with pytest.raises(ValueError, match="periods_per_year must be positive"):
        summarize_price_history(prices, periods_per_year=0)


def test_summarize_fundamentals_calculates_valuation_and_profitability_ratios() -> None:
    snapshot = metrics.FundamentalSnapshot(
        ticker="NOVA",
        as_of_date=date(2026, 1, 7),
        market_cap=500_000_000.0,
        revenue_ttm=100_000_000.0,
        net_income_ttm=15_000_000.0,
        total_equity=75_000_000.0,
    )

    summary = metrics.summarize_fundamentals(snapshot)

    assert summary.ticker == "NOVA"
    assert summary.as_of_date == date(2026, 1, 7)
    assert summary.price_to_sales_ratio == pytest.approx(5.0)
    assert summary.net_margin_pct == pytest.approx(15.0)
    assert summary.return_on_equity_pct == pytest.approx(20.0)


def test_summarize_fundamentals_trend_compares_oldest_and_latest_snapshots() -> None:
    trend = metrics.summarize_fundamentals_trend(
        [
            metrics.FundamentalSnapshot(
                ticker="NOVA",
                as_of_date=date(2025, 10, 7),
                market_cap=400_000_000.0,
                revenue_ttm=90_000_000.0,
                net_income_ttm=12_000_000.0,
                total_equity=70_000_000.0,
            ),
            metrics.FundamentalSnapshot(
                ticker="NOVA",
                as_of_date=date(2026, 1, 7),
                market_cap=500_000_000.0,
                revenue_ttm=100_000_000.0,
                net_income_ttm=15_000_000.0,
                total_equity=75_000_000.0,
            ),
        ]
    )

    assert trend.ticker == "NOVA"
    assert trend.observation_count == 2
    assert trend.start_date == date(2025, 10, 7)
    assert trend.end_date == date(2026, 1, 7)
    assert trend.start_price_to_sales_ratio == pytest.approx(4.444444)
    assert trend.end_price_to_sales_ratio == pytest.approx(5.0)
    assert trend.price_to_sales_change == pytest.approx(0.555556)
    assert trend.net_margin_change_points == pytest.approx(1.666667)
    assert trend.return_on_equity_change_points == pytest.approx(2.857143)


def test_summarize_fundamentals_rejects_non_positive_ratio_denominators() -> None:
    snapshot = metrics.FundamentalSnapshot(
        ticker="NOVA",
        as_of_date=date(2026, 1, 7),
        market_cap=500_000_000.0,
        revenue_ttm=0.0,
        net_income_ttm=15_000_000.0,
        total_equity=75_000_000.0,
    )

    with pytest.raises(ValueError, match="TTM revenue must be positive"):
        metrics.summarize_fundamentals(snapshot)


def test_summarize_benchmark_sensitivity_calculates_correlation_and_beta() -> None:
    asset_prices = [
        PricePoint(date(2026, 4, 1), "NOVA", 100.0, 1_200_000),
        PricePoint(date(2026, 4, 2), "NOVA", 120.0, 1_300_000),
        PricePoint(date(2026, 4, 3), "NOVA", 96.0, 1_400_000),
    ]
    benchmark_prices = [
        PricePoint(date(2026, 4, 1), "MKT", 100.0, 4_200_000),
        PricePoint(date(2026, 4, 2), "MKT", 110.0, 4_300_000),
        PricePoint(date(2026, 4, 3), "MKT", 99.0, 4_400_000),
    ]

    sensitivity = metrics.summarize_benchmark_sensitivity(asset_prices, benchmark_prices)

    assert sensitivity.asset_ticker == "NOVA"
    assert sensitivity.benchmark_ticker == "MKT"
    assert sensitivity.observation_count == 3
    assert sensitivity.correlation == pytest.approx(1.0)
    assert sensitivity.beta == pytest.approx(2.0)


def test_summarize_moving_average_trend_flags_current_uptrend() -> None:
    prices = [
        PricePoint(date(2026, 1, 2), "NOVA", 100.0, 1_200_000),
        PricePoint(date(2026, 1, 3), "NOVA", 102.0, 1_300_000),
        PricePoint(date(2026, 1, 4), "NOVA", 101.0, 1_100_000),
        PricePoint(date(2026, 1, 5), "NOVA", 106.0, 1_500_000),
        PricePoint(date(2026, 1, 6), "NOVA", 104.0, 1_400_000),
        PricePoint(date(2026, 1, 7), "NOVA", 110.0, 1_800_000),
    ]

    trend = metrics.summarize_moving_average_trend(prices, short_window=3, long_window=5)

    assert trend.ticker == "NOVA"
    assert trend.short_window == 3
    assert trend.long_window == 5
    assert trend.latest_close == 110.0
    assert trend.short_moving_average == pytest.approx(106.666667, abs=0.000001)
    assert trend.long_moving_average == pytest.approx(104.6)
    assert trend.close_vs_long_ma_pct == pytest.approx(5.162524, abs=0.000001)
    assert trend.short_vs_long_ma_pct == pytest.approx(1.975781, abs=0.000001)
    assert trend.trend_label == "uptrend"


def test_build_risk_notes_highlights_elevated_volatility_and_supportive_trend() -> None:
    asset_prices = [
        PricePoint(date(2026, 1, 2), "NOVA", 100.0, 1_200_000),
        PricePoint(date(2026, 1, 3), "NOVA", 102.0, 1_300_000),
        PricePoint(date(2026, 1, 4), "NOVA", 101.0, 1_100_000),
        PricePoint(date(2026, 1, 5), "NOVA", 106.0, 1_500_000),
        PricePoint(date(2026, 1, 6), "NOVA", 104.0, 1_400_000),
        PricePoint(date(2026, 1, 7), "NOVA", 110.0, 1_800_000),
    ]
    benchmark_prices = [
        PricePoint(date(2026, 1, 2), "MKT", 100.0, 4_200_000),
        PricePoint(date(2026, 1, 3), "MKT", 101.0, 4_300_000),
        PricePoint(date(2026, 1, 4), "MKT", 102.0, 4_100_000),
        PricePoint(date(2026, 1, 5), "MKT", 101.0, 4_500_000),
        PricePoint(date(2026, 1, 6), "MKT", 103.0, 4_400_000),
        PricePoint(date(2026, 1, 7), "MKT", 105.0, 4_800_000),
    ]

    notes = metrics.build_risk_notes(
        summarize_price_history(asset_prices),
        benchmark=summarize_price_history(benchmark_prices),
        trend=metrics.summarize_moving_average_trend(asset_prices),
    )

    assert (
        "- Annualized volatility is elevated at 54.36%; "
        "review position sizing and scenario-test wider return swings."
    ) in notes
    assert "- Cumulative return led MKT by 5.00 percentage points over the sample window." in notes
    assert (
        "- Moving-average signal is uptrend; latest close is 5.16% above "
        "the 5-day moving average."
    ) in notes
    assert notes[-1] == "- Educational portfolio demo, not investment advice."


def test_build_risk_notes_flags_drawdown_underperformance_and_downtrend() -> None:
    asset_prices = [
        PricePoint(date(2026, 2, 2), "NOVA", 100.0, 1_200_000),
        PricePoint(date(2026, 2, 3), "NOVA", 98.0, 1_250_000),
        PricePoint(date(2026, 2, 4), "NOVA", 95.0, 1_300_000),
        PricePoint(date(2026, 2, 5), "NOVA", 93.0, 1_350_000),
        PricePoint(date(2026, 2, 6), "NOVA", 90.0, 1_400_000),
        PricePoint(date(2026, 2, 7), "NOVA", 88.0, 1_450_000),
    ]
    benchmark_prices = [
        PricePoint(date(2026, 2, 2), "MKT", 100.0, 4_200_000),
        PricePoint(date(2026, 2, 3), "MKT", 101.0, 4_300_000),
        PricePoint(date(2026, 2, 4), "MKT", 102.0, 4_100_000),
        PricePoint(date(2026, 2, 5), "MKT", 103.0, 4_500_000),
        PricePoint(date(2026, 2, 6), "MKT", 104.0, 4_400_000),
        PricePoint(date(2026, 2, 7), "MKT", 105.0, 4_800_000),
    ]

    notes = metrics.build_risk_notes(
        summarize_price_history(asset_prices),
        benchmark=summarize_price_history(benchmark_prices),
        trend=metrics.summarize_moving_average_trend(asset_prices),
    )

    assert "- Cumulative return trailed MKT by 17.00 percentage points over the sample window." in notes
    assert "- Maximum drawdown reached -12.00%, beyond the -10.00% review threshold." in notes
    assert (
        "- Moving-average signal is downtrend; latest close is 5.17% below "
        "the 5-day moving average."
    ) in notes


def test_build_risk_notes_identifies_asset_specific_drawdown_against_benchmark() -> None:
    asset_prices = [
        PricePoint(date(2026, 2, 2), "NOVA", 100.0, 1_200_000),
        PricePoint(date(2026, 2, 3), "NOVA", 98.0, 1_250_000),
        PricePoint(date(2026, 2, 4), "NOVA", 95.0, 1_300_000),
        PricePoint(date(2026, 2, 5), "NOVA", 93.0, 1_350_000),
        PricePoint(date(2026, 2, 6), "NOVA", 90.0, 1_400_000),
        PricePoint(date(2026, 2, 7), "NOVA", 88.0, 1_450_000),
    ]
    benchmark_prices = [
        PricePoint(date(2026, 2, 2), "MKT", 100.0, 4_200_000),
        PricePoint(date(2026, 2, 3), "MKT", 101.0, 4_300_000),
        PricePoint(date(2026, 2, 4), "MKT", 102.0, 4_100_000),
        PricePoint(date(2026, 2, 5), "MKT", 103.0, 4_500_000),
        PricePoint(date(2026, 2, 6), "MKT", 104.0, 4_400_000),
        PricePoint(date(2026, 2, 7), "MKT", 105.0, 4_800_000),
    ]

    notes = metrics.build_risk_notes(
        summarize_price_history(asset_prices),
        benchmark=summarize_price_history(benchmark_prices),
    )

    assert (
        "- Drawdown looks asset-specific: NOVA fell 12.00 percentage points more "
        "than MKT from peak to trough."
    ) in notes


def test_build_risk_notes_identifies_market_wide_drawdown_against_benchmark() -> None:
    asset_prices = [
        PricePoint(date(2026, 3, 2), "NOVA", 100.0, 1_200_000),
        PricePoint(date(2026, 3, 3), "NOVA", 98.0, 1_250_000),
        PricePoint(date(2026, 3, 4), "NOVA", 92.0, 1_300_000),
        PricePoint(date(2026, 3, 5), "NOVA", 88.0, 1_350_000),
        PricePoint(date(2026, 3, 6), "NOVA", 90.0, 1_400_000),
    ]
    benchmark_prices = [
        PricePoint(date(2026, 3, 2), "MKT", 100.0, 4_200_000),
        PricePoint(date(2026, 3, 3), "MKT", 96.0, 4_300_000),
        PricePoint(date(2026, 3, 4), "MKT", 90.0, 4_100_000),
        PricePoint(date(2026, 3, 5), "MKT", 85.0, 4_500_000),
        PricePoint(date(2026, 3, 6), "MKT", 88.0, 4_400_000),
    ]

    notes = metrics.build_risk_notes(
        summarize_price_history(asset_prices),
        benchmark=summarize_price_history(benchmark_prices),
    )

    assert (
        "- Drawdown looks market-wide: MKT fell 15.00% versus NOVA's 12.00% "
        "from peak to trough."
    ) in notes


def test_package_exports_fundamentals_api() -> None:
    from financial_research import (
        FundamentalSnapshot,
        FundamentalsSummary,
        load_fundamental_snapshot,
        summarize_fundamentals,
    )

    assert FundamentalSnapshot is metrics.FundamentalSnapshot
    assert FundamentalsSummary is metrics.FundamentalsSummary
    assert load_fundamental_snapshot is metrics.load_fundamental_snapshot
    assert summarize_fundamentals is metrics.summarize_fundamentals


def test_package_exports_fundamentals_trend_api() -> None:
    from financial_research import (
        FundamentalsTrend,
        load_fundamental_history,
        summarize_fundamentals_trend,
    )

    assert FundamentalsTrend is metrics.FundamentalsTrend
    assert load_fundamental_history is metrics.load_fundamental_history
    assert summarize_fundamentals_trend is metrics.summarize_fundamentals_trend


def test_package_exports_benchmark_sensitivity_api() -> None:
    from financial_research import BenchmarkSensitivity, summarize_benchmark_sensitivity

    assert BenchmarkSensitivity is metrics.BenchmarkSensitivity
    assert summarize_benchmark_sensitivity is metrics.summarize_benchmark_sensitivity


def test_package_exports_moving_average_trend_and_risk_note_api() -> None:
    from financial_research import (
        MovingAverageTrend,
        build_risk_notes,
        summarize_moving_average_trend,
    )

    assert MovingAverageTrend is metrics.MovingAverageTrend
    assert summarize_moving_average_trend is metrics.summarize_moving_average_trend
    assert build_risk_notes is metrics.build_risk_notes


def test_package_exports_the_html_renderer() -> None:
    from financial_research import render_research_brief_html

    assert render_research_brief_html is metrics.render_research_brief_html


def test_load_price_history_filters_ticker_and_sorts_rows(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    price_file.write_text(
        "date,ticker,close,volume\n"
        "2026-01-04,NOVA,101,1100000\n"
        "2026-01-02,NOVA,100,1200000\n"
        "2026-01-03,BENCH,101,2200000\n"
        "2026-01-03,NOVA,102,1300000\n",
        encoding="utf-8",
    )

    prices = load_price_history(price_file, ticker="nova")

    assert [point.date for point in prices] == [
        date(2026, 1, 2),
        date(2026, 1, 3),
        date(2026, 1, 4),
    ]
    assert [point.close for point in prices] == [100.0, 102.0, 101.0]
    assert all(point.ticker == "NOVA" for point in prices)


def test_load_fundamental_snapshot_filters_ticker_and_normalizes_input(tmp_path) -> None:
    fundamentals_file = tmp_path / "fundamentals.csv"
    fundamentals_file.write_text(
        "as_of_date,ticker,market_cap,revenue_ttm,net_income_ttm,total_equity\n"
        "2026-01-07,NOVA,500000000,100000000,15000000,75000000\n"
        "2026-01-07,MKT,900000000,200000000,30000000,250000000\n",
        encoding="utf-8",
    )

    snapshot = metrics.load_fundamental_snapshot(fundamentals_file, ticker="nova")

    assert snapshot.ticker == "NOVA"
    assert snapshot.as_of_date == date(2026, 1, 7)
    assert snapshot.market_cap == 500_000_000.0
    assert snapshot.net_income_ttm == 15_000_000.0


def test_load_fundamental_snapshot_uses_the_most_recent_ticker_row(tmp_path) -> None:
    fundamentals_file = tmp_path / "fundamentals.csv"
    fundamentals_file.write_text(
        "as_of_date,ticker,market_cap,revenue_ttm,net_income_ttm,total_equity\n"
        "2026-01-03,NOVA,450000000,90000000,12000000,70000000\n"
        "2026-01-07,NOVA,500000000,100000000,15000000,75000000\n",
        encoding="utf-8",
    )

    snapshot = metrics.load_fundamental_snapshot(fundamentals_file, ticker="NOVA")

    assert snapshot.as_of_date == date(2026, 1, 7)
    assert snapshot.market_cap == 500_000_000.0


def test_render_research_brief_includes_fundamentals_snapshot() -> None:
    asset = summarize_price_history(
        [
            PricePoint(date(2026, 1, 2), "NOVA", 100.0, 1_200_000),
            PricePoint(date(2026, 1, 7), "NOVA", 110.0, 1_800_000),
        ]
    )
    fundamentals = metrics.summarize_fundamentals(
        metrics.FundamentalSnapshot(
            ticker="NOVA",
            as_of_date=date(2026, 1, 7),
            market_cap=500_000_000.0,
            revenue_ttm=100_000_000.0,
            net_income_ttm=15_000_000.0,
            total_equity=75_000_000.0,
        )
    )

    markdown = render_research_brief(asset, fundamentals=fundamentals)

    assert "## Fundamentals snapshot" in markdown
    assert "As of: 2026-01-07 (TTM inputs)" in markdown
    assert "| Price-to-sales | 5.00x |" in markdown
    assert "| Net margin | 15.00% |" in markdown
    assert "| Return on equity | 20.00% |" in markdown


def test_render_research_brief_includes_fundamentals_trend_comparison() -> None:
    asset = summarize_price_history(
        [
            PricePoint(date(2026, 1, 2), "NOVA", 100.0, 1_200_000),
            PricePoint(date(2026, 1, 7), "NOVA", 110.0, 1_800_000),
        ]
    )
    snapshots = [
        metrics.FundamentalSnapshot(
            ticker="NOVA",
            as_of_date=date(2025, 10, 7),
            market_cap=400_000_000.0,
            revenue_ttm=90_000_000.0,
            net_income_ttm=12_000_000.0,
            total_equity=70_000_000.0,
        ),
        metrics.FundamentalSnapshot(
            ticker="NOVA",
            as_of_date=date(2026, 1, 7),
            market_cap=500_000_000.0,
            revenue_ttm=100_000_000.0,
            net_income_ttm=15_000_000.0,
            total_equity=75_000_000.0,
        ),
    ]
    fundamentals = metrics.summarize_fundamentals(snapshots[-1])
    trend = metrics.summarize_fundamentals_trend(snapshots)

    markdown = render_research_brief(
        asset,
        fundamentals=fundamentals,
        fundamentals_trend=trend,
    )

    assert "## Fundamentals trend" in markdown
    assert "Coverage: 2025-10-07 to 2026-01-07 (2 observations)." in markdown
    assert "| Price-to-sales | 4.44x | 5.00x | +0.56x |" in markdown
    assert "| Net margin | 13.33% | 15.00% | +1.67 pts |" in markdown
    assert "| Return on equity | 17.14% | 20.00% | +2.86 pts |" in markdown


def test_render_research_brief_includes_benchmark_sensitivity() -> None:
    asset_prices = [
        PricePoint(date(2026, 4, 1), "NOVA", 100.0, 1_200_000),
        PricePoint(date(2026, 4, 2), "NOVA", 120.0, 1_300_000),
        PricePoint(date(2026, 4, 3), "NOVA", 96.0, 1_400_000),
    ]
    benchmark_prices = [
        PricePoint(date(2026, 4, 1), "MKT", 100.0, 4_200_000),
        PricePoint(date(2026, 4, 2), "MKT", 110.0, 4_300_000),
        PricePoint(date(2026, 4, 3), "MKT", 99.0, 4_400_000),
    ]

    markdown = render_research_brief(
        summarize_price_history(asset_prices),
        benchmark=summarize_price_history(benchmark_prices),
        benchmark_sensitivity=metrics.summarize_benchmark_sensitivity(
            asset_prices,
            benchmark_prices,
        ),
    )

    assert "## Benchmark sensitivity" in markdown
    assert "Aligned observations: 3." in markdown
    assert "| Return correlation | 1.00 |" in markdown
    assert "| Beta vs MKT | 2.00 |" in markdown


def test_render_research_brief_compares_asset_to_benchmark() -> None:
    asset = summarize_price_history(
        [
            PricePoint(date(2026, 1, 2), "NOVA", 100.0, 1_200_000),
            PricePoint(date(2026, 1, 3), "NOVA", 102.0, 1_300_000),
            PricePoint(date(2026, 1, 4), "NOVA", 101.0, 1_100_000),
            PricePoint(date(2026, 1, 5), "NOVA", 106.0, 1_500_000),
            PricePoint(date(2026, 1, 6), "NOVA", 104.0, 1_400_000),
            PricePoint(date(2026, 1, 7), "NOVA", 110.0, 1_800_000),
        ]
    )
    benchmark = summarize_price_history(
        [
            PricePoint(date(2026, 1, 2), "MKT", 100.0, 4_200_000),
            PricePoint(date(2026, 1, 3), "MKT", 101.0, 4_300_000),
            PricePoint(date(2026, 1, 4), "MKT", 102.0, 4_100_000),
            PricePoint(date(2026, 1, 5), "MKT", 101.0, 4_500_000),
            PricePoint(date(2026, 1, 6), "MKT", 103.0, 4_400_000),
            PricePoint(date(2026, 1, 7), "MKT", 105.0, 4_800_000),
        ]
    )

    trend = metrics.summarize_moving_average_trend(
        [
            PricePoint(date(2026, 1, 2), "NOVA", 100.0, 1_200_000),
            PricePoint(date(2026, 1, 3), "NOVA", 102.0, 1_300_000),
            PricePoint(date(2026, 1, 4), "NOVA", 101.0, 1_100_000),
            PricePoint(date(2026, 1, 5), "NOVA", 106.0, 1_500_000),
            PricePoint(date(2026, 1, 6), "NOVA", 104.0, 1_400_000),
            PricePoint(date(2026, 1, 7), "NOVA", 110.0, 1_800_000),
        ]
    )

    markdown = render_research_brief(asset, benchmark=benchmark, trend=trend)

    assert markdown.startswith("# NOVA Financial Research Brief")
    assert "Coverage window: 2026-01-02 to 2026-01-07" in markdown
    assert "| Cumulative return | 10.00% | 5.00% | +5.00 pts |" in markdown
    assert "| Annualized volatility | 54.36% | 19.06% | +35.29 pts |" in markdown
    assert "| Maximum drawdown | -1.89% | -0.98% | -0.91 pts |" in markdown
    assert "## Moving-average trend" in markdown
    assert "| Latest close | 110.00 |" in markdown
    assert "| 3-day moving average | 106.67 |" in markdown
    assert "| 5-day moving average | 104.60 |" in markdown
    assert "| Close vs 5-day MA | +5.16% |" in markdown
    assert "Signal: **uptrend**" in markdown
    assert "## Risk notes" in markdown
    assert (
        "- Annualized volatility is elevated at 54.36%; "
        "review position sizing and scenario-test wider return swings."
    ) in markdown
    assert "- Cumulative return led MKT by 5.00 percentage points over the sample window." in markdown
    assert (
        "- Moving-average signal is uptrend; latest close is 5.16% above "
        "the 5-day moving average."
    ) in markdown
    assert "- Annualized volatility is estimated from the supplied periodic return series." not in markdown
    assert "Educational portfolio demo, not investment advice." in markdown


def test_render_research_brief_html_creates_a_shareable_document() -> None:
    summary = summarize_price_history(
        [
            PricePoint(date(2026, 1, 2), "NOVA", 100.0, 1_200_000),
            PricePoint(date(2026, 1, 3), "NOVA", 102.0, 1_300_000),
        ]
    )

    document = metrics.render_research_brief_html(summary)

    assert document.startswith("<!doctype html>")
    assert "<title>NOVA Financial Research Brief</title>" in document
    assert "<h1>NOVA Financial Research Brief</h1>" in document
    assert "<h2>Performance summary</h2>" in document
    assert "<table>" in document
    assert "Educational portfolio demo, not investment advice." in document
