> Current checkpoint —23 November2026: this exact batch is now imported into the personal main database as unpublished drafts after direct owner authorization, fresh verified backup and disposable restore rehearsal. The older staging statements below describe the pre-import review. Qualified human review and empirical calibration remain pending. No future batch is authorized.

# Previously empty modules: authored drafts, not main imports

This separate batch fills the 17 source-empty slots identified by the prior
52-module audit. It contains **51 lessons, 102 scored exercises and 17 open
writing/speaking transfer tasks**, with three lessons per module:

1. Read and notice: contextual grammar, a linked rule/example, three linked
   lexical expressions, reading interpretation and grammar-scope questions.
2. Listen and integrate: a fictional scripted exchange, stance/detail listening,
   comparison with the reading and explicitly supported exact-phrase retrieval.
3. Transfer and assess: an unfamiliar written/spoken task, task-specific criteria,
   saved-error review and delayed retrieval of the lexical expressions.

Input 2 requires Input 1; transfer requires both inputs. The global learning map
keeps the existing recommended module order. Source generation is idempotent only
for byte-identical files; edited releases require a new version.

| Module | Scenario and focus |
|---|---|
| A2-05 | Routine appointment; availability, politeness and confirmation |
| A2-06 | Picnic change; reason, apology and individual constraints |
| A2-07 | Parcel collection; times and clarification |
| A2-08 | Day-trip disruption; cumulative practical problem |
| B1-05 | Shared project; pronoun reference and coherence |
| B1-06 | Local news; announcement, opinion and unanswered questions |
| B1-07 | Lost object; informal/formal requests and uncertainty |
| B1-08 | Volunteer event; options, condition and provisional commitment |
| B2-06 | University attendance; concession and structured argument |
| B2-07 | Shared workspace; negotiation and practical constraints |
| B2-08 | Collective energy proposal; evidence and distributional concerns |
| C1-05 | Research meeting; shifting qualifications and absent voices |
| C1-07 | Project update; modal commitment, reformulation and prosody |
| C1-08 | Cultural service; multi-source decision and mediation |
| C2-05 | Public discussion; humour, stance and a changed criterion |
| C2-06 | Institutional invitation; ambiguity and spontaneous clarification |
| C2-08 | Museum narrative; presupposition, attribution and register |

## Validation and review scope

`backend/scripts/validate_missing_modules.py` accepts no database URL and uses a
fresh in-memory SQLite database with foreign keys. It seeds all 130 existing
source lessons, imports this batch twice, checks all 102 intended/wrong answers,
checks 51 internal prerequisite links and verifies that no pre-existing row was
changed or removed. Result: 181 source lessons and 620 objective exercises across
main-source and staged packs. These totals are **not** main-database totals.
The validation manifest records release hashes and the actual method used.

On 23 November 2026 the port issue was traced to Windows taking about two seconds
to return explicit refusal, beyond the guard's original 0.3-second deadline.
The bounded deadline was corrected to three seconds; ambiguous errors still refuse
startup. After preflight, all 80 staged lessons were rehearsed on a fresh PostgreSQL
restore of main: every original row was preserved, and all keys/prerequisites and
duplicate-import checks passed. All 34 staged listening scripts and a 600-character
boundary generated valid WAV output. See
`docs/learning/STAGED-POSTGRES-VALIDATION.json`. This is not human pronunciation
acceptance. No lesson may be imported into main without separate authorization.

The original 29 staged lessons remain unchanged. Main was last verified at
101 lessons/470 exercises. All 80 staged lessons remain unpublished and outside
main. No data from the historical M08 database is merged or modified.

## Educational limitations

All 52 modules now have authored input, but this does not mean that every CEFR
competency has been adequately taught or demonstrated. The new advanced items
practise source fidelity, inference, concession, register and pragmatic scope;
exact-phrase retrieval and vocabulary matching are supported practice, not proof
of advanced proficiency. Word ranges guide tasks, not certification thresholds.

The dialogues are original, realistic-style scripts. Local synthesis can perform
all roles in one voice. They do not constitute authentic varied-speaker recordings,
spontaneous interaction or an acoustic prosody assessment. Extended natural speech,
pronunciation and productive-task judgements still require qualified human review.

AI-assisted reference review consulted the
[OQLF discussion of compound subordinators](https://vitrinelinguistique.oqlf.gouv.qc.ca/24238/la-grammaire/le-verbe/modes/subjonctif/subjonctif-ou-indicatif-apres-les-subordonnants-composes),
the [OQLF conditional entry](https://vitrinelinguistique.oqlf.gouv.qc.ca/fiche-gdt/fiche/26570992/conditionnel)
and the existing Council of Europe competency blueprint. The passages are original;
the sequence is the project's interpretation, not an official grammar syllabus.
No independent human approval or empirical CEFR calibration is claimed.

## Audio contract

The authoring definition and both learner/reviewer audio routes now allow up to
600 characters, matching the existing private Piper synthesis schema/provider.
Ownership, live permission checks, rate limiting, RIFF validation and the 6 MB
output cap remain in force. Tests accept 600, reject 601, and verify revocation
before synthesis. Frozen answer keys and previously imported releases are unchanged.
