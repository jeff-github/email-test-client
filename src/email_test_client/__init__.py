"""Email helpers for end-to-end tests."""

from email_test_client.client import (
    AuthenticationError,
    EmailClient,
    EmailTimeoutError,
    ImapConfig,
    MailboxError,
)
from email_test_client.extraction import (
    AmbiguousLinkError,
    LinkExtractionError,
    LinkNotFoundError,
    extract_button_link,
)

__all__ = [
    "AmbiguousLinkError",
    "AuthenticationError",
    "EmailClient",
    "EmailTimeoutError",
    "ImapConfig",
    "LinkExtractionError",
    "LinkNotFoundError",
    "MailboxError",
    "extract_button_link",
]
