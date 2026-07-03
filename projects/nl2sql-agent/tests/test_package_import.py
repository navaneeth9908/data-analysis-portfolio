"""Package import tests for runnable module commands."""

import importlib


def test_src_package_imports_without_optional_api_or_cli_modules() -> None:
    package = importlib.import_module("src")

    assert package.__version__ == "1.0.0"
    assert hasattr(package, "Config")
    assert hasattr(package, "SQLGenerator")
    assert "create_app" not in package.__all__
    assert "cli" not in package.__all__
