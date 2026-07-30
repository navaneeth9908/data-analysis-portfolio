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


def test_package_exports_moving_average_trend_and_risk_note_api() -> None:
    from financial_research import (
        MovingAverageTrend,
        build_risk_notes,
        summarize_moving_average_trend,
    )

    assert MovingAverageTrend is metrics.MovingAverageTrend
    assert summarize_moving_average_trend is metrics.summarize_moving_average_trend
    assert build_risk_notes is metrics.build_risk_notes


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
