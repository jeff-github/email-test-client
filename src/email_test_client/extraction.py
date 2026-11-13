"""Extract a labeled HTML link from an RFC 5322 message without network access."""

from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from urllib.parse import urlsplit


class LinkExtractionError(ValueError):
    """The message does not contain a usable, unambiguous requested link."""


class LinkNotFoundError(LinkExtractionError):
    """No HTML body or anchor with the requested text was found."""


class AmbiguousLinkError(LinkExtractionError):
    """The requested label identifies multiple different destinations."""


def _normalize_label(text: str) -> str:
    return " ".join(text.split()).casefold()


class _AnchorParser(HTMLParser):
    """Collect anchor text, including nested inline markup and line breaks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str | None]] = []
        self._text: list[str] | None = None
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            if self._text is not None:
                raise LinkExtractionError("Nested anchor elements are unsupported.")
            self._href = dict(attrs).get("href")
            self._text = []
        elif tag == "br" and self._text is not None:
            self._text.append(" ")

    def handle_data(self, data: str) -> None:
        if self._text is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._text is not None:
            self.links.append(("".join(self._text), self._href))
            self._text = None
            self._href = None

    def close(self) -> None:
        super().close()
        if self._text is not None:
            raise LinkExtractionError("An anchor element is not closed.")


def extract_button_link(raw_email: bytes, *, button_text: str) -> str:
    """Return the HTTP(S) href whose anchor text matches ``button_text``.

    Match text case-insensitively with whitespace collapsed. Inspect the MIME
    HTML body, not attachments. Repeated matches are accepted only when their
    destinations are identical. Do not fetch, follow, or rewrite the URL.
    """
    label = _normalize_label(button_text)
    if not label:
        raise ValueError("button_text must not be empty or whitespace-only.")

    message = BytesParser(policy=policy.default).parsebytes(raw_email)
    body = message.get_body(preferencelist=("html",))
    if body is None:
        raise LinkNotFoundError("The message has no HTML body.")
    try:
        html = body.get_content(errors="strict")
    except (LookupError, UnicodeError, ValueError):
        raise LinkExtractionError("The HTML body could not be decoded.") from None

    parser = _AnchorParser()
    parser.feed(html)
    parser.close()
    hrefs = [href for text, href in parser.links if _normalize_label(text) == label]
    if not hrefs:
        raise LinkNotFoundError("No anchor matches the requested button text.")

    destinations: set[str] = set()
    for href in hrefs:
        destination = (href or "").strip()
        try:
            parsed = urlsplit(destination)
            valid = (
                parsed.scheme.lower() in {"http", "https"}
                and bool(parsed.hostname)
                and not any(character.isspace() for character in destination)
            )
        except ValueError:
            valid = False
        if not valid:
            raise LinkExtractionError(
                "A matching anchor must have an absolute HTTP(S) destination."
            )
        destinations.add(destination)

    if len(destinations) != 1:
        raise AmbiguousLinkError("Matching anchors have different destinations.")
    return destinations.pop()
