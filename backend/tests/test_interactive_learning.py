"""M08 API/SQLite regressions; PostgreSQL checks run separately."""
from uuid import UUID,uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import select,func
from app.config import Settings
from app.curriculum_models import Lesson,Exercise,ExerciseOption,GrammarTopic
from app.learning_models import ExerciseAttempt,LessonProgress,LearningSessionExercise
from app.interactive_content import load_pack,import_pack
from app.services.grading_service import grade_saved,normalize_written
from app.services.email import get_email_service
from test_learning import _register_and_login,_csrf,_import_content,_set_role


@pytest.fixture
def interactive(api_client,monkeypatch):
    client,sessions,emails=api_client
    _register_and_login(client,emails,'interactive@example.com')
    _set_role(sessions,'interactive@example.com','admin')
    monkeypatch.setattr('app.services.draft_preview.get_settings',lambda:Settings(_env_file=None,APP_ENV='development',ENABLE_DRAFT_LEARNING_PREVIEW=True))
    _import_content(sessions)
    with sessions.begin() as db:
        import_pack(db,load_pack())
        lesson=db.scalar(select(Lesson).where(Lesson.slug=='m08-etre-interactive-lesson'))
        lid=str(lesson.id)
    return client,sessions,lid


def start(client,lid):
    response=client.post('/api/v1/learning/sessions',headers=_csrf(client),json={'lesson_id':lid})
    assert response.status_code in (200,201),response.text
    return response.json()


def answer_for(saved):
    if saved['type'] in ('multiple_choice','listening'):return {'selected_option_id':saved['correct_option_id']}
    if saved['type'] in ('fill_blank','short_answer'):return {'text_answer':saved['accepted_answers'][-1]}
    if saved['type']=='sentence_order':return {'tile_ids':saved['accepted_orders'][0]}
    return {'matches':saved['answer_pairs']}


def test_six_formats_snapshots_idempotency_resume_and_completion(interactive):
    client,sessions,lid=interactive
    first=start(client,lid);sid=first['id']
    assert len(first['exercises'])==6
    assert not any(key in str(first) for key in ('accepted_answers','correct_option_id','accepted_orders','answer_pairs','text_fr'))
    with sessions() as db:
        frozen={str(s.id):s.exercise_snapshot for s in db.scalars(select(LearningSessionExercise).where(LearningSessionExercise.learning_session_id==UUID(sid)))}
    for exercise in first['exercises']:
        payload={'session_exercise_id':exercise['id'],'idempotency_key':str(uuid4()),**answer_for(frozen[exercise['id']])}
        response=client.post(f'/api/v1/learning/sessions/{sid}/answers',headers=_csrf(client),json=payload)
        assert response.status_code==200,response.text
        assert response.json()['is_correct']
        retry=client.post(f'/api/v1/learning/sessions/{sid}/answers',headers=_csrf(client),json=payload)
        assert retry.status_code==200 and retry.json()['idempotent_replay'] is True
        assert retry.json()['score_points']==response.json()['score_points']
        resumed=client.post(f'/api/v1/learning/sessions/{sid}/resume',headers=_csrf(client)).json()
        assert resumed['exercises'][exercise['exercise_order']-1]['answered']
        assert resumed['exercises'][exercise['exercise_order']-1]['submitted_answer']==answer_for(frozen[exercise['id']])
    completed=client.post(f'/api/v1/learning/sessions/{sid}/complete',headers=_csrf(client))
    assert completed.status_code==200 and completed.json()['percentage']==100
    with sessions() as db:
        assert db.scalar(select(func.count(ExerciseAttempt.id)))==6
        assert db.scalar(select(LessonProgress)).status=='completed'


def test_import_idempotency_and_authorized_grammar(interactive):
    client,sessions,lid=interactive
    with sessions.begin() as db:
        before=db.scalar(select(func.count(Exercise.id)))
        result=import_pack(db,load_pack())
        assert result['inserted']==0 and result['updated']==0
        assert db.scalar(select(func.count(Exercise.id)))==before
    grammar=client.get('/api/v1/learning/grammar').json()
    topic=next(t for t in grammar['items'] if t['teaching'])
    assert topic['teaching']['independent_human_review'] is False
    assert topic['objectives'] and topic['rules']
    assert client.get('/api/v1/learning/library?level=A0').status_code==422
    assert client.get('/api/v1/learning/library?level=C2').json()['items']==[]


def test_practice_does_not_complete_lesson_or_create_review_cards(interactive):
    client,sessions,lid=interactive
    result=client.post('/api/v1/learning/practice/sessions',headers=_csrf(client),json={'category':'sentence_building','lesson_id':lid})
    assert result.status_code==200,result.text
    session=result.json();exercise=session['exercises'][0]
    with sessions() as db:saved=db.get(LearningSessionExercise,UUID(exercise['id'])).exercise_snapshot
    assert client.post(f"/api/v1/learning/sessions/{session['id']}/answers",headers=_csrf(client),json={'session_exercise_id':exercise['id'],'idempotency_key':str(uuid4()),**answer_for(saved)}).status_code==200
    completed=client.post(f"/api/v1/learning/sessions/{session['id']}/complete",headers=_csrf(client))
    assert completed.status_code==200 and completed.json()['activity_key'].startswith('practice:')
    with sessions() as db:assert db.scalar(select(func.count(LessonProgress.id)))==0
    assert start(client,lid)['activity_key']=='lesson'


