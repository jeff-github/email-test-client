import json
from pathlib import Path

import pytest


@pytest.fixture(params=["activation.eml", "site_invitation.eml"])
def supplied_sample(request):
    fixture_dir = Path(__file__).parent / "fixtures"
    expected = json.loads((fixture_dir / "expected_links.json").read_text())
    return (fixture_dir / request.param).read_bytes(), expected[request.param]


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
