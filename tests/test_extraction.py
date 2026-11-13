"""Synthetic messages only; these are NOT the recruiter's EML samples."""

from email.message import EmailMessage

import pytest

from email_test_client import (
    AmbiguousLinkError,
    LinkExtractionError,
    LinkNotFoundError,
    extract_button_link,
)


def html_message(html: str, **kwargs: str) -> bytes:
    message = EmailMessage()
    message.set_content(html, subtype="html", **kwargs)
    return message.as_bytes()


@pytest.mark.parametrize("label", ["Activate account", "Accept invitation"])
def test_selects_labeled_button_instead_of_first_link(label):
    raw = html_message(
        '<a href="https://example.com/logo">Logo</a>'
        f'<a href="https://example.com/action?token=synthetic">{label}</a>'
        '<a href="https://example.com/help">Help</a>'
    )
    assert extract_button_link(raw, button_text=label) == (
        "https://example.com/action?token=synthetic"
    )


def test_normalizes_case_whitespace_entities_and_nested_markup():
    raw = html_message(
        '<a href="https://example.com/a?x=1&amp;y=2">'
        "\n <strong>ACTIVATE</strong><br/> account&nbsp; </a>"
    )
    assert extract_button_link(raw, button_text="activate ACCOUNT") == (
        "https://example.com/a?x=1&y=2"
    )


@pytest.mark.parametrize("encoding", ["base64", "quoted-printable"])
@pytest.mark.parametrize("charset", ["utf-8", "iso-8859-1"])
def test_decodes_mime_transfer_encoding_and_character_set(encoding, charset):
    raw = html_message(
        '<a href="https://example.com/a">Activer le compte été</a>',
        cte=encoding,
        charset=charset,
    )
    assert extract_button_link(raw, button_text="Activer le compte été") == (
        "https://example.com/a"
    )


def test_selects_html_alternative_and_ignores_html_attachment():
    message = EmailMessage()
    message.set_content("Activate account: https://example.com/plain")
    message.add_alternative(
        '<a href="https://example.com/body">Activate account</a>', subtype="html"
    )
    message.add_attachment(
        '<a href="https://example.com/attachment">Activate account</a>',
        subtype="html",
        filename="attachment.html",
    )
    assert extract_button_link(message.as_bytes(), button_text="Activate account") == (
        "https://example.com/body"
    )


def test_html_attachment_does_not_replace_missing_html_body():
    message = EmailMessage()
    message.set_content("Plain text body")
    message.add_attachment(
        '<a href="https://example.com/attachment">Activate account</a>',
        subtype="html",
        filename="attachment.html",
    )
    with pytest.raises(LinkNotFoundError):
        extract_button_link(message.as_bytes(), button_text="Activate account")


def test_identical_repeated_links_are_accepted():
    raw = html_message('<a href="https://example.com/a">Activate account</a>' * 2)
    assert extract_button_link(raw, button_text="Activate account") == (
        "https://example.com/a"
    )


def test_different_destinations_are_ambiguous_and_tokens_are_not_logged():
    raw = html_message(
        '<a href="https://example.com/a?token=secret1">Activate account</a>'
        '<a href="https://example.com/a?token=secret2">Activate account</a>'
    )
    with pytest.raises(AmbiguousLinkError) as error:
        extract_button_link(raw, button_text="Activate account")
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "href", ["", "/relative", "javascript:alert(1)", "https://", "https://[bad"]
)
def test_rejects_invalid_matching_destinations(href):
    raw = html_message(f'<a href="{href}">Activate account</a>')
    with pytest.raises(LinkExtractionError, match="absolute HTTP"):
        extract_button_link(raw, button_text="Activate account")


def test_missing_href_is_an_extraction_error():
    with pytest.raises(LinkExtractionError, match="absolute HTTP"):
        extract_button_link(
            html_message("<a>Activate account</a>"), button_text="Activate account"
        )


def test_label_is_not_a_substring_match():
    raw = html_message('<a href="https://example.com/a">Do not Activate account</a>')
    with pytest.raises(LinkNotFoundError):
        extract_button_link(raw, button_text="Activate account")


@pytest.mark.parametrize("label", ["", " \n\t"])
def test_rejects_empty_requested_label(label):
    with pytest.raises(ValueError, match="button_text"):
        extract_button_link(b"", button_text=label)


def test_unknown_charset_is_a_clear_decoding_error():
    raw = (
        b'Content-Type: text/html; charset="unknown-charset"\r\n\r\n'
        b'<a href="https://example.com/a">Activate account</a>'
    )
    with pytest.raises(LinkExtractionError, match="decoded"):
        extract_button_link(raw, button_text="Activate account")


@pytest.mark.parametrize(
    "html",
    [
        '<a href="https://example.com/a">Activate account',
        '<a href="https://example.com/a"><a>Activate account</a></a>',
    ],
)
def test_rejects_unsupported_broken_anchor_structure(html):
    with pytest.raises(LinkExtractionError):
        extract_button_link(html_message(html), button_text="Activate account")
