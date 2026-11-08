"""M08.2 navigation and genuine mistake-review regressions."""
from uuid import UUID,uuid4
from sqlalchemy import select,func
from app.learning_models import LearningSessionExercise,ExerciseAttempt,LessonProgress
from app.study_models import ReviewAttempt
from app.curriculum_models import GrammarTopic
from test_interactive_learning import interactive,start
from test_learning import _csrf
from test_learning import _register_and_login,_set_role
from app.services.email import get_email_service


def test_saved_reading_position_does_not_grade_or_complete(interactive):
    client,sessions,lid=interactive;saved=start(client,lid);sid=saved['id']
    assert saved['lesson']['learning_flow_version']==1
    for position in (1,2,1,2,3):
        response=client.post(f'/api/v1/learning/sessions/{sid}/position',headers=_csrf(client),json={'position':position})
        assert response.status_code==200 and response.json()['current_section_position']==position
        assert client.get(f'/api/v1/learning/sessions/{sid}').json()['current_section_position']==position
    for invalid in (-1,4,True,'2'):
        assert client.post(f'/api/v1/learning/sessions/{sid}/position',headers=_csrf(client),json={'position':invalid}).status_code==422
    assert client.post(f'/api/v1/learning/sessions/{sid}/position',json={'position':1}).status_code==403
    with sessions() as db:
        assert db.scalar(select(func.count(ExerciseAttempt.id)))==0
        assert db.scalar(select(LessonProgress)).completion_count==0


def test_legacy_snapshot_navigation_remains_untouched(interactive):
    client,sessions,lid=interactive;saved=start(client,lid);sid=saved['id']
    from app.learning_models import LearningSession
    with sessions.begin() as db:
        row=db.get(LearningSession,UUID(sid));old={k:v for k,v in row.lesson_snapshot.items() if k!='learning_flow_version'}
        row.lesson_snapshot=old
    response=client.post(f'/api/v1/learning/sessions/{sid}/position',headers=_csrf(client),json={'position':1})
    assert response.status_code==409
    assert client.get(f'/api/v1/learning/sessions/{sid}').json()['lesson']==old
    _register_and_login(client,client.app.dependency_overrides[get_email_service](),'navigation-other@example.com')
    _set_role(sessions,'navigation-other@example.com','admin')
    assert client.get(f'/api/v1/learning/sessions/{sid}/review').status_code==404
    assert client.post(f'/api/v1/learning/sessions/{sid}/position',headers=_csrf(client),json={'position':1}).status_code==404


def test_review_uses_real_evidence_and_resolution_keeps_history_and_srs(interactive):
    client,sessions,lid=interactive;saved=start(client,lid);sid=saved['id'];first=saved['exercises'][0]
    with sessions() as db:
        frozen=db.get(LearningSessionExercise,UUID(first['id'])).exercise_snapshot
        correct=frozen['correct_option_id'];wrong=next(o['id'] for o in frozen['options'] if o['id']!=correct)
    assert client.get('/api/v1/learning/mistakes').json()['items']==[]
    response=client.post(f'/api/v1/learning/sessions/{sid}/answers',headers=_csrf(client),json={
        'session_exercise_id':first['id'],'selected_option_id':wrong,'idempotency_key':str(uuid4())})
    assert response.status_code==200 and not response.json()['is_correct']
    mistakes=client.get('/api/v1/learning/mistakes').json()['items'];assert len(mistakes)==1
    assert mistakes[0]['learning_objective_id']==frozen['learning_objective_id'] and mistakes[0]['objective_title']
    review=client.get(f'/api/v1/learning/sessions/{sid}/review').json()
    assert review['items'][0]['practice_available'] is True
    focused=client.post('/api/v1/learning/practice/sessions',headers=_csrf(client),json={
        'category':'mistakes','lesson_id':lid,'learning_objective_id':frozen['learning_objective_id']}).json()
    payload={'session_exercise_id':focused['exercises'][0]['id'],'selected_option_id':correct,'idempotency_key':str(uuid4())}
    for _ in range(2):assert client.post(f"/api/v1/learning/sessions/{focused['id']}/answers",headers=_csrf(client),json=payload).status_code==200
    for _ in range(2):assert client.post(f"/api/v1/learning/sessions/{focused['id']}/complete",headers=_csrf(client)).status_code==200
    assert client.get('/api/v1/learning/mistakes').json()['items']==[]
    assert not client.get(f'/api/v1/learning/sessions/{sid}/review').json()['items'][0]['practice_available']
    assert client.get(f'/api/v1/learning/sessions/{sid}').json()['exercises'][0]['feedback']['is_correct'] is False
    with sessions() as db:
        assert db.scalar(select(func.count(ExerciseAttempt.id)))==2
        assert db.scalar(select(func.count(ReviewAttempt.id)))==0
        assert db.scalar(select(LessonProgress)).completion_count==0


def test_review_permissions_rechecked_and_empty_level_has_no_invented_errors(interactive):
    client,sessions,lid=interactive;saved=start(client,lid)
    assert client.get('/api/v1/learning/mistakes?level=C2').json()['items']==[]
    with sessions.begin() as db:db.scalar(select(GrammarTopic).where(GrammarTopic.slug=='subject-pronouns-etre')).publication_status='retired'
    assert client.get(f"/api/v1/learning/sessions/{saved['id']}/review").status_code==404
    assert client.post(f"/api/v1/learning/sessions/{saved['id']}/position",headers=_csrf(client),json={'position':1}).status_code==404
    assert client.get('/api/v1/learning/mistakes').json()['items']==[]
