# Email Test Client

A Python 3.12+ library for end-to-end tests that share an IMAP mailbox.

## Current status

The extraction function, IMAP client, and wait loop are implemented. Pytest covers
unit, public Python API, regression, smoke, and real-server end-to-end behavior.
See [testing instructions](docs/testing.md) for commands and coverage boundaries.
The assignment's `activation.eml` and `site_invitation.eml` from `homework.zip`
were validated on November 14, 2026. Both original samples extract the expected
complete action URLs with no library changes. Six new regression cases cover
direct extraction, unmodified bytes through IMAP, and SMTP-to-IMAP retrieval with
only the recipient header changed for run isolation. All 70 tests passed locally, including a verified Docker-backed run.
GreenMail ran in Docker; pytest and the Python library ran on Windows.
See `evidence/TEST_RESULTS.md` for versions and saved results.

## Development setup

From the repository directory in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m build
```

Python 3.13 is the initial local development interpreter. The package declares
Python 3.12 as its minimum; actual execution on 3.12 remains to be verified.
Explicit virtual-environment executable paths avoid requiring shell activation.

Run fast tests (no Docker or credentials needed):

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

Run local server tests using the pinned, loopback-only GreenMail service:

```powershell
docker compose up -d
.\.venv\Scripts\python.exe -m pytest --run-e2e --cov --junitxml=reports/results.xml
docker compose down
```

The fixture waits for SMTP and authenticated IMAP readiness. An unavailable server
fails an explicitly requested E2E run. The server uses disposable test credentials
and routes `qa+<unique>@example.com` to the same `qa` mailbox. No personal Gmail
account is used. A Java fallback is described in the testing instructions.

## Waiting for a message

```python
import os
from uuid import uuid4

from email_test_client import EmailClient, ImapConfig

recipient = f"qa+{uuid4().hex}@example.com"
# Trigger the application's signup with this recipient before waiting.
config = ImapConfig(
    host=os.environ["IMAP_HOST"],
    username=os.environ["IMAP_USERNAME"],
    password=os.environ["IMAP_PASSWORD"],
)
with EmailClient(config) as mailbox:
    link = mailbox.wait_for_link(
        recipient=recipient,
        button_text="Activate account",
        timeout=30,
    )
```

Defaults: verified TLS on port 993, INBOX, LOGIN authentication, one-second polling,
and a ten-second socket inactivity timeout. STARTTLS and explicit plaintext are
also available; set the corresponding port yourself (typically 143, or 33143 for
this local test server). Plaintext is for the local test setup. OAuth token
acquisition is not implemented; use a server/account that permits LOGIN.

Use one client context per concurrent caller. The client searches already-arrived
mail immediately, validates the exact parsed `To` address, and fetches by UID with
`BODY.PEEK[]` in a read-only mailbox. It never deletes mail or uses unread flags as
coordination. Domain comparison ignores case; local parts retain case. Only bare
ASCII recipient addresses are accepted. Bcc-only mail or a rewritten `To` header
is not supported in this version.

Messages with no requested button are skipped. Invalid matching links fail
immediately. Multiple matches in a search must agree on the destination; otherwise
`AmbiguousLinkError` is raised. This checks the current search snapshot, not future
deliveries. Generate a fresh recipient for each independent request.

`EmailTimeoutError`, `AuthenticationError`, and `MailboxError` distinguish absence
of mail, rejected credentials, and protocol/network failures. Failed connections
are not automatically retried. The monotonic wait budget bounds polling and caps
socket inactivity timeouts; it is not a hard wall-clock cancellation guarantee
against DNS stalls or a server streaming forever. Connection setup is outside the
wait budget. Full recipient searches recur, but examined bodies are downloaded
only once per wait unless UIDVALIDITY changes.

## Extracting a button link

```python
from pathlib import Path

from email_test_client import extract_button_link

link = extract_button_link(
    Path("tests/fixtures/activation.eml").read_bytes(), button_text="Activate account"
)
```

Both supplied EML files are included unchanged under `tests/fixtures/`.
Use `button_text="Accept invitation"` for an invitation message. The function
returns the link without opening it. It matches anchor text with case and
whitespace normalized and decodes HTML entities in the destination.

Missing HTML or a missing label raises `LinkNotFoundError`. Different URLs for
the same label raise `AmbiguousLinkError`. Other extraction problems raise
`LinkExtractionError`, the base class for both errors. Identical repeated links
are accepted. Only absolute HTTP(S) destinations are supported.

The parser does not render CSS or execute JavaScript, infer image-only labels,
or extract Outlook-only VML buttons. It uses the MIME-selected HTML body and
excludes attachments. Both actual supplied templates pass, including the nested
multipart/related invitation with an inline logo.

## Design and scope

See [the design record](docs/design.md) for proposed behavior, assumptions,
tradeoffs, and the implementation sequence. See [the test matrix](docs/testing.md)
for evidence and remaining gaps, including TLS integration and hosted CI.

## AI assistance

OpenAI Codex assisted with reviewing the assignment, proposing the implementation
plan, creating the packaging configuration and documentation, and implementing
the extraction function, IMAP polling, and the pytest testing framework, including
synthetic unit/API/regression tests, GreenMail E2E tests, smoke checks, and CI.
Codex ran local validation; see the test documentation for actual results.
Codex also inspected and validated the two supplied EML files and added regression
tests without changing the library implementation. Update this record as work
progresses. The candidate should review and understand each change before submission.

## Submission

The submission ZIP contains this source tree, both original EML fixtures, the
four Word documents in `docs/deliverables/`, recorded test evidence in
`evidence/`, and `git-history.bundle` preserving all local Git history and branches.
It excludes virtual environments, downloaded server binaries, caches and local
credentials. Install dependencies and start GreenMail as described above.

After extracting the ZIP, run tests from its `EmailTestClient` directory. A source
ZIP is not itself a Git checkout. To restore the repository and its history:

```text
git clone --branch codex/link-extraction git-history.bundle ../EmailTestClient-history
git -C ../EmailTestClient-history log --oneline --all
```

`SUBMISSION.json` in the ZIP records the packaged commit and bundle SHA256.
The restored checkout contains the same tracked source and documents as the ZIP;
the bundle and submission metadata are packaging additions, not tracked files.
See `evidence/TEST_RESULTS.md` for the executed test environment and limits.

Word documents:

- `docs/deliverables/Interview_Walkthrough.docx`: design explanation and interview rehearsal.
- `docs/deliverables/Software_Test_Plan.docx`: scope, risks, test strategy and acceptance criteria.
- `docs/deliverables/Test_Cases_and_User_Journeys.docx`: 48 case descriptions covering 70 test variants.

- `docs/deliverables/Docker_Test_Interview_Demo_Guide.docx`: PowerShell demo commands, expected results, coverage viewing and troubleshooting.
