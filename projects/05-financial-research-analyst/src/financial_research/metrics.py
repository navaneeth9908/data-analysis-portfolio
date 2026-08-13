"""Financial research metric calculations for deterministic offline demos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from math import sqrt
from pathlib import Path
import re
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
class BenchmarkSensitivity:
    """How an asset's aligned periodic returns move relative to a benchmark."""

    asset_ticker: str
    benchmark_ticker: str
    observation_count: int
    correlation: float
    beta: float


@dataclass(frozen=True)
class FundamentalSnapshot:
    """One point-in-time fundamentals input used for an equity research brief."""

    ticker: str
    as_of_date: date
    market_cap: float
    revenue_ttm: float
    net_income_ttm: float
    total_equity: float


@dataclass(frozen=True)
class FundamentalsSummary:
    """Valuation and profitability ratios calculated from a fundamentals snapshot."""

    ticker: str
    as_of_date: date
    market_cap: float
    revenue_ttm: float
    net_income_ttm: float
    total_equity: float
    price_to_sales_ratio: float
    net_margin_pct: float
    return_on_equity_pct: float


@dataclass(frozen=True)
class FundamentalsTrend:
    """Change in valuation and profitability ratios across fundamentals snapshots."""

    ticker: str
    observation_count: int
    start_date: date
    end_date: date
    start_price_to_sales_ratio: float
    end_price_to_sales_ratio: float
    price_to_sales_change: float
    start_net_margin_pct: float
    end_net_margin_pct: float
    net_margin_change_points: float
    start_return_on_equity_pct: float
    end_return_on_equity_pct: float
    return_on_equity_change_points: float


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
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")

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


def summarize_benchmark_sensitivity(
    asset_prices: list[PricePoint] | tuple[PricePoint, ...],
    benchmark_prices: list[PricePoint] | tuple[PricePoint, ...],
) -> BenchmarkSensitivity:
    """Calculate correlation and beta from dates shared by an asset and benchmark."""
    asset_summary = summarize_price_history(asset_prices)
    benchmark_summary = summarize_price_history(benchmark_prices)

    asset_by_date = {point.date: point.close for point in asset_prices}
    benchmark_by_date = {point.date: point.close for point in benchmark_prices}
    shared_dates = sorted(asset_by_date.keys() & benchmark_by_date.keys())
    if len(shared_dates) < 3:
        raise ValueError("at least three shared price dates are required")

    asset_closes = [asset_by_date[point_date] for point_date in shared_dates]
    benchmark_closes = [benchmark_by_date[point_date] for point_date in shared_dates]
    asset_returns = [
        current / previous - 1
        for previous, current in zip(asset_closes, asset_closes[1:])
    ]
    benchmark_returns = [
        current / previous - 1
        for previous, current in zip(benchmark_closes, benchmark_closes[1:])
    ]

    asset_average = mean(asset_returns)
    benchmark_average = mean(benchmark_returns)
    covariance = mean(
        (asset_return - asset_average) * (benchmark_return - benchmark_average)
        for asset_return, benchmark_return in zip(asset_returns, benchmark_returns)
    )
    asset_variance = mean((item - asset_average) ** 2 for item in asset_returns)
    benchmark_variance = mean((item - benchmark_average) ** 2 for item in benchmark_returns)
    if asset_variance == 0 or benchmark_variance == 0:
        raise ValueError("aligned periodic returns must vary for correlation and beta")

    return BenchmarkSensitivity(
        asset_ticker=asset_summary.ticker,
        benchmark_ticker=benchmark_summary.ticker,
        observation_count=len(shared_dates),
        correlation=covariance / sqrt(asset_variance * benchmark_variance),
        beta=covariance / benchmark_variance,
    )


