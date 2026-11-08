"""Real M08 PostgreSQL migration, locking and historical-snapshot checks."""
import os,subprocess,sys,json
from pathlib import Path
from uuid import UUID,uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine,select,text,func,inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from app.models import User,UserProfile,UserPreferences,utcnow
from app.security import hash_password
from app.curriculum_models import Exercise,Lesson,GrammarTopic
from app.learning_models import LearningSessionExercise,ExerciseAttempt,LessonProgress
from app.interactive_content import load_pack,import_pack
from app.services import learning_service as learning,daily_learning_service as daily
from app.config import Settings
from test_learning import _import_content
from test_interactive_learning import answer_for

ROOT=Path(__file__).resolve().parents[2]
ADMIN=os.getenv('M08_TEST_ADMIN_DATABASE_URL','')
pytestmark=pytest.mark.skipif(not ADMIN,reason='Requires isolated local PostgreSQL M08 admin URL.')


@pytest.fixture
def database():
    admin_url=make_url(ADMIN);assert admin_url.host in ('127.0.0.1','localhost')
    name='fluentloop_m08_test_'+uuid4().hex[:10]
    admin=create_engine(admin_url,isolation_level='AUTOCOMMIT')
    with admin.connect() as db:db.execute(text(f'CREATE DATABASE "{name}"'))
    url=admin_url.set(database=name).render_as_string(hide_password=False)
    engine=create_engine(url);yield url,engine
    engine.dispose();admin.dispose()


def migrate(url,target,success=True):
    result=subprocess.run([sys.executable,'-m','alembic','downgrade' if target=='-1' else 'upgrade',target],
        cwd=ROOT/'backend',env={**os.environ,'DATABASE_URL':url},capture_output=True,text=True)
    assert (result.returncode==0)==success,result.stderr


def projection(engine,columns):
    with engine.connect() as db:
        return {table:list(db.execute(text(f'''SELECT count(*),md5(coalesce(string_agg(jsonb_build_array({','.join('"'+c+'"' for c in names)})::text,'' ORDER BY jsonb_build_array({','.join('"'+c+'"' for c in names)})::text),'')) FROM "{table}"''')).one()) for table,names in columns.items()}


def test_upgrade_preserves_populated_m07_and_lossy_downgrade_blocked(database,monkeypatch):
    url,engine=database;migrate(url,'head');sessions=sessionmaker(bind=engine)
    _import_content(sessions)
    monkeypatch.setattr('app.services.draft_preview.get_settings',lambda:Settings(_env_file=None,APP_ENV='development',ENABLE_DRAFT_LEARNING_PREVIEW=True))
    with sessions.begin() as db:
        from datetime import timedelta
        from app.models import UserSession
        from app.ai.models import Conversation,Message
        from app.speech.models import SpeechSession,SpeechTurn
        user=User(email=f'preserve-m08-{uuid4().hex}@example.com',role='admin',password_hash=hash_password('IsolatedM08Test2026!'),email_verified_at=utcnow())
        db.add(user);db.flush();uid=user.id
        db.add(UserProfile(user_id=uid,display_name='Preserved synthetic learner'))
        db.add(UserPreferences(user_id=uid))
        db.add(UserSession(user_id=uid,token_hash=uuid4().hex+uuid4().hex,expires_at=utcnow()+timedelta(days=7)))
        conversation=Conversation(user_id=uid,title='Preserved AI memory',mode='roleplay',cefr_level='A1')
        db.add(conversation);db.flush()
        db.add(Message(conversation_id=conversation.id,role='user',content='Bonjour',response_status='success'))
        speech=SpeechSession(user_id=uid,ai_conversation_id=conversation.id,cefr_level='A1')
        db.add(speech);db.flush()
        db.add(SpeechTurn(user_id=uid,speech_session_id=speech.id,request_id=uuid4(),input_checksum='a'*64,
            transcript='Original synthetic recognition',transcription_status='uncertain',status='unusable'))
        lid=db.scalar(select(Lesson.id).where(Lesson.slug=='a1-001'))
    with sessions() as db:
        old,_=learning.start_session(db,user=db.get(User,uid),lesson_id=lid)
        saved=db.get(LearningSessionExercise,old.exercises[0].id).exercise_snapshot
        learning.submit_answer(db,user=db.get(User,uid),session_id=old.id,session_exercise_id=old.exercises[0].id,
            selected_option_id=UUID(saved['correct_option_id']),idempotency_key=uuid4())
    # Back to a genuine pre-M08 schema with only legacy content.
    migrate(url,'-1')
    schema=inspect(engine);columns={t:[c['name'] for c in schema.get_columns(t)] for t in schema.get_table_names() if t!='alembic_version'}
    before=projection(engine,columns);migrate(url,'head')
    assert projection(engine,columns)==before
    with sessions.begin() as db:import_pack(db,load_pack())
    migrate(url,'-1',success=False)
    with engine.connect() as db:assert db.execute(text('SELECT version_num FROM alembic_version')).scalar()=='20261104_0009'


