# Testing strategy: fail early, prove behavior at the right boundary

This is a Python library, not a web service. API tests exercise its exported
Python classes/functions and errors. E2E tests exercise the full library flow
from actual SMTP submission through a shared mailbox to real IMAP reads and the
returned URL; they do not test a web application's signup UI or follow the link.

## Layers and commands

Run these from the repository with the virtual environment's Python. On Windows,
replace `python` below with `.\.venv\Scripts\python.exe` if not activated.

| Suite | Command | Purpose |
| --- | --- | --- |
| Fast smoke | `python -m pytest -m "smoke and not e2e"` | Package import, both button labels, basic wait API |
| Unit | `python -m pytest -m unit` | MIME and HTML behavior without IMAP |
| API | `python -m pytest -m api` | Context lifecycle, errors, timeout contract, IMAP commands |
| Fast regression | `python -m pytest -m "regression and not e2e"` | Protect named failure modes without Docker |
| All fast | `python -m pytest -m "not e2e" --cov --cov-report=term-missing` | Branch-aware coverage and fast feedback |
| Server smoke | `python -m pytest --run-e2e -m "smoke and e2e"` | Both button labels through real SMTP/IMAP |
| All E2E | `python -m pytest --run-e2e -m e2e` | Shared mailbox, concurrency, flags, failures |
| Full suite | `python -m pytest --run-e2e --cov --junitxml=reports/all.xml` | All layers, with real server required |

Markers overlap intentionally: a regression can also be an API or E2E test.
`python -m pytest` runs fast tests and explicitly skips E2E. To request E2E, pass
`--run-e2e`; unavailable infrastructure then fails instead of silently skipping.
Smoke cases repeat in the full suite intentionally in CI: first prove the basic
environment works, then run all scenarios.

## Reproducible local server

```text
docker compose up -d
python -m pytest --run-e2e -m "smoke and e2e"
python -m pytest --run-e2e -m e2e
docker compose down
```

