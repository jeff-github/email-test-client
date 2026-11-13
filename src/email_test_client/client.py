"""Synchronous, non-destructive IMAP polling for uniquely addressed test runs."""

import imaplib
import math
import re
import ssl
import time
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from typing import Literal

from email_test_client.extraction import (
    AmbiguousLinkError,
    LinkNotFoundError,
    extract_button_link,
)


class MailboxError(RuntimeError):
    """Connection, protocol, or mailbox operation failed."""


class AuthenticationError(MailboxError):
    """The server rejected LOGIN credentials."""


class EmailTimeoutError(TimeoutError):
    """No matching link was found within the wait budget."""


def _positive(value: float, name: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than zero.")


def _quote(value: str) -> str:
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("IMAP arguments must not contain control characters.")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


@dataclass(frozen=True)
class ImapConfig:
    host: str
    username: str
    password: str = field(repr=False)
    port: int = 993
    mailbox: str = "INBOX"
    security: Literal["ssl", "starttls", "plain"] = "ssl"
    network_timeout: float = 10.0

    def __post_init__(self) -> None:
        if self.security not in {"ssl", "starttls", "plain"}:
            raise ValueError("security must be ssl, starttls, or plain.")
        if not self.host or not self.username or not self.mailbox:
            raise ValueError("host, username, and mailbox must not be empty.")
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535.")
        _positive(self.network_timeout, "network_timeout")
        _quote(self.mailbox)


def _recipient_key(address: str) -> tuple[str, str]:
    # Deliberately support the assignment's ASCII addr-spec, not display names
    # or quoted local parts. Keep local-part case; DNS domains ignore case.
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+", address):
        raise ValueError("recipient must be a bare ASCII email address.")
    local, domain = address.rsplit("@", 1)
    return local, domain.lower()


def _matches_recipient(raw: bytes, recipient: tuple[str, str]) -> bool:
    message = BytesParser(policy=policy.default).parsebytes(raw, headersonly=True)
    for header in message.get_all("To", []):
        if header.defects:
            continue
        for address in header.addresses:
            if (address.username, address.domain.lower()) == recipient:
                return True
    return False


class EmailClient:
    """One connection per context/caller; do not share across threads.

    Connection setup has its own network timeout. ``wait_for_link`` starts its
    budget after setup and applies remaining time to socket operations. Socket
    timeouts bound inactivity, not an absolute wall-clock limit for a response
    that streams indefinitely; no cancellation worker is used.
    """

    def __init__(self, config: ImapConfig):
        self.config = config
        self._connection: imaplib.IMAP4 | None = None

    def __enter__(self):
        if self._connection is not None:
            raise RuntimeError("EmailClient is already connected.")
        config = self.config
        try:
            if config.security == "ssl":
                self._connection = imaplib.IMAP4_SSL(
                    config.host,
                    config.port,
                    timeout=config.network_timeout,
                    ssl_context=ssl.create_default_context(),
                )
            else:
                self._connection = imaplib.IMAP4(
                    config.host, config.port, timeout=config.network_timeout
                )
                if config.security == "starttls":
                    status, _ = self._connection.starttls(
                        ssl_context=ssl.create_default_context()
                    )
                    if status != "OK":
                        raise MailboxError("IMAP STARTTLS failed.")
            try:
                status, _ = self._connection.login(config.username, config.password)
                if status != "OK":
                    raise AuthenticationError("IMAP authentication failed.")
            except imaplib.IMAP4.abort:
                raise MailboxError("IMAP disconnected during authentication.") from None
            except imaplib.IMAP4.error:
                raise AuthenticationError("IMAP authentication failed.") from None
        except (OSError, imaplib.IMAP4.error):
            self.close()
            raise MailboxError("Could not establish the IMAP connection.") from None
        except MailboxError:
            self.close()
            raise
        return self

    def close(self) -> None:
        connection, self._connection = self._connection, None
        if connection is not None:
            # Close the socket directly: no CLOSE/EXPUNGE and no blocking LOGOUT.
            try:
                connection.shutdown()
            except OSError:
                pass

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise EmailTimeoutError("Timed out waiting for the requested email link.")
        return remaining

    def _call(self, deadline: float, method, *args, **kwargs):
        remaining = self._remaining(deadline)
        connection = self._connection
        assert connection is not None
        connection.sock.settimeout(min(self.config.network_timeout, remaining))
        try:
            status, data = method(*args, **kwargs)
        except (OSError, imaplib.IMAP4.error):
            self.close()  # A failed command may leave protocol state unusable.
            if time.monotonic() >= deadline:
                raise EmailTimeoutError(
                    "Timed out waiting for the requested email link."
                ) from None
            raise MailboxError("IMAP operation failed.") from None
        self._remaining(deadline)
        if status != "OK":
            raise MailboxError("IMAP server rejected an operation.")
        return data

    def wait_for_link(
        self,
        *,
        recipient: str,
        button_text: str,
        timeout: float = 30.0,
        poll_interval: float = 1.0,
    ) -> str:
        """Search existing and arriving mail for an exact To recipient and label.

        Messages lacking the label are skipped. Invalid/ambiguous matching links
        fail immediately. Multiple messages in one search may agree on a URL;
        different URLs are ambiguous. Mail arriving after a successful search is
        outside that result's snapshot. Use a fresh address per independent run.
        """
        recipient_key = _recipient_key(recipient)
        if not button_text.strip():
            raise ValueError("button_text must not be empty or whitespace-only.")
        _positive(timeout, "timeout")
        _positive(poll_interval, "poll_interval")
        connection = self._connection
        if connection is None:
            raise RuntimeError("Use EmailClient inside a with block.")
        deadline = time.monotonic() + timeout
        seen: set[bytes] = set()
        validity = None
        while True:
            # Re-select read-only to refresh the view and detect UID namespace
            # changes before trusting the per-wait cache. Never use a UID cursor.
            self._call(
                deadline, connection.select, _quote(self.config.mailbox), readonly=True
            )
            _, values = connection.response("UIDVALIDITY")
            current = tuple(values or [])
            if not current or any(value is None for value in current):
                raise MailboxError("Server did not provide UIDVALIDITY.")
            if current != validity:
                seen.clear()
                validity = current
            data = self._call(
                deadline,
                connection.uid,
                "SEARCH",
                None,
                "HEADER",
                "To",
                _quote(recipient),
            )
            if not data or any(not isinstance(item, bytes) for item in data):
                raise MailboxError("Invalid IMAP search response.")
            uids = b" ".join(data).split()
            if any(not uid.isdigit() or int(uid) <= 0 for uid in uids):
                raise MailboxError("Invalid UID in IMAP search response.")
            links: set[str] = set()
            for uid in uids:
                self._remaining(deadline)
                if uid in seen:
                    continue
                fetched = self._call(
                    deadline, connection.uid, "FETCH", uid, "(UID BODY.PEEK[])"
                )
                raw = None
                for item in fetched or []:
                    if isinstance(item, tuple) and len(item) == 2:
                        metadata, payload = item
                        match = re.search(rb"\bUID (\d+)\b", metadata)
                        if (
                            match
                            and match.group(1) == uid
                            and isinstance(payload, bytes)
                        ):
                            raw = payload
                            break
                if raw is None:
                    # An expunge between SEARCH and FETCH legitimately yields no body.
                    if fetched in (None, [], [None]):
                        continue
                    raise MailboxError("Invalid IMAP fetch response.")
                seen.add(uid)
                if not _matches_recipient(raw, recipient_key):
                    continue
                try:
                    links.add(extract_button_link(raw, button_text=button_text))
                except LinkNotFoundError:
                    continue
            self._remaining(deadline)
            if len(links) > 1:
                raise AmbiguousLinkError("Matching messages have different links.")
            if links:
                return links.pop()
            time.sleep(min(poll_interval, self._remaining(deadline)))
