from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
import pytest
from sqlalchemy import select, func
from app.models import User
from app.config import Settings
from app.study_models import ReviewCard, ReviewAttempt, ReviewItem, DailyPlan, DailyActivity
from app.services import study_clock as clock
from app.services.review_grading_service import grade, normalize
from app.services.review_scheduler import schedule
from test_learning import _register_and_login, _import_content, _set_role, _csrf, _draft_lesson_id

AT=datetime(2026,11,4,12,tzinfo=timezone.utc)

@pytest.fixture
def study(api_client,monkeypatch):
    client,sessions,email=api_client
    monkeypatch.setattr(clock,'now',lambda:AT)
    _register_and_login(client,email,'study@example.com')
    _import_content(sessions)
    return client,sessions,email

def preview(study,monkeypatch):
    client,sessions,_=study
    _set_role(sessions,'study@example.com','admin')
    monkeypatch.setattr('app.services.draft_preview.get_settings',lambda:Settings(_env_file=None,APP_ENV='development',ENABLE_DRAFT_LEARNING_PREVIEW=True))

def post(client,path,payload=None):
    return client.post('/api/v1/'+path,headers=_csrf(client),json=payload)

def plan(client,**kw):
    return post(client,'study/today/generate',{'request_id':str(uuid4()),**kw})

def start(client,limit=3):
    return post(client,'review/sessions',{'request_id':str(uuid4()),'limit':limit})

def answer_key(sessions,item):
    with sessions() as db:
        return db.get(ReviewItem,UUID(item)).snapshot['answers'][0]

@pytest.mark.parametrize('rating',['easy','normal','difficult',None])
@pytest.mark.parametrize('correct',[True,False])
def test_schedule_new_success_failure_and_rating_separation(rating,correct):
    result=schedule(repetitions=0,interval=0,ease=2.5,lapses=0,correct=correct,rating=rating,at=AT)
    assert result['next_due_at']==AT+(timedelta(days=1) if correct else timedelta(minutes=10))
    assert result['state']==('learning' if correct else 'relearning')
    assert result['lapse_count']==(0 if correct else 1)
    assert result['algorithm_version']=='fl-sm2-v1'

@pytest.mark.parametrize('reps,interval,ease,expected',[(1,1,2.5,3),(2,3,2.5,8),(5,300,3,365),(3,1,1.3,1)])
def test_success_interval_boundaries(reps,interval,ease,expected):
    result=schedule(repetitions=reps,interval=interval,ease=ease,lapses=2,correct=True,rating='normal',at=AT)
    assert result['interval_days']==expected and 1.3<=result['ease_factor']<=3

@pytest.mark.parametrize('submitted,expected,result',[("  E\u0301TUDIANT ! ",'étudiant',True),("J’HABITE.","j'habite",True),('ecole','école',False),('bonjours','bonjour',False),('  bonjour  ','bonjour',True),('bonjour???','bonjour',True),('','bonjour',False)])
def test_unicode_accents_whitespace_punctuation_and_no_fuzzy_answers(submitted,expected,result):
    assert grade(submitted,[expected]) is result
    assert grade('salut',['bonjour','salut'])

@pytest.mark.parametrize('name,stamp,day',[('Europe/Paris','2026-03-28T23:30:00+00:00','2026-03-29'),('Europe/Paris','2026-10-25T01:30:00+00:00','2026-10-25'),('America/New_York','2026-11-04T02:00:00+00:00','2026-11-03'),('bad/timezone','2026-11-04T02:00:00+00:00','2026-11-04')])
def test_saved_iana_timezone_dst_and_documented_utc_fallback(name,stamp,day):
    assert clock.study_date(datetime.fromisoformat(stamp),name)[0].isoformat()==day

def test_empty_ordinary_plan_no_draft_no_fabrication_and_offline_independence(study,monkeypatch):
    client,sessions,_=study
    from app.ai.providers.ollama_provider import OllamaProvider
    def offline(*args,**kw):raise AssertionError('Planner must not contact Ollama')
    monkeypatch.setattr(OllamaProvider,'health',offline)
    monkeypatch.setattr(OllamaProvider,'generate',offline)
    response=plan(client)
    assert response.status_code==200,response.text
    saved=response.json()
    assert saved['target_minutes']==15 and saved['planned_minutes']==15
    assert {a['activity_type'] for a in saved['activities']}=={'tutor','speaking'}
    assert all(not a['draft_preview'] and 'mistake' not in a['reason'] for a in saved['activities'])
    assert client.get('/api/v1/study/today').json()['id']==saved['id']
    assert plan(client).json()['id']==saved['id']
    assert client.get('/api/v1/review/due').json()['available_vocabulary_count']==0
    assert start(client).status_code==409
    assert 'no-store' in response.headers['cache-control']
    with sessions() as db:
        assert db.scalar(select(func.count(ReviewCard.id)))==0
        assert db.scalar(select(func.count(DailyPlan.id)))==1

