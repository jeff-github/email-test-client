# Submission test evidence

Validated November 14, 2026 on Windows with Python 3.13.7, pytest 9.2.0,
pytest-cov 7.1.0, GreenMail 2.1.15 in a Linux container on Docker Desktop 4.56.0.
Docker Engine 29.1.3; Compose v5.0.0-desktop.1; container Java 21.0.13.
Pytest and the library ran on Windows; only GreenMail was containerized. The library and test implementation
correspond to commit `2fd297f`; subsequent submission changes update documentation
and package evidence, without modifying the library implementation.

- Full suite: **70 passed**, zero failures, errors or skips.
- Fast tests: 54; real-server E2E: 16.
- Smoke selection overlaps those totals: four fast and two E2E cases.
- Six supplied-email regressions: original-byte extraction, unmodified-byte IMAP
  retrieval, and SMTP-to-IMAP retrieval with only To changed for isolation, for
  each of activation.eml and site_invitation.eml.
- Branch-aware coverage: 93% overall, 90% client, 100% extraction.
- No library implementation changes were needed for the supplied templates.
- Ruff lint/format checks and local wheel/sdist build passed.

Saved execution artifacts:
- `docker-2026-11-14.xml`: Docker-backed run, 70 passed in 6.86 seconds.
- `coverage-docker-2026-11-14.xml`: coverage from the Docker-backed run.
- `docker-server-2026-11-14.log`: GreenMail container startup logs.
- `all-2026-11-14.xml`: prior standalone Java run with all 70 variants.
- `coverage-2026-11-14.xml`: coverage report for that execution.

Command used:

```text
docker compose -p emailtestclient-verification up -d
python -m pytest --run-e2e --cov --cov-report=term-missing --cov-report=xml:evidence/coverage-docker-2026-11-14.xml --junitxml=evidence/docker-2026-11-14.xml
docker compose -p emailtestclient-verification down
```

Docker startup, SMTP/IMAP readiness, the full suite and teardown passed without
code or Compose changes. Image: `greenmail/standalone:2.1.15`; digest
`sha256:309ba544ea482e5d4265d09921cdab07c8dad2cc4481d715c9b8ff5d3f0a149f`.
Ports were bound only to 127.0.0.1:33025 and 127.0.0.1:33143.
The initial tool-sandbox attempt passed 54 fast tests but blocked sockets
(WinError 10013), causing 16 E2E setup errors. Rerunning with local network access
produced the recorded 70-pass result. The disposable container and network were
removed afterward. Earlier standalone Java results remain as historical evidence.
Hosted CI, Python 3.12 execution, real TLS interoperability and other IMAP server
implementations remain unverified. The tests verify retrieval and extraction; they do not visit action
links or assert application-side token validity.

Original fixtures are preserved byte-for-byte. Their provenance and SHA256 hashes
are recorded in `tests/fixtures/README.md`. The case catalog maps automated test
functions to requirements and records remaining portability and TLS work.
