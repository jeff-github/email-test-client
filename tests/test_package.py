"""Smoke check from outside the checkout to catch broken package discovery."""

import subprocess
import sys

import pytest


@pytest.mark.smoke
@pytest.mark.api
def test_installed_public_api_imports_outside_repository(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "from email_test_client import EmailClient, ImapConfig, "
            "EmailTimeoutError, extract_button_link",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