def test_real_pg_concurrent_answers_historical_keys_and_objective_evidence(database,monkeypatch):
    url,engine=database;migrate(url,'head');sessions=sessionmaker(bind=engine,expire_on_commit=False)
    _import_content(sessions)
    monkeypatch.setattr('app.services.draft_preview.get_settings',lambda:Settings(_env_file=None,APP_ENV='development',ENABLE_DRAFT_LEARNING_PREVIEW=True))
    with sessions.begin() as db:
        import_pack(db,load_pack())
        user=User(email=f'm08-{uuid4().hex}@example.com',role='admin',password_hash=hash_password('IsolatedM08Test2026!'),email_verified_at=utcnow())
        db.add(user);db.flush();uid=user.id
        db.add(UserProfile(user_id=uid,display_name='Synthetic learner'));db.add(UserPreferences(user_id=uid));db.flush()
        lesson=db.scalar(select(Lesson).where(Lesson.slug=='m08-etre-interactive-lesson'));lid=lesson.id
    with sessions() as db:session,_=learning.start_session(db,user=db.get(User,uid),lesson_id=lid)
    sid=session.id;first=session.exercises[0];key=uuid4()
    with sessions() as db:saved=db.get(LearningSessionExercise,first.id).exercise_snapshot
    def submit():
        with sessions() as db:return learning.submit_answer(db,user=db.get(User,uid),session_id=sid,session_exercise_id=first.id,
            selected_option_id=UUID(saved['correct_option_id']),idempotency_key=key)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:submit(),range(2)))
    assert sorted(r.idempotent_replay for r in results)==[False,True]
    with sessions() as db:assert db.scalar(select(func.count(ExerciseAttempt.id)))==1
    # A source key change cannot silently change the saved session's key.
    second=session.exercises[1]
    with sessions.begin() as db:
        source=db.get(Exercise,second.exercise_id);source.exercise_data={'accepted_answers':['different future key']}
    with sessions() as db:
        result=learning.submit_answer(db,user=db.get(User,uid),session_id=sid,session_exercise_id=second.id,
            answer_payload={'text_answer':'es'},idempotency_key=uuid4())
        assert result.is_correct
    # A real wrong answer yields objective evidence; no invented grammar labels.
    third=session.exercises[2]
    with sessions() as db:
        stored=db.get(LearningSessionExercise,third.id).exercise_snapshot
        order=list(reversed(stored['accepted_orders'][0]))
        assert not learning.submit_answer(db,user=db.get(User,uid),session_id=sid,session_exercise_id=third.id,
            answer_payload={'tile_ids':order},idempotency_key=uuid4()).is_correct
        recommendations=daily.recommendations(db,db.get(User,uid))
        targeted=[r for r in recommendations if r.get('learning_objective_id')]
        assert targeted and targeted[0]['evidence_attempt_ids']
        assert str(targeted[0]['learning_objective_id'])==stored['learning_objective_id']
    with sessions.begin() as db:db.get(User,uid).role='learner'
    with sessions() as db:
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as error:learning.get_session(db,user=db.get(User,uid),session_id=sid)
        assert error.value.status_code==404
