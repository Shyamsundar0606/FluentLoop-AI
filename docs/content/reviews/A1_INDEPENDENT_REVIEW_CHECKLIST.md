# A1 independent review checklist

**Unfilled review packet. No reviewer, qualification, date, signature or approval is asserted. All ten lessons remain draft.**

Review the exact `1.0.2` source and importer identified in [the structured pending template](A1_PUBLICATION_REVIEW_TEMPLATE.json). If either changes, refresh the digests and obtain applicable reviews again. Read [correction results](A1_CONTENT_CORRECTION_RESULTS.md), the archived prior source and the authorized local preview.

## Reviewer identification and scope

Reviewer name: ____________________
Role and relevant qualifications: ____________________
Independence from content generation: ____________________
Lesson slug(s), version, source SHA-256 and importer SHA-256: ____________________
Review date/time **with timezone**: ____________________
Evidence location / written findings / signature reference: ____________________
Decision (pending / changes required / approved): ____________________

Repeat the following for **each of a1-001 through a1-010**. Review the exact materials rather than treating automated test results as evidence of language quality.

## French language and pronunciation

- [ ] Check accents, apostrophes, spelling, noun gender, agreement and English translations.
- [ ] Verify every French example and dialogue turn for naturalness and register.
- [ ] Check être, avoir, aller, faire, parler, habiter and aimer in all six present-tense persons.
- [ ] Check elision, liaison and exceptions; specifically inspect dix, un/une, mon and voudrais.
- [ ] Approve IPA/phonetic variants and any separately licensed pronunciation/audio models.
- [ ] Resolve every remaining question in the lesson-by-lesson correction report.

## Pedagogy and sequence

- [ ] Confirm beginner A1 suitability, realistic lesson length and manageable vocabulary load.
- [ ] Confirm each objective has instruction, an example, practice and appropriate assessment.
- [ ] Verify written activities make no unsupported listening or pronunciation-assessment claim.
- [ ] Explain fixed chunks before using them; distinguish a useful expression from a full grammar paradigm.
- [ ] Check the 18/20 age examples, tu/vous transitions, negation/article changes, plural des and price vocabulary.
- [ ] Approve the explicit prerequisite chain: first lesson has no prior lesson; each following lesson requires its preceding lesson. Record the dependency review for every lesson.
- [ ] Confirm incomplete alphabet/listening coverage is represented honestly; ten lessons are not complete A1 certification.

## Exercise answer-key review

- [ ] Solve all five exercises independently before consulting the keys.
- [ ] Confirm one intended valid option, fair distractors, prerequisites and accurate feedback.
- [ ] Recheck A1-001 exercise 5 and A1-005 exercise 1 after their prompt corrections.
- [ ] Check all 50 correct indices against the exact approved source and the authorized preview.
- [ ] Confirm accent normalization does not silently accept a different French word.

## Rights and attribution (separate reviewer)

- [ ] Establish authorship and provenance for vocabulary definitions, explanations, dialogues, questions, IPA and reference data.
- [ ] Identify permissions, license terms and required attribution for any adapted or external material.
- [ ] Review audio/voice/dataset licenses separately; a voice license does not clear lesson wording.
- [ ] Verify that a dictionary citation is not being treated as permission to redistribute its content.
- [ ] Resolve the source metadata's current “no publication license asserted” and rights-pending notices before final approval; update the version/digests if metadata changes.
- [ ] Record genuine rights evidence. The rights reviewer must be separate from all lesson reviewers, including prerequisite reviews.

## Technical and authorized publication decision

- [ ] Run source validation, isolated import/re-import and the read-only audit on the final source/importer.
- [ ] Confirm source/database equality, zero published lessons while pending, all six CEFR levels and preserved learner history.
- [ ] Inspect retained legacy lexical aliases; do not merge or delete them at the expense of saved review/card references.
- [ ] Verify draft denial through courses, lessons, AI retrieval, daily plans, vocabulary review and speech targets.
- [ ] Complete a **copy** of the version-2 template. Pending templates deliberately fail publication validation.
- [ ] Supply real reviewer names, qualifications, independence attestations, evidence references and timezone-aware dates for language, pedagogy, answers, dependencies and rights.
- [ ] A current administrator makes an explicit separate publication decision **after** all reviews, with administrator user ID, evidence and timezone-aware decision date.
- [ ] Review the feature PR; do not merge or publish automatically.
- [ ] Only an authorized operator may later run the existing `python -m app.publish_content --review-record ...` command against the intended database after all conditions pass.

The technical gate verifies record completeness, current admin role, timestamps, digests and live source/database integrity. It cannot independently prove a person's qualifications, a signature's authenticity or ownership rights. The authorized operator must verify that evidence; do not invent it or substitute AI output for human approval.
