from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from app.services.progression_policy import evidence_for

LESSON=dict(id='lesson',kind='lesson',content_version='v2')
def attempt(day=0,score=9,version='v2',key='lesson',maximum=10):
    return SimpleNamespace(lesson_id='lesson',lesson_content_version=version,status='completed',
        activity_key=key,score_points=score,max_score_points=maximum,
        completed_at=datetime(2026,11,1,tzinfo=timezone.utc)+timedelta(days=day))

def test_repeats_are_not_mastery_and_require_delayed_retrieval():
    assert evidence_for([LESSON],[attempt(),attempt()])['state']=='delayed_retrieval_needed'
    body=evidence_for([LESSON],[attempt(),attempt(2)])
    assert body['objective_secure']==1 and body['state']=='objective_practice_secure'
    assert body['mastery_demonstrated'] is False
    assert evidence_for([LESSON],[attempt(),attempt(2,score=3)])['state']=='practice_or_revision_needed'

def test_old_version_focused_practice_zero_points_and_writing_cannot_establish_mastery():
    for attempts in ([attempt(version='v1')],[attempt(key='grammar')],[attempt(maximum=0)]):
        assert evidence_for([LESSON],attempts)['objective_secure']==0
    body=evidence_for([dict(id='w',kind='writing',content_version='v2',status='saved_submission')],[])
    assert body['state']=='productive_review_needed' and not body['mastery_demonstrated']
    assert evidence_for([],[])['state']=='content_pending'