def summarize_fundamentals(snapshot: FundamentalSnapshot) -> FundamentalsSummary:
    """Calculate transparent valuation and profitability ratios from TTM inputs."""
    ticker = snapshot.ticker.strip().upper()
    if not ticker:
        raise ValueError("ticker is required")
    if snapshot.market_cap <= 0:
        raise ValueError("market capitalization must be positive")
    if snapshot.revenue_ttm <= 0:
        raise ValueError("TTM revenue must be positive")
    if snapshot.total_equity <= 0:
        raise ValueError("total equity must be positive")

    return FundamentalsSummary(
        ticker=ticker,
        as_of_date=snapshot.as_of_date,
        market_cap=snapshot.market_cap,
        revenue_ttm=snapshot.revenue_ttm,
        net_income_ttm=snapshot.net_income_ttm,
        total_equity=snapshot.total_equity,
        price_to_sales_ratio=snapshot.market_cap / snapshot.revenue_ttm,
        net_margin_pct=(snapshot.net_income_ttm / snapshot.revenue_ttm) * 100,
        return_on_equity_pct=(snapshot.net_income_ttm / snapshot.total_equity) * 100,
    )


def summarize_fundamentals_trend(
    snapshots: list[FundamentalSnapshot] | tuple[FundamentalSnapshot, ...],
) -> FundamentalsTrend:
    """Compare the oldest and newest TTM fundamentals snapshots for one ticker."""
    if len(snapshots) < 2:
        raise ValueError("at least two fundamentals snapshots are required")

    summaries = tuple(
        summarize_fundamentals(snapshot)
        for snapshot in sorted(snapshots, key=lambda item: item.as_of_date)
    )
    ticker = summaries[0].ticker
    if any(summary.ticker != ticker for summary in summaries[1:]):
        raise ValueError("all fundamentals snapshots must use the same ticker")

    start, end = summaries[0], summaries[-1]
    return FundamentalsTrend(
        ticker=ticker,
        observation_count=len(summaries),
        start_date=start.as_of_date,
        end_date=end.as_of_date,
        start_price_to_sales_ratio=start.price_to_sales_ratio,
        end_price_to_sales_ratio=end.price_to_sales_ratio,
        price_to_sales_change=end.price_to_sales_ratio - start.price_to_sales_ratio,
        start_net_margin_pct=start.net_margin_pct,
        end_net_margin_pct=end.net_margin_pct,
        net_margin_change_points=end.net_margin_pct - start.net_margin_pct,
        start_return_on_equity_pct=start.return_on_equity_pct,
        end_return_on_equity_pct=end.return_on_equity_pct,
        return_on_equity_change_points=end.return_on_equity_pct - start.return_on_equity_pct,
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
    observed_dates: set[tuple[str, date]] = set()

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
            row_date = date.fromisoformat(row["date"].strip())
            date_key = (row_ticker, row_date)
            if date_key in observed_dates:
                raise ValueError(
                    f"duplicate price date for {row_ticker}: {row_date.isoformat()}"
                )
            observed_dates.add(date_key)
            price_points.append(
                PricePoint(
                    date=row_date,
                    ticker=row_ticker,
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                )
            )

    return tuple(sorted(price_points, key=lambda point: point.date))


def load_fundamental_history(path: str | Path, *, ticker: str) -> tuple[FundamentalSnapshot, ...]:
    """Load chronological point-in-time fundamentals snapshots for one ticker."""
    selected_ticker = ticker.strip().upper()
    if not selected_ticker:
        raise ValueError("ticker is required")

    required_columns = {
        "as_of_date",
        "ticker",
        "market_cap",
        "revenue_ttm",
        "net_income_ttm",
        "total_equity",
    }
    snapshots: list[FundamentalSnapshot] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not required_columns.issubset(reader.fieldnames or []):
            missing = ", ".join(sorted(required_columns - set(reader.fieldnames or [])))
            raise ValueError(f"fundamentals data is missing required columns: {missing}")

        for row in reader:
            if row["ticker"].strip().upper() != selected_ticker:
                continue
            snapshots.append(
                FundamentalSnapshot(
                    ticker=selected_ticker,
                    as_of_date=date.fromisoformat(row["as_of_date"].strip()),
                    market_cap=float(row["market_cap"]),
                    revenue_ttm=float(row["revenue_ttm"]),
                    net_income_ttm=float(row["net_income_ttm"]),
                    total_equity=float(row["total_equity"]),
                )
            )

    if not snapshots:
        raise ValueError(f"no fundamentals rows found for ticker: {selected_ticker}")
    return tuple(sorted(snapshots, key=lambda snapshot: snapshot.as_of_date))


def load_fundamental_snapshot(path: str | Path, *, ticker: str) -> FundamentalSnapshot:
    """Load the latest point-in-time fundamentals row for a ticker from a CSV file."""
    return load_fundamental_history(path, ticker=ticker)[-1]


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

        if summary.max_drawdown_pct < benchmark.max_drawdown_pct:
            drawdown_gap = benchmark.max_drawdown_pct - summary.max_drawdown_pct
            notes.append(
                f"- Drawdown looks asset-specific: {summary.ticker} fell "
                f"{drawdown_gap:.2f} percentage points more than {benchmark.ticker} "
                "from peak to trough."
            )
        elif benchmark.max_drawdown_pct < 0:
            notes.append(
                f"- Drawdown looks market-wide: {benchmark.ticker} fell "
                f"{abs(benchmark.max_drawdown_pct):.2f}% versus {summary.ticker}'s "
                f"{abs(summary.max_drawdown_pct):.2f}% from peak to trough."
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
    benchmark_sensitivity: BenchmarkSensitivity | None = None,
    trend: MovingAverageTrend | None = None,
    fundamentals: FundamentalsSummary | None = None,
    fundamentals_trend: FundamentalsTrend | None = None,
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

    if benchmark_sensitivity is not None:
        lines.extend(
            [
                "",
                "## Benchmark sensitivity",
                "",
                f"Aligned observations: {benchmark_sensitivity.observation_count}.",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Return correlation | {benchmark_sensitivity.correlation:.2f} |",
                f"| Beta vs {benchmark_sensitivity.benchmark_ticker} | "
                f"{benchmark_sensitivity.beta:.2f} |",
            ]
        )

    if fundamentals is not None:
        if fundamentals.ticker != summary.ticker:
            raise ValueError("fundamentals ticker must match the performance summary ticker")
        lines.extend(
            [
                "",
                "## Fundamentals snapshot",
                "",
                f"As of: {fundamentals.as_of_date.isoformat()} (TTM inputs)",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Price-to-sales | {fundamentals.price_to_sales_ratio:.2f}x |",
                f"| Net margin | {fundamentals.net_margin_pct:.2f}% |",
                f"| Return on equity | {fundamentals.return_on_equity_pct:.2f}% |",
            ]
        )

    if fundamentals_trend is not None:
        if fundamentals_trend.ticker != summary.ticker:
            raise ValueError("fundamentals trend ticker must match the performance summary ticker")
        lines.extend(
            [
                "",
                "## Fundamentals trend",
                "",
                "Coverage: "
                f"{fundamentals_trend.start_date.isoformat()} to "
                f"{fundamentals_trend.end_date.isoformat()} "
                f"({fundamentals_trend.observation_count} observations).",
                "",
                "| Metric | Start | Latest | Change |",
                "| --- | ---: | ---: | ---: |",
                "| Price-to-sales | "
                f"{fundamentals_trend.start_price_to_sales_ratio:.2f}x | "
                f"{fundamentals_trend.end_price_to_sales_ratio:.2f}x | "
                f"{fundamentals_trend.price_to_sales_change:+.2f}x |",
                "| Net margin | "
                f"{fundamentals_trend.start_net_margin_pct:.2f}% | "
                f"{fundamentals_trend.end_net_margin_pct:.2f}% | "
                f"{fundamentals_trend.net_margin_change_points:+.2f} pts |",
                "| Return on equity | "
                f"{fundamentals_trend.start_return_on_equity_pct:.2f}% | "
                f"{fundamentals_trend.end_return_on_equity_pct:.2f}% | "
                f"{fundamentals_trend.return_on_equity_change_points:+.2f} pts |",
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


def render_research_brief_html(
    summary: PerformanceSummary,
    *,
    benchmark: PerformanceSummary | None = None,
    benchmark_sensitivity: BenchmarkSensitivity | None = None,
    trend: MovingAverageTrend | None = None,
    fundamentals: FundamentalsSummary | None = None,
    fundamentals_trend: FundamentalsTrend | None = None,
) -> str:
    """Render the Markdown research brief as a standalone, shareable HTML document."""
    markdown = render_research_brief(
        summary,
        benchmark=benchmark,
        benchmark_sensitivity=benchmark_sensitivity,
        trend=trend,
        fundamentals=fundamentals,
        fundamentals_trend=fundamentals_trend,
    )
    body = _render_markdown_as_html(markdown)
    title = f"{summary.ticker} Financial Research Brief"
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{escape(title)}</title>",
            "  <style>",
            "    body { color: #172033; font-family: Arial, sans-serif; line-height: 1.5; margin: 0 auto; max-width: 900px; padding: 32px 20px; }",
            "    h1, h2 { color: #102a43; }",
            "    h2 { border-bottom: 1px solid #d9e2ec; margin-top: 32px; padding-bottom: 6px; }",
            "    table { border-collapse: collapse; margin: 16px 0; width: 100%; }",
            "    th, td { border: 1px solid #bcccdc; padding: 8px; text-align: left; }",
            "    th { background: #f0f4f8; }",
            "    td:not(:first-child), th:not(:first-child) { text-align: right; }",
            "    .disclaimer { color: #52606d; font-size: 0.9rem; }",
            "  </style>",
            "</head>",
            "<body>",
            body,
            "</body>",
            "</html>",
            "",
        ]
    )


def _render_markdown_as_html(markdown: str) -> str:
    """Convert this module's deterministic Markdown report structure to safe HTML."""
    html_lines: list[str] = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line:
            index += 1
            continue
        if line.startswith("# "):
            html_lines.append(f"<h1>{_format_html_text(line[2:])}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{_format_html_text(line[3:])}</h2>")
        elif line.startswith("| "):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            html_lines.extend(_render_markdown_table(table_lines))
            continue
        elif line.startswith("- "):
            list_items: list[str] = []
            while index < len(lines) and lines[index].startswith("- "):
                list_items.append(lines[index][2:])
                index += 1
            list_class = ' class="disclaimer"' if list_items == ["Educational portfolio demo, not investment advice."] else ""
            html_lines.append(f"<ul{list_class}>")
            html_lines.extend(f"  <li>{_format_html_text(item)}</li>" for item in list_items)
            html_lines.append("</ul>")
            continue
        else:
            html_lines.append(f"<p>{_format_html_text(line)}</p>")
        index += 1
    return "\n".join(html_lines)


def _render_markdown_table(lines: list[str]) -> list[str]:
    """Render one Markdown pipe table while omitting its delimiter row."""
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines
    ]
    header, *remaining_rows = rows
    data_rows = remaining_rows[1:]
    rendered = ["<table>", "  <thead>", "    <tr>"]
    rendered.extend(f"      <th>{_format_html_text(cell)}</th>" for cell in header)
    rendered.extend(["    </tr>", "  </thead>", "  <tbody>"])
    for row in data_rows:
        rendered.append("    <tr>")
        rendered.extend(f"      <td>{_format_html_text(cell)}</td>" for cell in row)
        rendered.append("    </tr>")
    rendered.extend(["  </tbody>", "</table>"])
    return rendered


def _format_html_text(value: str) -> str:
    """Escape report text and preserve the renderer's bold emphasis."""
    escaped = escape(value)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
