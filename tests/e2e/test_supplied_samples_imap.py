"""Original EML bytes over IMAP, and original MIME bodies over SMTP/IMAP."""

import re
import smtplib
from dataclasses import replace
from uuid import uuid4

import pytest

from email_test_client import EmailClient

pytestmark = [pytest.mark.e2e, pytest.mark.integration, pytest.mark.regression]


def test_unmodified_sample_through_imap(server_config, inspector, supplied_sample):
    raw, expected = supplied_sample
    # A fresh folder isolates fixed sample addresses from previous test runs.
    # APPEND injects the exact supplied bytes, including the original To header.
    folder = f"sample-{uuid4().hex}"
    assert inspector.create(folder)[0] == "OK"
    try:
        assert inspector.append(folder, None, None, raw)[0] == "OK"
        with EmailClient(replace(server_config, mailbox=folder)) as client:
            assert (
                client.wait_for_link(
                    recipient=expected["recipient"],
                    button_text=expected["button_text"],
                    timeout=5,
                )
                == expected["url"]
            )
    finally:
        # Delete only this test's unique folder, never the shared INBOX.
        assert inspector.delete(folder)[0] == "OK"


def test_sample_body_through_smtp_shared_inbox(
    server_config, recipient, supplied_sample
):
    raw, expected = supplied_sample
    # Change only the To header for run isolation. Preserve invitation display
    # name, MIME boundaries, transfer encodings, HTML, inline image and URL bytes.
    routed, changes = re.subn(
        rb"(?m)^(To:[^\r\n]*)" + re.escape(expected["recipient"].encode()),
        lambda match: match.group(1) + recipient.encode(),
        raw,
        count=1,
    )
    assert changes == 1
    assert routed.split(b"\r\n\r\n", 1)[1] == raw.split(b"\r\n\r\n", 1)[1]
    with smtplib.SMTP(server_config.host, 33025, timeout=3) as smtp:
        assert not smtp.sendmail("noreply@cloud.example.com", [recipient], routed)
    with EmailClient(server_config) as client:
        assert (
            client.wait_for_link(
                recipient=recipient, button_text=expected["button_text"], timeout=5
            )
            == expected["url"]
        )