@pytest.mark.parametrize('level',['a1','a2','b1','b2','c1','c2'])
def test_exact_six_levels_saved_target_and_level_history(study,level):
    client,sessions,_=study
    first=plan(client).json()
    assert client.patch('/api/v1/users/me/preferences',headers=_csrf(client),json={'current_level':level,'daily_study_minutes':20}).status_code==200
    new=plan(client).json()
    assert new['cefr_level']==level.upper()
    assert new['target_minutes']==(15 if level=='a1' else 20)  # same-day persisted target
    assert client.get('/api/v1/study/plans/'+first['id']).status_code==200
    assert client.patch('/api/v1/users/me/preferences',headers=_csrf(client),json={'current_level':'a0'}).status_code==422

def test_target_default_and_explicit_unstarted_regeneration_policy(study):
    client,_,_=study
    first=plan(client).json()
    client.patch('/api/v1/users/me/preferences',headers=_csrf(client),json={'daily_study_minutes':30})
    assert plan(client).json()['target_minutes']==15
    request={'request_id':str(uuid4()),'regenerate':True}
    regenerated=post(client,'study/today/generate',request)
    assert regenerated.status_code==200,regenerated.text
    assert regenerated.json()['generation']==2 and regenerated.json()['target_minutes']==30
    assert regenerated.json()['planned_minutes']==20  # honest two real practice tasks capped at ten minutes
    assert post(client,'study/today/generate',request).json()['generation']==2
    aid=regenerated.json()['activities'][0]['id']
    assert post(client,'study/activities/'+aid+'/complete').status_code==409
    opened=post(client,'study/activities/'+aid+'/start')
    assert opened.status_code==200,opened.text
    assert post(client,'study/activities/'+aid+'/start').json()['url']==opened.json()['url']
    assert plan(client,regenerate=True).status_code==409
    assert client.get('/api/v1/study/today').json()['activities'][0]['status']=='in_progress'

def test_review_persistence_idempotence_rating_and_no_answer_leak(study,monkeypatch):
    preview(study,monkeypatch)
    client,sessions,_=study
    session=start(client).json()
    sid=session['id']
    assert session['total_cards']==3
    with sessions() as db:
        from app.curriculum_models import WordSense,Lexeme
        card=db.get(ReviewCard,UUID(session['current_question']['card_id']))
        sense=db.get(WordSense,card.word_sense_id)
        assert db.get(Lexeme,sense.lexeme_id).lemma=='bonjour'
    assert session['current_question']['draft_preview'] is True
    assert 'answers' not in str(session) and 'correct_answer' not in str(session)
    assert post(client,'review/sessions/'+sid+'/complete').status_code==409
    for n in range(3):
        question=client.get('/api/v1/review/sessions/'+sid).json()['current_question']
        payload={'request_id':str(uuid4()),'item_id':question['item_id'],'answer':answer_key(sessions,question['item_id']) if n!=1 else 'definitely wrong','recall_rating':'easy'}
        result=post(client,'review/sessions/'+sid+'/answers',payload)
        assert result.status_code==200,result.text
        assert result.json()['is_correct'] is (n!=1)
        assert post(client,'review/sessions/'+sid+'/answers',payload).json()['id']==result.json()['id']
        assert post(client,'review/sessions/'+sid+'/answers',{**payload,'request_id':str(uuid4())}).status_code==409
        assert post(client,'review/sessions/'+sid+'/answers',{**payload,'answer':'changed'}).status_code==409
    assert post(client,'review/sessions/'+sid+'/complete').json()['status']=='completed'
    with sessions() as db:
        assert db.scalar(select(func.count(ReviewAttempt.id)))==3
        cards=db.scalars(select(ReviewCard)).all()
        assert sorted(c.repetition_count for c in cards)==[0,1,1]
        assert sorted(c.lapse_count for c in cards)==[0,0,1]
    assert client.get('/api/v1/review/progress').json()=={'reviews_completed':3,'cards_due':0,'vocabulary_items_studied':3}
    assert len(client.get('/api/v1/review/history').json()['items'])==3
    monkeypatch.setattr(clock,'now',lambda:AT+timedelta(minutes=11))
    assert client.get('/api/v1/review/due').json()['due_count']==1
    assert client.get('/api/v1/study/recommendations').json()[0]['priority']==100

