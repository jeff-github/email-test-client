# Email Test Client

A Python 3.12+ library for end-to-end tests that share an IMAP mailbox.

## Current status

Step 1: installable project scaffold and design record. Email parsing, the public
client API, IMAP operations, and executable tests are not implemented yet.
The assignment's `activation.eml` and `site_invitation.eml` samples are still needed.

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

Once behavior tests are added:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

Currently pytest will report no tests collected (exit code 5). Do not interpret
that as a passing suite. Docker/GreenMail setup and integration test commands will
be documented when they are implemented. Docker is not needed for this scaffold.

## Design and scope

See [the design record](docs/design.md) for proposed behavior, assumptions,
tradeoffs, and the implementation sequence. This document describes intended
behavior rather than claiming that it already works.

## AI assistance

OpenAI Codex assisted with reviewing the assignment, proposing the implementation
plan, and creating the initial packaging configuration and documentation. Update
this record as implementation progresses so the final disclosure reflects actual
usage. The candidate should review and understand each change before submission.

## Submission

Keep genuine incremental Git commits. The requested final ZIP should include
source and a Git bundle preserving history (or be accompanied by a repository
link), since a normal source ZIP does not preserve Git history. Final packaging
and clean-install verification are still pending.
