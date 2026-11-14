"""Regression checks against the exact EML bytes supplied in homework.zip."""

import pytest

from email_test_client import extract_button_link

pytestmark = [pytest.mark.unit, pytest.mark.regression]


def test_original_sample_returns_exact_button_url(supplied_sample):
    raw, expected = supplied_sample
    assert (
        extract_button_link(raw, button_text=expected["button_text"]) == expected["url"]
    )
