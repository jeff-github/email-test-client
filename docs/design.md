# Design record

## 1. Correlation comes before polling

Each independent test execution creates a fresh plus-address before triggering
the application, for example `qa+<uuid4>@example.com`. A human-readable test name
alone is insufficient because the same test can run concurrently on many hosts.

The initial mailbox search includes existing messages: the application may send
the email before the caller starts waiting. Neither the wait start time nor the
unread flag identifies the correct run. Old runs are isolated by their different
recipient addresses, not by clearing a shared mailbox.

Assumptions to confirm against the supplied fixtures:

- The caller controls the address used by the application.
- The original plus-address survives in a message header accessible over IMAP.
- A scenario's expected message can be distinguished using the recipient and
  the requested button label, with additional filters if the fixtures require it.

If an address is reused for indistinguishable requests, the library cannot infer
which request produced a message. Document that limitation explicitly.

## 2. Small, separate responsibilities

Implemented components are IMAP access and waiting in `client.py`, and pure
message parsing in `extraction.py`. Tests exercise timeout behavior without a server;
integration tests prove actual protocol behavior against a server.

Use Python's standard `imaplib` and `email` packages initially. The first extraction
implementation uses standard-library `HTMLParser`; it handles anchor text, nested
inline markup, entities, and line breaks without a runtime dependency. This choice
is provisional until the real samples are accessible. Pytest, Ruff, and build
are development tools only.

Use standard IMAP operations rather than Gmail-only extensions. Connection
settings will expose host, port, mailbox, credentials, and TLS mode. Describe
supported authentication explicitly rather than claiming every provider's login
flow works. Credentials must not be committed.

## 3. Read without interfering

Use UIDs, a read-only mailbox, and non-marking body fetches. Never use deletion,
expunge, or read flags as coordination. Each concurrent caller owns its connection;
do not share a mutable IMAP connection across threads.

Server-side recipient search narrows candidates; parsed addresses must still be
validated exactly. Avoid repeated body downloads within a wait. Any incremental
UID optimization must preserve the initial scan and handle UIDVALIDITY correctly.
Start with a simple correct search and measure before adding cursor complexity.

## 4. Explicit outcomes

The convenience API waits for a recipient's message and returns the link
behind a specified button label. Extract from decoded MIME HTML with an HTML
parser, not a regex over raw email or the first URL in the message.

Implemented extraction policies: select the HTML MIME body using `get_body`,
decode strictly using its charset, and match normalized anchor text exactly.
Missing bodies/labels raise `LinkNotFoundError`; identical repeated destinations
are accepted; conflicting destinations raise `AmbiguousLinkError`. Invalid or
missing HTTP(S) destinations, decoding failures, and nested/unclosed anchors
raise `LinkExtractionError`. Error text excludes the message content and URLs.
Only HTML entity decoding and surrounding href whitespace removal change the
returned href; query parameters, percent escapes, and redirects are preserved.

This is a structural HTML parser, not a renderer: CSS visibility, image labels,
VML, plain-text link inference, and general broken-HTML repair are out of scope
for now. The actual sample files must be inspected to confirm this scope fits.
Within one search snapshot, multiple matching messages must agree on their URL;
otherwise the wait raises `AmbiguousLinkError`. Messages lacking the requested
button are skipped; other extraction failures surface immediately. A successful
result cannot account for messages that arrive after its search snapshot.
Timeouts, authentication failures, transport failures, and extraction failures
should be distinguishable. Diagnostics must not expose credentials or link tokens.

Use a monotonic deadline and bound network operations as well as polling sleeps.
Avoid hiding permanent errors behind timeout retries.

The implementation re-selects read-only on each poll, checks UIDVALIDITY, searches
the full matching recipient set, and caches examined UIDs only within that wait.
It trades a small metadata search per poll for simpler correctness than a UID
cursor. No reconnect/retry loop can silently reset the wait budget. Network errors
close the unusable connection. Socket inactivity is capped by remaining time,
but DNS and indefinite streaming are not hard wall-clock bounded. Context setup
has a separate network timeout. Context exit shuts down the socket directly;
it does not issue CLOSE/EXPUNGE or wait for a LOGOUT reply.

## 5. Repository choices

- A `src` layout makes imports use the installed package and helps reveal
  packaging mistakes that imports from the repository root can hide.
- A local `.venv` isolates dependencies from other projects.
- `pyproject.toml` holds package metadata and tool configuration in one place.
- Python 3.12 is the compatibility target; local development initially uses 3.13.
- No async framework, distributed locks, background service, or Gmail API is
  planned for this focused assignment.

## Implementation sequence

1. Scaffold, editable-install check, lint, and package build.
2. Review the two EML samples; implement and test parsing and button extraction.
3. Implement recipient correlation, IMAP access, and deadline-based waiting.
4. Add GreenMail integration tests with one shared mailbox and concurrent readers.
5. Verify setup from a clean environment, finish documentation, preserve history,
   and create the submission ZIP.

## Interview checkpoints

- Why is a unique recipient stronger than a timestamp or unread flag?
- Why must the first search include mail that already exists?
- How do read-only operations allow independent concurrent readers?
- What is verified by unit tests versus a real IMAP server?
- Which assumptions limit correctness when the same recipient is reused?
- Why decode MIME before parsing HTML, rather than search raw message text?
- Why match a label instead of selecting the first URL or a CSS class?
- Why accept repeated identical links but reject conflicting destinations?
