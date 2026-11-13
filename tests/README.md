# Test plan

`test_extraction.py` contains executable synthetic unit tests for MIME decoding,
HTML selection, anchor matching, repeated/conflicting links, and error handling.
These messages are generated with Python's email package or explicit raw bytes;
they are not the recruiter's samples. Run them with `python -m pytest` using the
project virtual environment.

Still planned:

- Unit tests: MIME decoding, recipient matching, button-link extraction,
  polling deadlines, and transport errors without a network connection.
- Integration tests: SMTP delivery into one shared mailbox, IMAP reads,
  mail arriving before and during a wait, old-run isolation, concurrent readers,
  and unchanged message flags.
- Keep the two supplied EML samples as fixtures after reviewing them for secrets.
  They have not yet been provided to this project.

Integration tests will use the `integration` marker and a pinned GreenMail image.
The server configuration and runnable instructions will be added with that suite.