def test_review_plan_completion_and_revocation_preserve_history(study,monkeypatch):
    preview(study,monkeypatch)
    client,sessions,_=study
    saved=plan(client).json()
    activity=next(a for a in saved['activities'] if a['activity_type']=='vocabulary_review')
    opened=post(client,'study/activities/'+activity['id']+'/start').json()
    sid=opened['url'].split('/')[-1]
    question=client.get('/api/v1/review/sessions/'+sid).json()['current_question']
    response=post(client,'review/sessions/'+sid+'/answers',{'item_id':question['item_id'],'answer':answer_key(sessions,question['item_id']),'request_id':str(uuid4())})
    assert response.status_code==200,response.text
    preview_settings=Settings(_env_file=None,APP_ENV='production',COOKIE_SECURE=True,ENABLE_DRAFT_LEARNING_PREVIEW=True)
    monkeypatch.setattr('app.services.draft_preview.get_settings',lambda:preview_settings)
    hidden=client.get('/api/v1/study/today').json()
    assert all(not a['draft_preview'] for a in hidden['activities'])
    assert hidden['unavailable_activity_count']>0
    assert client.get('/api/v1/review/sessions/'+sid).json()['current_question'] is None
    assert client.get('/api/v1/review/sessions/'+sid).json()['feedback']==[]
    assert post(client,'review/sessions/'+sid+'/answers',{'item_id':question['item_id'],'answer':'guess','request_id':str(uuid4())}).status_code==404
    assert post(client,'study/activities/'+activity['id']+'/start').status_code==404
    assert client.get('/api/v1/review/due').json()['due_count']==0
    assert len(client.get('/api/v1/review/history').json()['items'])==1
    assert post(client,'review/sessions/'+sid+'/complete').status_code==200
    with sessions() as db:
        assert db.scalar(select(func.count(ReviewAttempt.id)))==1
        assert db.scalar(select(func.count(ReviewCard.id)))==3

def test_user_isolation_csrf_and_strict_payloads(study,monkeypatch):
    preview(study,monkeypatch)
    client,sessions,email=study
    saved=plan(client).json()
    session=start(client).json()
    assert client.post('/api/v1/study/today/generate',json={'request_id':str(uuid4())}).status_code==403
    assert post(client,'study/today/generate',{'request_id':str(uuid4()),'user_id':str(uuid4())}).status_code==422
    assert post(client,'review/sessions',{'request_id':str(uuid4()),'limit':21}).status_code==422
    post(client,'auth/logout')
    _register_and_login(client,email,'other-study@example.com')
    assert client.get('/api/v1/study/plans/'+saved['id']).status_code==404
    assert client.get('/api/v1/review/sessions/'+session['id']).status_code==404
    assert post(client,'study/activities/'+saved['activities'][0]['id']+'/start').status_code==404
    assert post(client,'review/sessions/'+session['id']+'/answers',{'request_id':str(uuid4()),'item_id':session['current_question']['item_id'],'answer':'bonjour'}).status_code==404
    assert client.get('/api/v1/review/history').json()['items']==[]

def test_due_views_do_not_schedule_and_invalid_answer_fields_are_rejected(study,monkeypatch):
    preview(study,monkeypatch)
    client,sessions,_=study
    saved=start(client).json();question=saved['current_question']
    with sessions() as db:
        card=db.get(ReviewCard,UUID(question['card_id']));before=(card.next_due_at,card.repetition_count,card.last_reviewed_at)
    for _ in range(2):
        assert client.get('/api/v1/review/due').status_code==200
        assert client.get('/api/v1/review/sessions/'+saved['id']).status_code==200
    with sessions() as db:
        card=db.get(ReviewCard,UUID(question['card_id']));assert (card.next_due_at,card.repetition_count,card.last_reviewed_at)==before
    valid={'request_id':str(uuid4()),'item_id':question['item_id'],'answer':'bonjour'}
    for extra in ({'is_correct':True},{'recall_rating':'perfect'},{'answer':'\u0000'},{'answer':'   '}):
        assert post(client,'review/sessions/'+saved['id']+'/answers',{**valid,**extra}).status_code==422

