"""Deterministic client tests; the scripted IMAP peer is not a real server."""

import imaplib
import ssl
from email.message import EmailMessage

import pytest

from email_test_client import (
    AmbiguousLinkError,
    AuthenticationError,
    EmailClient,
    EmailTimeoutError,
    ImapConfig,
    LinkExtractionError,
    MailboxError,
)
from email_test_client import client as module

RECIPIENT = "qa+run123@example.com"
LINK = "https://example.com/activate?token=synthetic"

pytestmark = pytest.mark.api


def mail(to=RECIPIENT, link=LINK, label="Activate account"):
    message = EmailMessage()
    message["To"] = to
    message.set_content(f'<a href="{link}">{label}</a>', subtype="html")
    return message.as_bytes()


class Clock:
    now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Peer:
    """Each read-only select exposes the next scripted mailbox snapshot."""

    def __init__(self, snapshots=None, validities=None):
        self.snapshots = snapshots or [{}]
        self.validities = validities or [b"1"] * len(self.snapshots)
        self.round = -1
        self.calls = []
        self.timeouts = []
        self.sock = self
        self.closed = False

    def settimeout(self, value):
        self.timeouts.append(value)

    def login(self, username, password):
        self.calls.append(("LOGIN", username))
        return "OK", []

    def starttls(self, ssl_context):
        assert ssl_context.verify_mode == ssl.CERT_REQUIRED
        self.calls.append(("STARTTLS",))
        return "OK", []

    def select(self, mailbox, readonly):
        self.calls.append(("SELECT", mailbox, readonly))
        self.round = min(self.round + 1, len(self.snapshots) - 1)
        return "OK", [b"0"]

    def response(self, code):
        assert code == "UIDVALIDITY"
        return code, [self.validities[self.round]]

    def uid(self, command, *args):
        self.calls.append((command, *args))
        snapshot = self.snapshots[self.round]
        if command == "SEARCH":
            # Deliberately overmatch, as IMAP HEADER search can do.
            return "OK", [b" ".join(snapshot)]
        assert command == "FETCH"
        uid, body = args
        assert body == "(UID BODY.PEEK[])"
        if snapshot[uid] is None:
            return "OK", [None]
        raw = snapshot[uid]
        return "OK", [(b"1 (UID " + uid + b" BODY[] {100}", raw), b")"]

    def shutdown(self):
        self.closed = True


