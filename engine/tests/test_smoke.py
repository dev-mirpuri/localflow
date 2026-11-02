import localflow_engine


def test_package_imports() -> None:
    assert callable(localflow_engine.main)
