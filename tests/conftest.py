import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run real-server tests; missing/unhealthy GreenMail is a failure.",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-e2e"):
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(reason="Requires --run-e2e and GreenMail")
                )