def test_saved_plan_date_and_timezone_across_midnight_and_dst(study,monkeypatch):
    client,sessions,_=study
    with sessions.begin() as db:
        user=db.scalar(select(User).where(User.email=='study@example.com'))
        user.profile.timezone='Europe/Paris'
    monkeypatch.setattr(clock,'now',lambda:datetime(2026,10,25,0,30,tzinfo=timezone.utc))
    first=plan(client).json()
    assert first['timezone_name']=='Europe/Paris' and first['local_study_date']=='2026-10-25'
    monkeypatch.setattr(clock,'now',lambda:datetime(2026,10,25,1,30,tzinfo=timezone.utc))
    assert client.get('/api/v1/study/today').json()['id']==first['id']
    monkeypatch.setattr(clock,'now',lambda:datetime(2026,10,25,23,30,tzinfo=timezone.utc))
    assert client.get('/api/v1/study/today').json() is None
    second=plan(client).json()
    assert second['local_study_date']=='2026-10-26' and second['id']!=first['id']

def test_goal_and_focus_influence_practice_without_changing_level(study):
    client,sessions,_=study
    with sessions.begin() as db:
        user=db.scalar(select(User).where(User.email=='study@example.com'))
        user.profile.learning_goal='Daily conversations'
    assert client.get('/api/v1/study/recommendations').json()[0]['activity_type']=='speaking'
    client.patch('/api/v1/users/me/preferences',headers=_csrf(client),json={'learning_focus':'writing'})
    assert client.get('/api/v1/study/recommendations').json()[0]['activity_type']=='tutor'
    assert client.get('/api/v1/users/me/preferences').json()['current_level']=='a1'

def test_equivalent_answers_come_only_from_currently_authorized_records(study,monkeypatch):
    from app.services.study_content import vocabulary
    from app.curriculum_models import Translation
    preview(study,monkeypatch)
    client,sessions,_=study
    with sessions.begin() as db:
        rows=db.scalars(select(Translation).where(Translation.language_code=='en').order_by(Translation.id).limit(2)).all()
        rows[0].translated_text='shared test meaning';rows[1].translated_text='shared test meaning'
    with sessions() as db:
        user=db.scalar(select(User).where(User.email=='study@example.com'))
        shared=[v for v in vocabulary(db,user,'A1').values() if v['prompt']=='Write in French: shared test meaning']
        assert len(shared)==2 and set(shared[0]['answers'])==set(shared[1]['answers'])
        assert all(grade(key,shared[0]['answers']) for key in shared[1]['answers'])
    _set_role(sessions,'study@example.com','learner')
    assert client.get('/api/v1/review/due').json()['available_vocabulary_count']==0

def test_recommendations_use_only_actual_lesson_mistakes_and_unfinished_progress(study,monkeypatch):
    preview(study,monkeypatch)
    client,sessions,_=study
    lesson=_draft_lesson_id(sessions)
    response=post(client,'learning/sessions',{'lesson_id':str(lesson)})
    assert response.status_code==201,response.text
    saved=response.json()
    first=saved['exercises'][0]
    from app.learning_models import LearningSessionExercise
    with sessions() as db:
        snapshot=db.get(LearningSessionExercise,UUID(first['id'])).exercise_snapshot
        wrong=next(o['id'] for o in snapshot['options'] if o['id']!=snapshot['correct_option_id'])
    submitted=post(client,'learning/sessions/'+saved['id']+'/answers',{'session_exercise_id':first['id'],'selected_option_id':wrong,'idempotency_key':str(uuid4())})
    assert submitted.status_code==200,submitted.text
    recommendations=client.get('/api/v1/study/recommendations').json()
    assert recommendations[0]['activity_type']=='continue_lesson'
    weakness=next(r for r in recommendations if r['activity_type']=='lesson_review')
    assert weakness['lesson_id']==str(lesson) and len(weakness['evidence_attempt_ids'])==1
    assert '1 recorded incorrect' in weakness['reason']
    assert all(r['activity_type']!='grammar_review' for r in recommendations)
    planned=plan(client).json()
    assert planned['activities'][0]['activity_type']=='continue_lesson'

