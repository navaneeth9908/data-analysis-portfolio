"""CLI behavior tests for the financial research analyst demo."""

from __future__ import annotations


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
