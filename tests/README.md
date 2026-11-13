# Test plan

No executable tests exist in the initial scaffold. Add behavior tests alongside
each implementation step; an empty suite is not a passing validation result.

- Unit tests: MIME decoding, recipient matching, button-link extraction,
  polling deadlines, and transport errors without a network connection.
- Integration tests: SMTP delivery into one shared mailbox, IMAP reads,
  mail arriving before and during a wait, old-run isolation, concurrent readers,
  and unchanged message flags.
- Keep the two supplied EML samples as fixtures after reviewing them for secrets.
  They have not yet been provided to this project.

Integration tests will use the `integration` marker and a pinned GreenMail image.
The server configuration and runnable instructions will be added with that suite.
