# Daily study plans

Open Home and choose **Create today’s plan**. This explicit on-demand action saves a plan for the authenticated learner, local study date and saved French level. Reloading or signing in again returns that persisted identity. No scheduled job or model generates plans in the background.

## Target and allocation

Read the existing daily target; use 15 minutes only when no saved preference exists. Supported existing targets remain 5, 10, 15, 20 and 30 minutes. Never overwrite a preference. Plans use estimated activity durations, not actual study-duration claims.

Choose due reviews first, then an unfinished permitted lesson, unresolved mistake evidence, suitable new material and tutor/speaking practice. At most one lesson candidate is allocated. Three review cards get up to two minutes, a lesson gets up to five, and each distinct conversation gets at most ten. Remaining time goes to those real practice opportunities within their cap.

Examples: an authorized preview learner may receive 2 minutes of vocabulary, 5 of lesson work, 4 of speaking and 4 of tutor practice. An ordinary learner with no published content receives 8/7 minutes of speaking/tutor practice according to preference. A 30-minute target without usable curriculum has 20 estimated minutes of distinct practice and an honest unmet remainder; no filler activity is cloned.

The ten A1 drafts remain hidden from ordinary learners. No published-content availability is assumed for A2–C2. Review availability comes only from actual permitted vocabulary; otherwise tutor and speaking remain linked through their existing features.

## Completion policy

| Activity | Trusted completion condition |
|---|---|
| Vocabulary | Assigned review session is completed and has at least one actual saved answer |
| Lesson / revisit / continue | Linked owned lesson session reaches completed status after activity start |
| Tutor | Linked owned conversation receives a successful assistant reply after activity start |
| Speaking | Linked owned speech session contains a successful transcribed or explicitly user-confirmed speech turn after activity start |

Page views, failed replies, silence, unsupported speech and navigation do not complete activities. A text fallback alone does not complete a speaking assignment. Backend state reconciliation updates Home when the learner returns; the explicit completion endpoint applies the same checks. Partial plans persist with remaining activities visible.

## Same-day resume and regeneration

The plan snapshots its target and selected context at creation. Changing preferences does not replace a started plan. An explicit **Regenerate unstarted plan** action is permitted only while every current activity is pending. It increments the generation, retains cancelled prior activity rows, and uses current availability/preferences. A repeated generation request is idempotent. Started/completed plans reject regeneration.

Switching CEFR level creates or resumes the separate plan for that level/date, preserving earlier plans and review history. Reading an earlier-level plan is allowed when content remains authorized; starting its activities requires selecting that plan's level explicitly first. The application never changes the level automatically.

## Timezones

Use the saved `UserProfile.timezone` IANA identifier; UTC is the documented default and invalid/unsupported legacy values fall back to UTC. Do not derive timezone from name, address or browser hints. The plan records the resolved timezone used for its local date. UTC timestamps are used for generation/completion and all schedules. DST repeated hours retain the same study date; a real local-date boundary creates a different plan. A saved plan's timezone/target are not rewritten by later preference edits.

## Outages and permissions

Planning and grading do not call Ollama. Existing non-model lesson/review activities remain available during model outages. If neither published nor previously permitted vocabulary exists and inference is offline, a plan can still be generated/resumed but its model-dependent practice cannot complete until those services recover. Display an honest service error rather than inventing offline lessons or completion.

Recheck publication/RBAC at every content boundary. Hide revoked activities without deleting historical evidence. Use review history under Learn for actual results and scheduled dates. Home and Learn handle loading, empty and error states; an unavailable plan does not hide existing practice navigation.
