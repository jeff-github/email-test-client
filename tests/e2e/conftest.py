import imaplib
import smtplib
import time
from email.message import EmailMessage
from uuid import uuid4

import pytest

from email_test_client import ImapConfig


@pytest.fixture(scope="session")
def server_config():
    """Dedicated local GreenMail; never reads personal mailbox credentials."""
    config = ImapConfig(
        host="127.0.0.1",
        port=33143,
        username="qa",
        password="test-password",
        security="plain",
        network_timeout=3,
    )
    deadline = time.monotonic() + 30
    while True:
        try:
            with smtplib.SMTP(config.host, 33025, timeout=2) as smtp:
                smtp.noop()
            with imaplib.IMAP4(config.host, config.port, timeout=2) as imap:
                imap.login(config.username, config.password)
            return config
        except (OSError, imaplib.IMAP4.error, smtplib.SMTPException):
            if time.monotonic() >= deadline:
                pytest.fail("GreenMail unavailable. Run: docker compose up -d")
            time.sleep(0.25)


@pytest.fixture
def recipient():
    return f"qa+{uuid4().hex}@example.com"


@pytest.fixture
def send_mail(server_config):
    def send(recipient, link, label="Activate account", cte="quoted-printable"):
        message = EmailMessage()
        message["From"] = "application@example.com"
        message["To"] = recipient
        message["Subject"] = "Synthetic end-to-end test message"
        message.set_content("Please use the button in the HTML message.")
        message.add_alternative(
            '<a href="https://example.com/help">Help</a>'
            f'<a href="{link}"><span>{label}</span></a>',
            subtype="html",
            cte=cte,
        )
        with smtplib.SMTP(server_config.host, 33025, timeout=3) as smtp:
            # The actual SMTP envelope uses the plus-address too. GreenMail's
            # configured subaddress handling routes all qa+detail to qa's mailbox.
            refused = smtp.send_message(message)
            assert not refused

    return send


@pytest.fixture
def inspector(server_config):
    """Independent protocol observer; does not use the library under test."""
    with imaplib.IMAP4(server_config.host, server_config.port, timeout=3) as imap:
        imap.login(server_config.username, server_config.password)
        yield imap
