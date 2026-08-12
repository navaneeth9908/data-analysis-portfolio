"""Verify that the portfolio keeps its documented project structure intact."""

from __future__ import annotations

import argparse
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
REQUIRED_PATHS = ("README.md", "pyproject.toml", "src", "tests")


def find_layout_issues(root: Path) -> list[str]:
    """Return required paths missing from the six documented project folders."""
    issues: list[str] = []
    for project in PROJECTS:
        project_directory = root / "projects" / project
        for required_path in REQUIRED_PATHS:
            if not (project_directory / required_path).exists():
                issues.append(f"{project}/{required_path}")
    return issues


def find_navigation_issues(root: Path) -> list[str]:
    """Return documented projects that are not linked from the root README."""
    root_readme = root / "README.md"
    if not root_readme.exists():
        return ["README.md"]

    navigation = root_readme.read_text(encoding="utf-8")
    return [
        f"README.md -> projects/{project}/"
        for project in PROJECTS
        if f"](projects/{project}/)" not in navigation
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check portfolio project structure and run each project test suite."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to inspect (defaults to this script's repository).",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate project structure without running test suites.",
    )
    arguments = parser.parse_args()

    issues = find_layout_issues(arguments.root)
    if issues:
        print("Portfolio layout is incomplete:")
        for issue in issues:
            print(f"- Missing: {issue}")
        return 1

    navigation_issues = find_navigation_issues(arguments.root)
    if navigation_issues:
        print("Portfolio navigation is incomplete:")
        for issue in navigation_issues:
            print(f"- Missing: {issue}")
        return 1

    print(f"Portfolio layout and navigation verified: {len(PROJECTS)} projects.")
    if arguments.check_only:
        return 0

    for project in PROJECTS:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q"],
            cwd=arguments.root / "projects" / project,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            print(f"[FAIL] {project}")
            if completed.stdout:
                print(completed.stdout.rstrip())
            if completed.stderr:
                print(completed.stderr.rstrip())
            return completed.returncode
        print(f"[PASS] {project}")

    print(f"Portfolio test suites passed: {len(PROJECTS)} projects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
