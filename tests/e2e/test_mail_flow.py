"""Real SMTP -> shared mailbox -> public Python API -> expected URL."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier, Event
from uuid import uuid4

import pytest

from email_test_client import (
    AmbiguousLinkError,
    AuthenticationError,
    EmailClient,
    EmailTimeoutError,
)

pytestmark = [pytest.mark.e2e, pytest.mark.integration, pytest.mark.regression]


def wait(config, recipient, label="Activate account"):
    with EmailClient(config) as client:
        return client.wait_for_link(
            recipient=recipient, button_text=label, timeout=5, poll_interval=0.05
        )


@pytest.mark.parametrize(
    ("label", "cte"),
    [("Activate account", "quoted-printable"), ("Accept invitation", "base64")],
)
@pytest.mark.smoke
def test_mail_arriving_before_wait(server_config, recipient, send_mail, label, cte):
    expected = f"https://example.com/action?token={uuid4().hex}"
    send_mail(recipient, expected, label, cte)
    assert wait(server_config, recipient, label) == expected


def test_mail_arriving_after_first_empty_search(
    server_config, recipient, send_mail, monkeypatch
):
    searched = Event()
    expected = "https://example.com/delayed"
    with EmailClient(server_config) as client:
        # Observe a completed real SEARCH, then release SMTP delivery. This is
        # synchronization, not a mock response or an arbitrary startup sleep.
        connection = client._connection
        original = connection.uid

        def observe(command, *args):
            result = original(command, *args)
            if command == "SEARCH":
                searched.set()
            return result

        monkeypatch.setattr(connection, "uid", observe)

        def deliver():
            assert searched.wait(timeout=5), "Client never searched"
            send_mail(recipient, expected)

        with ThreadPoolExecutor(max_workers=1) as pool:
            delivery = pool.submit(deliver)
            assert (
                client.wait_for_link(
                    recipient=recipient,
                    button_text="Activate account",
                    timeout=5,
                    poll_interval=0.05,
                )
                == expected
            )
            delivery.result(timeout=5)


def test_old_run_and_similar_address_do_not_match(server_config, recipient, send_mail):
    send_mail(f"qa+old-{uuid4().hex}@example.com", "https://example.com/old")
    # Contains the entire requested address as a substring, so HEADER search
    # may return it; exact parsed-address comparison must reject it.
    similar = recipient.replace("qa+", "qa+prefix-qa+")
    send_mail(similar, "https://example.com/wrong")
    send_mail(recipient, "https://example.com/right")
    assert wait(server_config, recipient) == "https://example.com/right"


@pytest.mark.parametrize("repetition", range(3))
def test_parallel_executions_share_one_mailbox(server_config, send_mail, repetition):
    recipients = [f"qa+{uuid4().hex}@example.com" for _ in range(4)]
    links = [f"https://example.com/run/{repetition}/{index}" for index in range(4)]
    for address, link in zip(recipients, links, strict=True):
        send_mail(address, link)
    barrier = Barrier(4, timeout=5)

    def read(address):
        with EmailClient(server_config) as client:
            barrier.wait()
            return client.wait_for_link(
                recipient=address, button_text="Activate account", timeout=5
            )

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(read, recipients)) == links


def test_two_readers_same_message_leave_flags_unchanged(
    server_config, recipient, send_mail, inspector
):
    send_mail(recipient, "https://example.com/shared")
    inspector.select("INBOX")
    status, data = inspector.uid("SEARCH", None, "HEADER", "To", f'"{recipient}"')
    assert status == "OK" and len(data[0].split()) == 1
    uid = data[0]
    # Seen mail must still be discoverable. An independent client sets this flag.
    assert inspector.uid("STORE", uid, "+FLAGS", r"(\Seen)")[0] == "OK"
    before = inspector.uid("FETCH", uid, "(FLAGS)")
    barrier = Barrier(2, timeout=5)

    def read():
        barrier.wait()
        return wait(server_config, recipient)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(read) for _ in range(2)]
        assert [job.result(timeout=10) for job in results] == [
            "https://example.com/shared",
            "https://example.com/shared",
        ]
    assert inspector.uid("FETCH", uid, "(FLAGS)") == before


def test_read_does_not_set_seen(server_config, recipient, send_mail, inspector):
    send_mail(recipient, "https://example.com/unread")
    inspector.select("INBOX", readonly=True)
    _, data = inspector.uid("SEARCH", None, "HEADER", "To", f'"{recipient}"')
    uid = data[0]
    before = inspector.uid("FETCH", uid, "(FLAGS)")
    assert b"\\Seen" not in b" ".join(before[1])
    assert wait(server_config, recipient) == "https://example.com/unread"
    assert inspector.uid("FETCH", uid, "(FLAGS)") == before


def test_conflicting_messages_fail_explicitly(server_config, recipient, send_mail):
    send_mail(recipient, "https://example.com/one")
    send_mail(recipient, "https://example.com/two")
    with pytest.raises(AmbiguousLinkError):
        wait(server_config, recipient)


def test_no_delivery_times_out(server_config, recipient):
    with EmailClient(server_config) as client, pytest.raises(EmailTimeoutError):
        client.wait_for_link(
            recipient=recipient,
            button_text="Activate account",
            timeout=0.3,
            poll_interval=0.05,
        )


def test_real_server_rejects_wrong_password(server_config):
    with pytest.raises(AuthenticationError):
        with EmailClient(replace(server_config, password="deliberately-wrong")):
            pytest.fail("Invalid credentials were accepted")
