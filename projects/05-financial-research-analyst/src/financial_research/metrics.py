"""Financial research metric calculations for deterministic offline demos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import sqrt
from pathlib import Path
from statistics import mean, stdev
import csv


@dataclass(frozen=True)
class PricePoint:
    """One adjusted close observation for a ticker."""

    date: date
    ticker: str
    close: float
    volume: int


@dataclass(frozen=True)
class PerformanceSummary:
    """Return and risk metrics for a single ticker price series."""

    ticker: str
    observation_count: int
    start_date: date
    end_date: date
    start_close: float
    end_close: float
    cumulative_return_pct: float
    average_return_pct: float
    annualized_volatility_pct: float
    max_drawdown_pct: float


@dataclass(frozen=True)
class MovingAverageTrend:
    """Simple moving-average trend snapshot for a ticker price series."""

    ticker: str
    observation_count: int
    latest_date: date
    latest_close: float
    short_window: int
    long_window: int
    short_moving_average: float
    long_moving_average: float
    close_vs_long_ma_pct: float
    short_vs_long_ma_pct: float
    trend_label: str


def summarize_price_history(
    prices: list[PricePoint] | tuple[PricePoint, ...],
    *,
    periods_per_year: int = 252,
) -> PerformanceSummary:
    """Summarize a ticker's price history with common return/risk metrics."""
    if not prices:
        raise ValueError("at least one price point is required")

    ordered = sorted(prices, key=lambda point: point.date)
    ticker = ordered[0].ticker.strip().upper()
    if not ticker:
        raise ValueError("ticker is required")

    for point in ordered:
        if point.ticker.strip().upper() != ticker:
            raise ValueError("all price points must use the same ticker")
        if point.close <= 0:
            raise ValueError("close prices must be positive")
        if point.volume < 0:
            raise ValueError("volume cannot be negative")

    closes = [point.close for point in ordered]
    returns = [current / previous - 1 for previous, current in zip(closes, closes[1:])]

    cumulative_return_pct = (closes[-1] / closes[0] - 1) * 100
    average_return_pct = mean(returns) * 100 if returns else 0.0
    annualized_volatility_pct = (
        stdev(returns) * sqrt(periods_per_year) * 100 if len(returns) > 1 else 0.0
    )

    peak = closes[0]
    max_drawdown = 0.0
    for close in closes:
        peak = max(peak, close)
        max_drawdown = min(max_drawdown, close / peak - 1)

    return PerformanceSummary(
        ticker=ticker,
        observation_count=len(ordered),
        start_date=ordered[0].date,
        end_date=ordered[-1].date,
        start_close=closes[0],
        end_close=closes[-1],
        cumulative_return_pct=cumulative_return_pct,
        average_return_pct=average_return_pct,
        annualized_volatility_pct=annualized_volatility_pct,
        max_drawdown_pct=max_drawdown * 100,
    )


def summarize_moving_average_trend(
    prices: list[PricePoint] | tuple[PricePoint, ...],
    *,
    short_window: int = 3,
    long_window: int = 5,
) -> MovingAverageTrend:
    """Calculate a short-vs-long moving-average trend snapshot."""
    if short_window <= 0 or long_window <= 0:
        raise ValueError("moving-average windows must be positive")
    if short_window >= long_window:
        raise ValueError("short_window must be smaller than long_window")

    summary = summarize_price_history(prices)
    ordered = sorted(prices, key=lambda point: point.date)
    if len(ordered) < long_window:
        raise ValueError(f"at least {long_window} observations are required")

    closes = [point.close for point in ordered]
    short_moving_average = mean(closes[-short_window:])
    long_moving_average = mean(closes[-long_window:])
    latest_close = closes[-1]

    if short_moving_average > long_moving_average and latest_close >= short_moving_average:
        trend_label = "uptrend"
    elif short_moving_average < long_moving_average and latest_close <= short_moving_average:
        trend_label = "downtrend"
    else:
        trend_label = "mixed"

    return MovingAverageTrend(
        ticker=summary.ticker,
        observation_count=summary.observation_count,
        latest_date=summary.end_date,
        latest_close=latest_close,
        short_window=short_window,
        long_window=long_window,
        short_moving_average=short_moving_average,
        long_moving_average=long_moving_average,
        close_vs_long_ma_pct=(latest_close / long_moving_average - 1) * 100,
        short_vs_long_ma_pct=(short_moving_average / long_moving_average - 1) * 100,
        trend_label=trend_label,
    )


def load_price_history(path: str | Path, *, ticker: str | None = None) -> tuple[PricePoint, ...]:
    """Load adjusted close observations from a CSV file.

    Expected columns are ``date``, ``ticker``, ``close``, and ``volume``. When a
    ticker is provided, rows are filtered case-insensitively and returned in
    chronological order.
    """
    selected_ticker = ticker.strip().upper() if ticker else None
    price_points: list[PricePoint] = []

    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required_columns = {"date", "ticker", "close", "volume"}
        if not required_columns.issubset(reader.fieldnames or []):
            missing = ", ".join(sorted(required_columns - set(reader.fieldnames or [])))
            raise ValueError(f"price history is missing required columns: {missing}")

        for row in reader:
            row_ticker = row["ticker"].strip().upper()
            if selected_ticker and row_ticker != selected_ticker:
                continue
            price_points.append(
                PricePoint(
                    date=date.fromisoformat(row["date"].strip()),
                    ticker=row_ticker,
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                )
            )

    return tuple(sorted(price_points, key=lambda point: point.date))