def test_permissions_rechecked_for_audio_resume_and_submit(interactive,monkeypatch):
    client,sessions,lid=interactive
    session=start(client,lid);sid=session['id'];listening=session['exercises'][4]
    calls=[]
    class Speech:
        def synthesize(self,text):calls.append(text);return b'RIFF'+b'\0'*40
    monkeypatch.setattr('app.speech.providers.get_speech_provider',lambda:Speech())
    path=f"/api/v1/learning/sessions/{sid}/exercises/{listening['id']}/audio"
    assert client.post(path,headers=_csrf(client)).status_code==200
    assert calls==['Elle est ici.']
    _set_role(sessions,'interactive@example.com','learner')
    assert client.get('/api/v1/learning/grammar').json()['items']==[]
    assert client.get('/api/v1/learning/library').json()['items']==[]
    assert client.post(path,headers=_csrf(client)).status_code==404
    assert client.post(f'/api/v1/learning/sessions/{sid}/resume',headers=_csrf(client)).status_code==404
    assert client.post('/api/v1/learning/practice/sessions',headers=_csrf(client),json={'category':'grammar'}).status_code==409
    assert len(calls)==1


@pytest.mark.parametrize('answer,expected',[(" JE  SUIS E\u0301TUDIANT. ",True),("je suis étudiant",True),("Je suis etudiant.",False),("Je es étudiant.",False)])
def test_written_accents_and_variants(answer,expected):
    saved={'type':'short_answer','accepted_answers':['Je suis étudiant.','Je suis étudiante.']}
    assert grade_saved(saved,{'text_answer':answer})[0] is expected


@pytest.mark.parametrize('kind',['sentence_order','matching'])
def test_incomplete_stable_identifiers_rejected(kind):
    data=next(e for e in load_pack().exercises if e.type==kind).data
    with pytest.raises(HTTPException) as error:
        grade_saved({'type':kind,**data},{'tile_ids':[]} if kind=='sentence_order' else {'matches':{}})
    assert error.value.status_code==422


def test_other_owner_cannot_read_grade_resume_or_play_audio(interactive):
    client,sessions,lid=interactive
    saved=start(client,lid);sid=saved['id'];eid=saved['exercises'][0]['id']
    _register_and_login(client,client.app.dependency_overrides[get_email_service](),'other-owner@example.com')
    _set_role(sessions,'other-owner@example.com','admin')
    assert client.get(f'/api/v1/learning/sessions/{sid}').status_code==404
    assert client.post(f'/api/v1/learning/sessions/{sid}/resume',headers=_csrf(client)).status_code==404
    assert client.post(f'/api/v1/learning/sessions/{sid}/answers',headers=_csrf(client),json={'session_exercise_id':eid,'text_answer':'es','idempotency_key':str(uuid4())}).status_code==404
    assert client.post(f"/api/v1/learning/sessions/{sid}/exercises/{saved['exercises'][4]['id']}/audio",headers=_csrf(client)).status_code==404


def test_invalid_payload_shapes_and_wrong_exercise_format(interactive):
    client,sessions,lid=interactive;saved=start(client,lid);exercise=saved['exercises'][0]
    path=f"/api/v1/learning/sessions/{saved['id']}/answers"
    for answer in ({},{'text_answer':'es','tile_ids':[str(uuid4())]},{'text_answer':'es'},{'matches':{'not-a-uuid':'also-invalid'}}):
        result=client.post(path,headers=_csrf(client),json={'session_exercise_id':exercise['id'],'idempotency_key':str(uuid4()),**answer})
        assert result.status_code==422
    assert client.get(f"/api/v1/learning/sessions/{saved['id']}").json()['answered_exercises']==0
    # Backfilling a current source objective must not turn an old unmapped
    # snapshot into invented objective-specific error evidence.
    with sessions.begin() as db:
        snapshot=db.get(LearningSessionExercise,UUID(exercise['id']))
        snapshot.exercise_snapshot={**snapshot.exercise_snapshot,'learning_objective_id':None}
        wrong=next(o['id'] for o in snapshot.exercise_snapshot['options'] if o['id']!=snapshot.exercise_snapshot['correct_option_id'])
    result=client.post(path,headers=_csrf(client),json={'session_exercise_id':exercise['id'],'idempotency_key':str(uuid4()),'selected_option_id':wrong})
    assert result.status_code==200 and not result.json()['is_correct']
    from app.services.daily_learning_service import recommendations
    from app.models import User
    with sessions() as db:
        rows=recommendations(db,db.scalar(select(User).where(User.email=='interactive@example.com')))
        assert any(r['activity_type']=='lesson_review' for r in rows)
        assert not any(r.get('learning_objective_id') for r in rows)


def test_retired_grammar_blocks_existing_snapshot_and_exercise_catalog(interactive):
    client,sessions,lid=interactive;saved=start(client,lid)
    with sessions.begin() as db:db.scalar(select(GrammarTopic).where(GrammarTopic.slug=='subject-pronouns-etre')).publication_status='retired'
    assert client.get(f"/api/v1/learning/sessions/{saved['id']}").status_code==404
    assert client.get('/api/v1/learning/sessions').json()['items']==[]
    assert client.get(f'/api/v1/lessons/{lid}/exercises').json()['items']==[]


def test_listening_unavailable_keeps_activity_unanswered(interactive,monkeypatch):
    from app.speech.asr_provider import SpeechUnavailable
    client,_,lid=interactive;saved=start(client,lid)
    class Offline:
        def synthesize(self,text):raise SpeechUnavailable()
    monkeypatch.setattr('app.speech.providers.get_speech_provider',lambda:Offline())
    response=client.post(f"/api/v1/learning/sessions/{saved['id']}/exercises/{saved['exercises'][4]['id']}/audio",headers=_csrf(client))
    assert response.status_code==503
    assert client.get(f"/api/v1/learning/sessions/{saved['id']}").json()['answered_exercises']==0