def test_a_later_correct_attempt_resolves_a_prior_mistake_without_overwriting_history(study,monkeypatch):
    from app.learning_models import LearningSession,LearningSessionExercise,ExerciseAttempt
    from app.services import learning_service
    preview(study,monkeypatch)
    client,sessions,_=study
    lesson=_draft_lesson_id(sessions)
    monkeypatch.setattr(learning_service,'_now',lambda:AT)
    first=post(client,'learning/sessions',{'lesson_id':str(lesson)}).json()
    question=first['exercises'][0]
    with sessions() as db:
        snapshot=db.get(LearningSessionExercise,UUID(question['id'])).exercise_snapshot
        correct=snapshot['correct_option_id']
        wrong=next(o['id'] for o in snapshot['options'] if o['id']!=correct)
    assert post(client,'learning/sessions/'+first['id']+'/answers',{'session_exercise_id':question['id'],'selected_option_id':wrong,'idempotency_key':str(uuid4())}).status_code==200
    assert any(r['activity_type']=='lesson_review' for r in client.get('/api/v1/study/recommendations').json())
    with sessions.begin() as db:
        db.get(LearningSession,UUID(first['id'])).status='abandoned'  # isolated retake fixture
    monkeypatch.setattr(learning_service,'_now',lambda:AT+timedelta(minutes=1))
    second=post(client,'learning/sessions',{'lesson_id':str(lesson)}).json()
    assert post(client,'learning/sessions/'+second['id']+'/answers',{'session_exercise_id':second['exercises'][0]['id'],'selected_option_id':correct,'idempotency_key':str(uuid4())}).status_code==200
    assert all(r['activity_type']!='lesson_review' for r in client.get('/api/v1/study/recommendations').json())
    with sessions() as db:
        assert db.scalar(select(func.count(ExerciseAttempt.id)))==2
        assert db.scalar(select(func.count(ExerciseAttempt.id)).where(ExerciseAttempt.is_correct.is_(False)))==1

def test_linked_review_completion_updates_saved_plan_and_not_navigation(study,monkeypatch):
    preview(study,monkeypatch)
    client,sessions,_=study
    saved=plan(client).json()
    aid=next(a['id'] for a in saved['activities'] if a['activity_type']=='vocabulary_review')
    opened=post(client,'study/activities/'+aid+'/start').json()
    sid=opened['url'].split('/')[-1]
    assert client.get('/api/v1/study/today').json()['status']=='in_progress'
    for _ in range(3):
        question=client.get('/api/v1/review/sessions/'+sid).json()['current_question']
        assert post(client,'review/sessions/'+sid+'/answers',{'request_id':str(uuid4()),'item_id':question['item_id'],'answer':answer_key(sessions,question['item_id'])}).status_code==200
    assert post(client,'review/sessions/'+sid+'/complete').status_code==200
    updated=client.get('/api/v1/study/today').json()
    assert next(a for a in updated['activities'] if a['id']==aid)['status']=='completed'
    assert updated['status']=='in_progress'  # other real activities still pending
    assert post(client,'study/activities/'+aid+'/complete').status_code==200

def test_tutor_and_speaking_require_successful_linked_interactions(study):
    from app.ai.models import Conversation, Message
    from app.speech.models import SpeechTurn
    client,sessions,_=study
    saved=plan(client).json()
    for activity in saved['activities']:
        opened=post(client,'study/activities/'+activity['id']+'/start').json()
        assert post(client,'study/activities/'+activity['id']+'/complete').status_code==409
        with sessions.begin() as db:
            user=db.scalar(select(User).where(User.email=='study@example.com'))
            if activity['activity_type']=='tutor':
                cid=UUID(opened['url'].split('/')[-1])
                db.add(Message(conversation_id=cid,role='assistant',content='Bonjour !',response_status='failed',created_at=AT+timedelta(seconds=1)))
            else:
                sid=UUID(opened['url'].split('/')[-1])
                db.add(SpeechTurn(user_id=user.id,speech_session_id=sid,request_id=uuid4(),input_checksum='a'*64,
                    transcript='',transcription_status='no_speech',status='unusable',created_at=AT+timedelta(seconds=1)))
        assert post(client,'study/activities/'+activity['id']+'/complete').status_code==409
        with sessions.begin() as db:
            if activity['activity_type']=='tutor':
                db.add(Message(conversation_id=cid,role='user',content='Bonjour',response_status='success',created_at=AT+timedelta(seconds=2)))
                db.add(Message(conversation_id=cid,role='assistant',content='Bonjour !',response_status='success',created_at=AT+timedelta(seconds=3)))
            else:
                db.add(SpeechTurn(user_id=user.id,speech_session_id=sid,request_id=uuid4(),input_checksum='b'*64,
                    transcript='Bonjour',transcription_status='transcribed',status='success',created_at=AT+timedelta(seconds=3)))
        assert post(client,'study/activities/'+activity['id']+'/complete').status_code==200
    assert client.get('/api/v1/study/today').json()['status']=='completed'
