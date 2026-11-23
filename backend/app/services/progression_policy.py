"""Conservative formative recommendations, never CEFR placement or certification."""
from datetime import timezone

POLICY_VERSION='formative-evidence-v1'

def evidence_for(lessons, sessions):
    """Use only the caller's current-version, completed full-lesson sessions.

    80% is an uncalibrated local revision cue, not a validated cut score. Repeated
    same-day attempts do not supply delayed retrieval evidence. Productive work
    always remains subject to qualitative review.
    """
    objective=[item for item in lessons if item['kind']!='writing']
    writing=[item for item in lessons if item['kind']=='writing']
    secure=0;needs_revision=[];delayed=[]
    for lesson in objective:
        attempts=sorted((s for s in sessions if str(s.lesson_id)==lesson['id']
            and s.lesson_content_version==lesson['content_version'] and s.status=='completed'
            and s.activity_key=='lesson' and s.max_score_points>0 and s.completed_at is not None),
            key=lambda s:s.completed_at)
        if not attempts or 100*attempts[-1].score_points/attempts[-1].max_score_points<80:
            needs_revision.append(lesson['id']);continue
        dates={s.completed_at.replace(tzinfo=timezone.utc).date() if s.completed_at.tzinfo is None
               else s.completed_at.astimezone(timezone.utc).date() for s in attempts
               if 100*s.score_points/s.max_score_points>=80}
        if len(dates)<2:delayed.append(lesson['id'])
        else:secure+=1
    if not lessons:state='content_pending'
    elif needs_revision:state='practice_or_revision_needed'
    elif delayed:state='delayed_retrieval_needed'
    elif writing:state='productive_review_needed'
    else:state='objective_practice_secure'
    return dict(policy_version=POLICY_VERSION,state=state,objective_lessons=len(objective),
        objective_secure=secure,revision_lesson_ids=needs_revision,delayed_retrieval_lesson_ids=delayed,
        productive_tasks=len(writing),productive_review_required=bool(writing),
        mastery_demonstrated=False,calibration='experimental; no empirical cut-score validation',
        guidance='Use unseen transfer, delayed retrieval and qualitative writing/speaking review. Saved work and quiz completion alone do not prove mastery.')