The versioned image is `greenmail/standalone:2.1.15`. Ports bind only to loopback:
SMTP 33025 and IMAP 33143. The test account is `qa` / `test-password`. SMTP envelope
recipients are actual `qa+<uuid>@example.com` addresses, not a separate delivery
address disguised by headers. `-Dgreenmail.sieve.ignore.detail=true` routes them to the
shared account. The actual 2.1.15 server needs this option: without it, smoke tests
found separate per-address mailboxes. See the [GreenMail options](https://greenmail-mail-test.github.io/greenmail/).
No persistent volume or global mailbox purge is used. Existing test messages stay
in the mailbox until this disposable container is removed.

### Java fallback when Docker is unavailable

With Java 11+ installed, download the [standalone 2.1.15 JAR](https://repo.maven.apache.org/maven2/com/icegreen/greenmail-standalone/2.1.15/greenmail-standalone-2.1.15.jar)
to `.tools/greenmail-standalone-2.1.15.jar` (ignored by Git). Start it in another
terminal; quote JVM properties in PowerShell:

```powershell
java '-Dgreenmail.hostname=127.0.0.1' '-Dgreenmail.smtp.hostname=127.0.0.1' '-Dgreenmail.smtp.port=33025' '-Dgreenmail.imap.hostname=127.0.0.1' '-Dgreenmail.imap.port=33143' '-Dgreenmail.api.port=0' '-Dgreenmail.users=qa:test-password@example.com' '-Dgreenmail.sieve.ignore.detail=true' -jar .tools/greenmail-standalone-2.1.15.jar
```

Run the same pytest commands, then stop Java with Ctrl+C. Do not run both servers
at once: they intentionally use identical ports and accounts.

Readiness checks exercise both SMTP and authenticated IMAP with bounded retries.
The delayed-delivery test waits for the first actual search before sending; it
does not use a guessed startup sleep. Parallel tests use barriers, separate
connections, UUID addresses, and bounded future waits. Another test has two
readers request the same message. An independent IMAP observer checks flags.

## Risk-to-test mapping

| Risk | Evidence |
| --- | --- |
| Email arrives before wait | Immediate-search API test and real delivery-before-wait E2E |
| Email arrives during wait | Fake-clock test and synchronized SMTP producer |
| Old or similar recipients collide | Exact-header API tests and shared-mailbox E2E |
| Same test runs concurrently | Four simultaneous connections, three E2E repetitions |
| Reading consumes or marks mail | Read-only/PEEK assertions; independent flag checks |
| UID namespace resets | API regression clears cached UIDs on UIDVALIDITY change |
| Search/FETCH race | API tests for disappeared messages and mismatched fetched UID |
| MIME encoding differs | Parameterized unit cases and both transfer encodings over SMTP |
| Duplicate actions are ambiguous | Identical/conflicting URL API cases; conflicting-message E2E |
| Mail never arrives | Deterministic deadline tests and real-server timeout |
| Auth/network fails | API errors and real invalid-password E2E; no blanket retry |
| STARTTLS fails | API regression proves credentials are not sent afterward |
| Packaging broken | Isolated import outside checkout and CI package build |

## Shift-left workflow

1. Define an observable behavior or failure mode before changing its implementation.
2. Add a focused API/unit regression first; use a fake monotonic clock instead of
   real sleeps to make timeout cases fast and deterministic.
3. Run smoke, then fast tests plus lint before committing.
4. Validate protocol claims with the real-server suite, not mocks alone.
5. CI runs smoke, lint, fast tests, coverage, and build on Python 3.12 and 3.13.
   After fast checks pass it starts GreenMail and runs server smoke/E2E. JUnit XML
   and coverage reports are retained. The workflow is authored; its presence does
   not imply that remote CI has run.

Coverage is a gap-finding tool, not proof of correctness. There is no arbitrary
percentage gate; prioritize meaningful assertions and known concurrency risks.
There are no automatic retries of failed tests to conceal flakiness.

## Remaining boundaries

Latest validation on 2026-11-14: all 70 tests passed (54 fast, 16 E2E) using
Windows Python 3.13.7 against GreenMail 2.1.15 in Docker Engine 29.1.3
(Linux containers), Compose v5.0.0-desktop.1. Coverage remains 93% overall.
Startup, loopback port mappings and teardown passed without configuration changes.
Reports: `evidence/docker-2026-11-14.xml` and
`evidence/coverage-docker-2026-11-14.xml`. The prior Java run is also retained.
The six new supplied-sample cases assert complete expected URLs for both files:
direct original-byte extraction, exact-byte IMAP APPEND into isolated folders,
and SMTP delivery to a fresh plus-address with the original MIME body unchanged.
Expected URLs are static reviewed fixtures, not calculated by the function under
test. No action link is opened and no token's live validity is asserted.
The Word documents in `docs/deliverables/` have been updated to the November 14
baseline: 70 passing test variants and completed supplied-sample validation.
Submission copies of the reports are retained under `evidence/`.

Local validation on 2026-11-13: Python 3.13.7, GreenMail 2.1.15 running directly
on Java 21. All 64 tests passed (52 fast, 12 E2E), including four fast smoke and
two server smoke cases. Branch-aware coverage: 93% overall, 90% client, 100%
extraction. Reports are generated under `reports/` and `coverage.xml` (Git-ignored).
The Docker engine was unavailable; Compose configuration validation passed but
container execution was not verified in that earlier run. The November 14 Docker
run above closes that gap. Python 3.12 and hosted CI execution remain pending.

The initial real-server smoke run caught a mailbox configuration defect:
GreenMail created separate users for plus-addresses. Inspection of the 2.1.15
implementation established that `greenmail.sieve.ignore.detail` requires the
explicit value `true`. Both documented startup routes now include it, and the
SMTP-to-shared-IMAP smoke cases pass. This is a concrete example of using smoke
tests to catch an environment assumption before relying on larger regression runs.

- Both supplied EML fixtures now pass; see `tests/fixtures/README.md` for provenance.
- E2E uses plaintext on loopback. TLS/STARTTLS settings have API tests, but
  certificate interoperability requires a separate TLS server setup. No OAuth.
- GreenMail demonstrates one server, not every IMAP product.
- E2E uses threads with independent connections, not multiple physical machines.
- Socket timeouts are inactivity limits; strict wall-clock cancellation is not
  claimed for indefinite streaming or DNS resolution.

