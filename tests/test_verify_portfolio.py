"""Behavior tests for the repository-wide portfolio verifier."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


PROJECTS = (
    "01-auto-eda-analyst",
    "nl2sql-agent",
    "03-report-qa-agent",
    "04-competitive-intelligence-pipeline",
    "05-financial-research-analyst",
    "06-research-briefing-generator",
)


def _create_complete_project_layout(root: Path, *, include_passing_tests: bool = False) -> None:
    navigation = "\n".join(
        f"- [Project](projects/{project}/)" for project in PROJECTS
    )
    (root / "README.md").write_text(f"# Portfolio\n\n{navigation}\n", encoding="utf-8")

    for project in PROJECTS:
        project_directory = root / "projects" / project
        (project_directory / "src").mkdir(parents=True)
        (project_directory / "tests").mkdir()
        (project_directory / "README.md").write_text("# Demo\n", encoding="utf-8")
        (project_directory / "pyproject.toml").write_text(
            "[project]\nname = 'demo'\nversion = '0.1.0'\n",
            encoding="utf-8",
        )
        if include_passing_tests:
            (project_directory / "tests" / "test_smoke.py").write_text(
                "def test_smoke() -> None:\n    assert True\n",
                encoding="utf-8",
            )


def test_check_only_confirms_a_complete_six_project_layout(tmp_path: Path) -> None:
    _create_complete_project_layout(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_portfolio.py",
            "--root",
            str(tmp_path),
            "--check-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "Portfolio layout and navigation verified: 6 projects.\n"


def test_check_only_reports_project_missing_from_root_navigation(tmp_path: Path) -> None:
    _create_complete_project_layout(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "- [Project](projects/06-research-briefing-generator/)\n", ""
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_portfolio.py",
            "--root",
            str(tmp_path),
            "--check-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == (
        "Portfolio navigation is incomplete:\n"
        "- Missing: README.md -> projects/06-research-briefing-generator/\n"
    )


def test_check_only_reports_a_missing_root_readme(tmp_path: Path) -> None:
    _create_complete_project_layout(tmp_path)
    (tmp_path / "README.md").unlink()

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_portfolio.py",
            "--root",
            str(tmp_path),
            "--check-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == (
        "Portfolio navigation is incomplete:\n- Missing: README.md\n"
    )


def test_check_only_reports_a_missing_required_project_file(tmp_path: Path) -> None:
    _create_complete_project_layout(tmp_path)
    (tmp_path / "projects" / "05-financial-research-analyst" / "pyproject.toml").unlink()

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_portfolio.py",
            "--root",
            str(tmp_path),
            "--check-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == (
        "Portfolio layout is incomplete:\n"
        "- Missing: 05-financial-research-analyst/pyproject.toml\n"
    )


def test_default_run_executes_every_project_test_suite(tmp_path: Path) -> None:
    _create_complete_project_layout(tmp_path, include_passing_tests=True)

    result = subprocess.run(
        [sys.executable, "scripts/verify_portfolio.py", "--root", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    for project in PROJECTS:
        assert f"[PASS] {project}" in result.stdout
    assert result.stdout.endswith("Portfolio test suites passed: 6 projects.\n")


def test_project_filter_runs_only_the_selected_project_suite(tmp_path: Path) -> None:
    _create_complete_project_layout(tmp_path, include_passing_tests=True)
    failing_project = tmp_path / "projects" / "06-research-briefing-generator"
    (failing_project / "tests" / "test_smoke.py").write_text(
        "def test_smoke() -> None:\n    assert False\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_portfolio.py",
            "--root",
            str(tmp_path),
            "--project",
            "01-auto-eda-analyst",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "[PASS] 01-auto-eda-analyst" in result.stdout
    assert "06-research-briefing-generator" not in result.stdout
    assert result.stdout.endswith("Portfolio test suites passed: 1 project.\n")
