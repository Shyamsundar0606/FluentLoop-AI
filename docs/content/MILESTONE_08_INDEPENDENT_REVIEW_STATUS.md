# Milestone 08 independent review status

All three real A1 courses remain draft. No independent decision was recorded
against the existing demo in this milestone.

| Category | Status | Evidence needed |
| --- | --- | --- |
| French language and grammar | Pending | Qualified review of usage, examples, translations and register |
| Pronunciation and phonetics | Pending | Listening checks, phonetic claims and documented variants |
| Pedagogy and CEFR | Pending | Teaching order, progression, prerequisites and assessment fit |
| Answer keys | Pending | Independently solved items, validated distractors and variants |
| Licensing and provenance | Pending | Rights and attribution evidence from a separate qualified reviewer |

The review workspace is at `/profile/curriculum-review` on a frontend running
the final code. Its backend verifies the signed-in account and CSRF token for
writes. Preview admins can inspect drafts in the development environment.
Independent reviewers need a verified, active non-admin identity and a
server-managed `CURRICULUM_REVIEWER_GRANTS` entry. The JSON object maps a user
UUID to `categories` and a `qualification` evidence reference. The default is
empty. A trusted operator checks qualifications and independence before
granting access. Reviewers record findings, required corrections and evidence
in the workspace. Licensing approval requires evidence.

Each saved decision records the authenticated account ID, permission evidence,
course version, packet digest, category, decision and UTC timestamp. The
latest decision for each reviewer and category applies to that exact packet.
A correction stays blocking until the reviewer resolves it on the same packet
or the content changes and receives new reviews. Historical decisions remain
available. Synthetic reviewers and findings used for verification live only
in disposable test databases.
