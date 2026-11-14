# Supplied email fixtures

Source: `homework.zip`, supplied by the user on November 14, 2026. These EML files
are byte-identical to their ZIP entries. `.gitattributes` disables text newline
conversion for EML files. These assignment samples use example.com addresses and
example action links; do not substitute real account tokens into public fixtures.

| File | SHA256 |
| --- | --- |
| activation.eml | ad973654e698d36d02a4290430de0fd70bd48716911b2699ff4bca998993bbc2 |
| site_invitation.eml | b776831b986021da3ce8add071974ab693c46dd9997cb20ec78745308e1550ef |

Activation uses multipart/alternative with quoted-printable plain and HTML bodies.
The requested Activate account anchor is separate from logo, website and support
links. Its full href must retain the code and lang parameters.

Invitation uses multipart/alternative with base64 bodies. Its HTML is nested in
multipart/related alongside an inline PNG. The To header has a display name.
Accept invitation must be selected instead of logo, site, website or support links;
both token and site parameters must survive decoding.

`expected_links.json` records the reviewed full destinations and original
recipients. Tests assert exact equality, not just a host or path prefix. Direct
extraction and IMAP APPEND tests use unchanged bytes. SMTP tests replace only the
To address with a unique recipient and assert that the MIME body is unchanged.
Test-created IMAP folders are removed individually; the shared INBOX is not purged.

All six checks passed on November 14, 2026. These tests validate extraction and
retrieval, not whether an external application accepts the action tokens.
