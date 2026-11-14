# Test plan

See [testing strategy and commands](../docs/testing.md) for all layers:
package smoke, extraction unit tests, public API/transport contracts, regressions,
and real SMTP-to-IMAP E2E tests. All use pytest; markers overlap intentionally.

`test_extraction.py` contains executable synthetic unit tests for MIME decoding,
HTML selection, anchor matching, repeated/conflicting links, and error handling.
These messages are generated with Python's email package or explicit raw bytes;
they are not the recruiter's samples. Run them with `python -m pytest` using the
project virtual environment.

Implemented coverage:

- Unit tests: MIME decoding, recipient matching, button-link extraction,
  polling deadlines, and transport errors without a network connection.
- Integration tests: SMTP delivery into one shared mailbox, IMAP reads,
  mail arriving before and during a wait, old-run isolation, concurrent readers,
  and unchanged message flags.

The supplied samples are now preserved unchanged under `fixtures/`, with reviewed
static expected URLs. `test_supplied_samples.py` checks original-byte extraction;
`e2e/test_supplied_samples_imap.py` checks original bytes through IMAP and the
original bodies through SMTP/IMAP with unique recipients. All six new cases passed.

Integration tests use both `integration` and `e2e` markers and a pinned GreenMail
image. They require `--run-e2e`; see `compose.yaml` and the testing instructions.
