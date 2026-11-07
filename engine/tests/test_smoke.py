from localflow_engine import cli


def test_package_imports() -> None:
    assert callable(cli.main)
