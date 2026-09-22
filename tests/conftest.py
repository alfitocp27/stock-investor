import pytest


# pytest config: register the `network` marker (used by tests/data/test_fetcher.py)
# so `-m "not network"` works and no unknown-mark warnings are emitted.
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "network: marks tests that hit live external services (e.g. Yahoo Finance). "
        "Skippable with: pytest -m 'not network'",
    )
