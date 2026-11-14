# Submission test evidence

Validated November 14, 2026 on Windows with Python 3.13.7, pytest 9.2.0,
pytest-cov 7.1.0, GreenMail 2.1.15 and Java 21. The library and test implementation
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
- `all-2026-11-14.xml`: JUnit result with all 70 collected variants.
- `coverage-2026-11-14.xml`: coverage report for that execution.

Command used:

```text
python -m pytest --run-e2e --cov --cov-report=term-missing --cov-report=xml:reports/coverage-2026-11-14.xml --junitxml=reports/all-2026-11-14.xml
```

GreenMail ran directly on Java because the local Docker engine was unavailable.
Compose configuration validation passed. Docker execution, hosted CI, Python 3.12
execution, real TLS interoperability and other IMAP server implementations remain
unverified. The tests verify retrieval and extraction; they do not visit action
links or assert application-side token validity.

Original fixtures are preserved byte-for-byte. Their provenance and SHA256 hashes
are recorded in `tests/fixtures/README.md`. The case catalog maps automated test
functions to requirements and records remaining portability and TLS work.
