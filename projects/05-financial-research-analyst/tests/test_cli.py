"""CLI behavior tests for the financial research analyst demo."""

from __future__ import annotations


def test_cli_includes_optional_fundamentals_snapshot(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    price_file.write_text(
        "date,ticker,close,volume\n"
        "2026-01-02,NOVA,100,1200000\n"
        "2026-01-03,NOVA,102,1300000\n"
        "2026-01-04,NOVA,101,1100000\n"
        "2026-01-05,NOVA,106,1500000\n"
        "2026-01-06,NOVA,104,1400000\n"
        "2026-01-07,NOVA,110,1800000\n",
        encoding="utf-8",
    )
    fundamentals_file = tmp_path / "fundamentals.csv"
    fundamentals_file.write_text(
        "as_of_date,ticker,market_cap,revenue_ttm,net_income_ttm,total_equity\n"
        "2026-01-07,NOVA,500000000,100000000,15000000,75000000\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "brief.md"

    from financial_research.cli import main

    exit_code = main(
        [
            str(price_file),
            "--ticker",
            "NOVA",
            "--fundamentals-file",
            str(fundamentals_file),
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0
    markdown = output_file.read_text(encoding="utf-8")
    assert "## Fundamentals snapshot" in markdown
    assert "| Price-to-sales | 5.00x |" in markdown


def test_cli_includes_fundamentals_trend_when_multiple_snapshots_are_available(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    price_file.write_text(
        "date,ticker,close,volume\n"
        "2026-01-02,NOVA,100,1200000\n"
        "2026-01-03,NOVA,102,1300000\n"
        "2026-01-04,NOVA,101,1100000\n"
        "2026-01-05,NOVA,106,1500000\n"
        "2026-01-06,NOVA,104,1400000\n"
        "2026-01-07,NOVA,110,1800000\n",
        encoding="utf-8",
    )
    fundamentals_file = tmp_path / "fundamentals.csv"
    fundamentals_file.write_text(
        "as_of_date,ticker,market_cap,revenue_ttm,net_income_ttm,total_equity\n"
        "2025-10-07,NOVA,400000000,90000000,12000000,70000000\n"
        "2026-01-07,NOVA,500000000,100000000,15000000,75000000\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "brief.md"

    from financial_research.cli import main

    exit_code = main(
        [
            str(price_file),
            "--ticker",
            "NOVA",
            "--fundamentals-file",
            str(fundamentals_file),
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0
    markdown = output_file.read_text(encoding="utf-8")
    assert "## Fundamentals trend" in markdown
    assert "| Price-to-sales | 4.44x | 5.00x | +0.56x |" in markdown


def test_cli_writes_research_brief_from_price_history(tmp_path) -> None:
    price_file = tmp_path / "sample_prices.csv"
    price_file.write_text(
        "date,ticker,close,volume\n"
        "2026-01-02,NOVA,100,1200000\n"
        "2026-01-03,NOVA,102,1300000\n"
        "2026-01-04,NOVA,101,1100000\n"
        "2026-01-05,NOVA,106,1500000\n"
        "2026-01-06,NOVA,104,1400000\n"
        "2026-01-07,NOVA,110,1800000\n"
        "2026-01-02,MKT,100,4200000\n"
        "2026-01-03,MKT,101,4300000\n"
        "2026-01-04,MKT,102,4100000\n"
        "2026-01-05,MKT,101,4500000\n"
        "2026-01-06,MKT,103,4400000\n"
        "2026-01-07,MKT,105,4800000\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "brief.md"

    from financial_research.cli import main

    exit_code = main(
        [
            str(price_file),
            "--ticker",
            "NOVA",
            "--benchmark",
            "MKT",
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0
    markdown = output_file.read_text(encoding="utf-8")
    assert markdown.startswith("# NOVA Financial Research Brief")
    assert "Benchmark: MKT" in markdown
    assert "| Cumulative return | 10.00% | 5.00% | +5.00 pts |" in markdown
    assert "## Moving-average trend" in markdown
    assert "| 3-day moving average | 106.67 |" in markdown
    assert "Signal: **uptrend**" in markdown


def test_cli_includes_benchmark_sensitivity_when_benchmark_is_requested(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    price_file.write_text(
        "date,ticker,close,volume\n"
        "2026-01-02,NOVA,100,1200000\n"
        "2026-01-03,NOVA,102,1300000\n"
        "2026-01-04,NOVA,101,1100000\n"
        "2026-01-05,NOVA,106,1500000\n"
        "2026-01-06,NOVA,104,1400000\n"
        "2026-01-07,NOVA,110,1800000\n"
        "2026-01-02,MKT,100,4200000\n"
        "2026-01-03,MKT,101,4300000\n"
        "2026-01-04,MKT,102,4100000\n"
        "2026-01-05,MKT,101,4500000\n"
        "2026-01-06,MKT,103,4400000\n"
        "2026-01-07,MKT,105,4800000\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "brief.md"

    from financial_research.cli import main

    exit_code = main(
        [
            str(price_file),
            "--ticker",
            "NOVA",
            "--benchmark",
            "MKT",
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0
    markdown = output_file.read_text(encoding="utf-8")
    assert "## Benchmark sensitivity" in markdown
    assert "Aligned observations: 6." in markdown
    assert "| Return correlation |" in markdown
    assert "| Beta vs MKT |" in markdown


def test_cli_uses_requested_periods_per_year_for_annualized_volatility(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    price_file.write_text(
        "date,ticker,close,volume\n"
        "2026-01-02,NOVA,100,1200000\n"
        "2026-01-03,NOVA,102,1300000\n"
        "2026-01-04,NOVA,101,1100000\n"
        "2026-01-05,NOVA,106,1500000\n"
        "2026-01-06,NOVA,104,1400000\n"
        "2026-01-07,NOVA,110,1800000\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "brief.md"

    from financial_research.cli import main
    from financial_research.metrics import load_price_history, summarize_price_history

    expected_summary = summarize_price_history(
        load_price_history(price_file, ticker="NOVA"),
        periods_per_year=12,
    )
    exit_code = main(
        [
            str(price_file),
            "--ticker",
            "NOVA",
            "--periods-per-year",
            "12",
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0
    markdown = output_file.read_text(encoding="utf-8")
    assert (
        f"| Annualized volatility | {expected_summary.annualized_volatility_pct:.2f}% |"
        in markdown
    )


def test_cli_applies_periods_per_year_to_the_benchmark_comparison(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    price_file.write_text(
        "date,ticker,close,volume\n"
        "2026-01-02,NOVA,100,1200000\n"
        "2026-01-03,NOVA,102,1300000\n"
        "2026-01-04,NOVA,101,1100000\n"
        "2026-01-05,NOVA,106,1500000\n"
        "2026-01-06,NOVA,104,1400000\n"
        "2026-01-07,NOVA,110,1800000\n"
        "2026-01-02,MKT,100,4200000\n"
        "2026-01-03,MKT,101,4300000\n"
        "2026-01-04,MKT,102,4100000\n"
        "2026-01-05,MKT,101,4500000\n"
        "2026-01-06,MKT,103,4400000\n"
        "2026-01-07,MKT,105,4800000\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "brief.md"

    from financial_research.cli import main
    from financial_research.metrics import load_price_history, summarize_price_history

    expected_asset = summarize_price_history(
        load_price_history(price_file, ticker="NOVA"),
        periods_per_year=12,
    )
    expected_benchmark = summarize_price_history(
        load_price_history(price_file, ticker="MKT"),
        periods_per_year=12,
    )
    exit_code = main(
        [
            str(price_file),
            "--ticker",
            "NOVA",
            "--benchmark",
            "MKT",
            "--periods-per-year",
            "12",
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0
    markdown = output_file.read_text(encoding="utf-8")
    assert (
        "| Annualized volatility | "
        f"{expected_asset.annualized_volatility_pct:.2f}% | "
        f"{expected_benchmark.annualized_volatility_pct:.2f}% | "
        f"{expected_asset.annualized_volatility_pct - expected_benchmark.annualized_volatility_pct:+.2f} pts |"
        in markdown
    )


def test_cli_writes_a_self_contained_html_research_brief(tmp_path) -> None:
    price_file = tmp_path / "prices.csv"
    price_file.write_text(
        "date,ticker,close,volume\n"
        "2026-01-02,NOVA,100,1200000\n"
        "2026-01-03,NOVA,102,1300000\n"
        "2026-01-04,NOVA,101,1100000\n"
        "2026-01-05,NOVA,106,1500000\n"
        "2026-01-06,NOVA,104,1400000\n"
        "2026-01-07,NOVA,110,1800000\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "brief.html"

    from financial_research.cli import main

    exit_code = main(
        [
            str(price_file),
            "--ticker",
            "NOVA",
            "--format",
            "html",
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0
    document = output_file.read_text(encoding="utf-8")
    assert document.startswith("<!doctype html>")
    assert "<title>NOVA Financial Research Brief</title>" in document
    assert "<h2>Moving-average trend</h2>" in document