def build_risk_notes(
    summary: PerformanceSummary,
    *,
    benchmark: PerformanceSummary | None = None,
    trend: MovingAverageTrend | None = None,
    volatility_warning_threshold_pct: float = 40.0,
    drawdown_warning_threshold_pct: float = -10.0,
) -> tuple[str, ...]:
    """Build deterministic analyst risk notes from return, benchmark, and trend metrics."""
    notes: list[str] = []

    if summary.annualized_volatility_pct >= volatility_warning_threshold_pct:
        notes.append(
            "- Annualized volatility is elevated at "
            f"{summary.annualized_volatility_pct:.2f}%; review position sizing and "
            "scenario-test wider return swings."
        )

    if summary.max_drawdown_pct <= drawdown_warning_threshold_pct:
        notes.append(
            f"- Maximum drawdown reached {summary.max_drawdown_pct:.2f}%, beyond the "
            f"{drawdown_warning_threshold_pct:.2f}% review threshold."
        )

    if benchmark is not None:
        cumulative_delta = summary.cumulative_return_pct - benchmark.cumulative_return_pct
        if cumulative_delta >= 0:
            notes.append(
                f"- Cumulative return led {benchmark.ticker} by "
                f"{cumulative_delta:.2f} percentage points over the sample window."
            )
        else:
            notes.append(
                f"- Cumulative return trailed {benchmark.ticker} by "
                f"{abs(cumulative_delta):.2f} percentage points over the sample window."
            )

    if trend is not None:
        if trend.trend_label == "uptrend":
            notes.append(
                "- Moving-average signal is uptrend; latest close is "
                f"{abs(trend.close_vs_long_ma_pct):.2f}% above the "
                f"{trend.long_window}-day moving average."
            )
        elif trend.trend_label == "downtrend":
            notes.append(
                "- Moving-average signal is downtrend; latest close is "
                f"{abs(trend.close_vs_long_ma_pct):.2f}% below the "
                f"{trend.long_window}-day moving average."
            )

    notes.append("- Educational portfolio demo, not investment advice.")
    return tuple(notes)


def render_research_brief(
    summary: PerformanceSummary,
    *,
    benchmark: PerformanceSummary | None = None,
    trend: MovingAverageTrend | None = None,
) -> str:
    """Render a concise Markdown performance brief for analyst review."""

    def pct(value: float) -> str:
        return f"{value:.2f}%"

    def pts(asset_value: float, benchmark_value: float) -> str:
        return f"{asset_value - benchmark_value:+.2f} pts"

    def signed_pct(value: float) -> str:
        return f"{value:+.2f}%"

    lines = [
        f"# {summary.ticker} Financial Research Brief",
        "",
        f"Coverage window: {summary.start_date.isoformat()} to {summary.end_date.isoformat()} "
        f"({summary.observation_count} observations).",
        "",
        "## Performance summary",
    ]

    if benchmark is not None:
        lines.extend(
            [
                "",
                f"Benchmark: {benchmark.ticker}",
                "",
                "| Metric | Asset | Benchmark | Difference |",
                "| --- | ---: | ---: | ---: |",
                "| Cumulative return | "
                f"{pct(summary.cumulative_return_pct)} | "
                f"{pct(benchmark.cumulative_return_pct)} | "
                f"{pts(summary.cumulative_return_pct, benchmark.cumulative_return_pct)} |",
                "| Average daily return | "
                f"{pct(summary.average_return_pct)} | "
                f"{pct(benchmark.average_return_pct)} | "
                f"{pts(summary.average_return_pct, benchmark.average_return_pct)} |",
                "| Annualized volatility | "
                f"{pct(summary.annualized_volatility_pct)} | "
                f"{pct(benchmark.annualized_volatility_pct)} | "
                f"{pts(summary.annualized_volatility_pct, benchmark.annualized_volatility_pct)} |",
                "| Maximum drawdown | "
                f"{pct(summary.max_drawdown_pct)} | "
                f"{pct(benchmark.max_drawdown_pct)} | "
                f"{pts(summary.max_drawdown_pct, benchmark.max_drawdown_pct)} |",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Cumulative return | {pct(summary.cumulative_return_pct)} |",
                f"| Average daily return | {pct(summary.average_return_pct)} |",
                f"| Annualized volatility | {pct(summary.annualized_volatility_pct)} |",
                f"| Maximum drawdown | {pct(summary.max_drawdown_pct)} |",
            ]
        )

    if trend is not None:
        lines.extend(
            [
                "",
                "## Moving-average trend",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Latest close | {trend.latest_close:.2f} |",
                f"| {trend.short_window}-day moving average | "
                f"{trend.short_moving_average:.2f} |",
                f"| {trend.long_window}-day moving average | "
                f"{trend.long_moving_average:.2f} |",
                f"| Close vs {trend.long_window}-day MA | "
                f"{signed_pct(trend.close_vs_long_ma_pct)} |",
                f"| {trend.short_window}-day vs {trend.long_window}-day MA | "
                f"{signed_pct(trend.short_vs_long_ma_pct)} |",
                "",
                f"Signal: **{trend.trend_label}**",
            ]
        )

    risk_notes = build_risk_notes(summary, benchmark=benchmark, trend=trend)
    lines.extend(["", "## Risk notes", *risk_notes, ""])
    return "\n".join(lines)