@pytest.fixture
def setup(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(module.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(module.time, "sleep", clock.sleep)

    def make(peer=None, **config):
        peer = peer or Peer()

        def connect(*args, **kwargs):
            if "ssl_context" in kwargs:
                assert kwargs["ssl_context"].check_hostname
            return peer

        monkeypatch.setattr(module.imaplib, "IMAP4_SSL", connect)

        # Keep IMAP4's error classes intact when substituting its constructor.
        class Plain:
            error = imaplib.IMAP4.error
            abort = imaplib.IMAP4.abort

            def __new__(cls, *args, **kwargs):
                return connect(*args, **kwargs)

        monkeypatch.setattr(module.imaplib, "IMAP4", Plain)
        return EmailClient(ImapConfig("localhost", "test", "secret", **config))

    return make, clock


def wait(client, **kwargs):
    return client.wait_for_link(
        recipient=RECIPIENT, button_text="Activate account", **kwargs
    )


@pytest.mark.regression
@pytest.mark.smoke
def test_existing_mail_found_immediately_with_non_destructive_commands(setup):
    make, clock = setup
    peer = Peer([{b"7": mail()}])
    with make(peer) as client:
        assert wait(client) == LINK
    assert clock.now == 0
    assert peer.closed
    assert ("SELECT", '"INBOX"', True) in peer.calls
    assert ("SEARCH", None, "HEADER", "To", f'"{RECIPIENT}"') in peer.calls
    assert ("FETCH", b"7", "(UID BODY.PEEK[])") in peer.calls
    assert all(call[0] not in {"STORE", "EXPUNGE", "CLOSE"} for call in peer.calls)


@pytest.mark.regression
def test_later_arrival_and_skip_previous_runs_and_substring_matches(setup):
    make, clock = setup
    old = {b"1": mail("qa+old@example.com"), b"2": mail("x" + RECIPIENT)}
    peer = Peer([old, old | {b"3": mail()}])
    with make(peer) as client:
        assert wait(client) == LINK
    assert clock.now == 1
    assert len([call for call in peer.calls if call[0] == "FETCH"]) == 3


def test_timeout_caps_last_sleep_and_socket_timeouts(setup):
    make, clock = setup
    peer = Peer()
    with make(peer) as client, pytest.raises(EmailTimeoutError):
        wait(client, timeout=2.5, poll_interval=2)
    assert clock.now == 2.5
    assert peer.timeouts == [2.5, 2.5, 0.5, 0.5]


@pytest.mark.regression
def test_uidvalidity_change_invalidates_seen_cache(setup):
    make, _ = setup
    peer = Peer([{b"1": mail(label="Other email")}, {b"1": mail()}], [b"1", b"2"])
    with make(peer) as client:
        assert wait(client) == LINK
    assert len([call for call in peer.calls if call[0] == "FETCH"]) == 2


@pytest.mark.parametrize("recipient", [f"Test <{RECIPIENT}>", RECIPIENT.upper()])
def test_exact_parsed_address_not_display_text_or_local_case(setup, recipient):
    make, _ = setup
    with make(Peer([{b"1": mail(recipient)}])) as client:
        if recipient.startswith("Test"):
            assert wait(client) == LINK
        else:
            with pytest.raises(EmailTimeoutError):
                wait(client, timeout=1)


def test_domain_case_and_multiple_to_addresses(setup):
    make, _ = setup
    peer = Peer([{b"1": mail("other@example.com, qa+run123@EXAMPLE.COM")}])
    with make(peer) as client:
        assert wait(client) == LINK


@pytest.mark.parametrize("different", [False, True])
def test_multiple_messages_must_agree_on_link(setup, different):
    make, _ = setup
    second = "https://example.com/different" if different else LINK
    with make(Peer([{b"1": mail(), b"2": mail(link=second)}])) as client:
        if different:
            with pytest.raises(AmbiguousLinkError):
                wait(client)
        else:
            assert wait(client) == LINK


def test_invalid_link_is_not_hidden_as_timeout(setup):
    make, clock = setup
    with make(Peer([{b"1": mail(link="/relative")}])) as client:
        with pytest.raises(LinkExtractionError):
            wait(client)
    assert clock.now == 0


def test_message_removed_between_search_and_fetch(setup):
    make, _ = setup
    with make(Peer([{b"1": None}, {b"2": mail()}])) as client:
        assert wait(client) == LINK


def test_authentication_failure_is_sanitized_and_closes_socket(setup):
    make, _ = setup
    peer = Peer()

    def reject(*args):
        raise imaplib.IMAP4.error("secret server detail")

    peer.login = reject
    with pytest.raises(AuthenticationError, match="authentication failed") as error:
        with make(peer):
            pass
    assert "secret" not in str(error.value)
    assert peer.closed


@pytest.mark.parametrize("deadline_elapsed", [False, True])
def test_network_failure_distinguished_from_wait_deadline(setup, deadline_elapsed):
    make, clock = setup
    peer = Peer()

    def fail(*args):
        clock.now += 1 if deadline_elapsed else 0
        raise TimeoutError("private detail")

    peer.uid = fail
    with make(peer) as client:
        expected = EmailTimeoutError if deadline_elapsed else MailboxError
        with pytest.raises(expected):
            wait(client, timeout=1)
    assert peer.closed


def test_server_no_is_not_an_empty_inbox(setup):
    make, _ = setup
    peer = Peer()
    peer.uid = lambda *args: ("NO", [b"private detail"])
    with make(peer) as client, pytest.raises(MailboxError, match="rejected"):
        wait(client)


def test_missing_uidvalidity_is_explicit_error(setup):
    make, _ = setup
    with make(Peer(validities=[None])) as client:
        with pytest.raises(MailboxError, match="UIDVALIDITY"):
            wait(client)


def test_starttls_precedes_login(setup):
    make, _ = setup
    peer = Peer()
    with make(peer, security="starttls", port=143):
        assert peer.calls[:2] == [("STARTTLS",), ("LOGIN", "test")]


@pytest.mark.regression
def test_failed_starttls_never_sends_credentials(setup):
    make, _ = setup
    peer = Peer()
    peer.starttls = lambda **kwargs: ("NO", [])
    with pytest.raises(MailboxError, match="STARTTLS"):
        with make(peer, security="starttls", port=143):
            pass
    assert not any(call[0] == "LOGIN" for call in peer.calls)
    assert peer.closed


def test_two_clients_read_same_mail_without_shared_cache_or_connection(setup):
    make, _ = setup
    snapshot = {b"1": mail()}
    first, second = Peer([snapshot]), Peer([snapshot])
    with make(first) as client_one:
        with make(second) as client_two:
            assert wait(client_one) == wait(client_two) == LINK
            client_one.close()
            assert wait(client_two) == LINK
    assert first.closed and second.closed


def test_non_inbox_mailbox_is_quoted(setup):
    make, _ = setup
    peer = Peer([{b"1": mail()}])
    with make(peer, mailbox="Test Mail") as client:
        assert wait(client) == LINK
    assert ("SELECT", '"Test Mail"', True) in peer.calls


def test_unexpected_fetch_uid_is_not_used(setup):
    make, _ = setup
    peer = Peer([{b"1": mail()}])
    original = peer.uid

    def wrong_uid(command, *args):
        if command == "FETCH":
            return "OK", [(b"1 (UID 99 BODY[] {100}", mail()), b")"]
        return original(command, *args)

    peer.uid = wrong_uid
    with make(peer) as client, pytest.raises(MailboxError, match="fetch"):
        wait(client)


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_rejects_invalid_wait_timeout(setup, value):
    make, _ = setup
    with make() as client, pytest.raises(ValueError, match="timeout"):
        wait(client, timeout=value)


def test_rejects_recipient_injection_and_empty_label_before_search(setup):
    make, _ = setup
    peer = Peer()
    with make(peer) as client:
        for recipient, label in [
            (RECIPIENT + "\r\nALL", "Activate account"),
            (RECIPIENT, " "),
        ]:
            with pytest.raises(ValueError):
                client.wait_for_link(recipient=recipient, button_text=label)
    assert not any(call[0] == "SEARCH" for call in peer.calls)


def test_cache_is_per_wait_not_shared_between_calls(setup):
    make, _ = setup
    peer = Peer([{b"1": mail()}])
    with make(peer) as client:
        assert wait(client) == wait(client) == LINK
    assert len([call for call in peer.calls if call[0] == "FETCH"]) == 2


def test_requires_context_and_hides_password():
    config = ImapConfig("localhost", "user", "secret")
    assert "secret" not in repr(config)
    with pytest.raises(RuntimeError, match="with block"):
        wait(EmailClient(config))
