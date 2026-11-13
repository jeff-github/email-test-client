# Email Test Client

A Python 3.12+ library for end-to-end tests that share an IMAP mailbox.

## Current status

Step 2: a pure link-extraction function with synthetic unit tests is implemented.
The IMAP client and wait loop are not implemented yet. The assignment's
`activation.eml` and `site_invitation.eml` samples were not accessible in the chat
or located in the project/Downloads folders; sample inspection and regression
tests remain pending. Synthetic messages are not substitutes for those fixtures.

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

Run the extraction tests (no Docker or credentials needed):

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

Docker/GreenMail setup and integration test commands will be documented when
they are implemented.

## Extracting a button link

```python
from pathlib import Path

from email_test_client import extract_button_link

link = extract_button_link(
    Path("activation.eml").read_bytes(), button_text="Activate account"
)
```

The caller supplies the EML file; it is not yet included in this repository.
Use `button_text="Accept invitation"` for an invitation message. The function
returns the link without opening it. It matches anchor text with case and
whitespace normalized and decodes HTML entities in the destination.

Missing HTML or a missing label raises `LinkNotFoundError`. Different URLs for
the same label raise `AmbiguousLinkError`. Other extraction problems raise
`LinkExtractionError`, the base class for both errors. Identical repeated links
are accepted. Only absolute HTTP(S) destinations are supported.

The parser does not render CSS or execute JavaScript, infer image-only labels,
or extract Outlook-only VML buttons. It uses the MIME-selected HTML body and
excludes attachments. These choices must be checked against the actual samples.

## Design and scope

See [the design record](docs/design.md) for proposed behavior, assumptions,
tradeoffs, and the implementation sequence. IMAP and polling sections describe
intended behavior; extraction behavior above is implemented and unit-tested.

## AI assistance

OpenAI Codex assisted with reviewing the assignment, proposing the implementation
plan, creating the packaging configuration and documentation, and implementing
the extraction function and synthetic tests. Codex ran pytest and Ruff locally.
It has not inspected the recruiter's EML files. Update this record as work
progresses. The candidate should review and understand each change before submission.

## Submission

Keep genuine incremental Git commits. The requested final ZIP should include
source and a Git bundle preserving history (or be accompanied by a repository
link), since a normal source ZIP does not preserve Git history. Final packaging
and clean-install verification are still pending.
