"""Real PostgreSQL only; creates fresh isolated m07 databases, never app DBs."""
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4, UUID
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.main import app
from app.core.database import get_db
from app.models import User, UserProfile, UserPreferences, UserSession
from app.security import hash_password
from app.services.email import get_email_service
from app.study_models import DailyPlan, ReviewCard, ReviewAttempt, ReviewItem, ReviewSession
from app.services import daily_learning_service as plans, spaced_repetition_service as reviews, study_clock as clock
from app.study_schemas import GeneratePlan, StartReview, AnswerReview
from app.config import Settings
from conftest import CapturedEmailService, IsolatedRateLimitRedis
from test_learning import _register_and_login, _import_content, _set_role, _csrf

ROOT=Path(__file__).resolve().parents[2]
ADMIN=os.getenv('STUDY_TEST_ADMIN_DATABASE_URL','')
pytestmark=pytest.mark.skipif(not ADMIN,reason='Set STUDY_TEST_ADMIN_DATABASE_URL to local postgres admin URL; only creates fluentloop_m07_* databases.')
AT=datetime(2026,11,4,12,tzinfo=timezone.utc)

def migrate(url,target):
    env={**os.environ,'DATABASE_URL':url}
    run=subprocess.run([sys.executable,'-m','alembic','upgrade' if target!='-1' else 'downgrade',target],cwd=ROOT/'backend',env=env,capture_output=True,text=True)
    assert run.returncode==0,run.stderr

def fingerprint(engine,names=None):
    from sqlalchemy import inspect
    names=names or [n for n in inspect(engine).get_table_names() if n!='alembic_version']
    with engine.connect() as db:
        return {name:list(db.execute(text(f"SELECT count(*),md5(coalesce(string_agg(to_jsonb(t)::text,'' ORDER BY to_jsonb(t)::text),'')) FROM \"{name}\" t")).one()) for name in names}

@pytest.fixture
def database():
    url=make_url(ADMIN)
    assert url.host in ('127.0.0.1','localhost')
    name='fluentloop_m07_'+uuid4().hex[:10]
    admin=create_engine(url,isolation_level='AUTOCOMMIT')
    with admin.connect() as db:
        db.execute(text(f'CREATE DATABASE "{name}"'))
    target=url.set(database=name).render_as_string(hide_password=False)
    engine=create_engine(target)
    yield target,engine
    # Keep the explicitly isolated database for inspection; never drop app DBs.
    engine.dispose();admin.dispose()

def test_fresh_upgrade_and_populated_rollback_preserve_preexisting_rows(database):
    url,engine=database
    # Seed with the current ORM, then remove empty M08 columns before the
    # original M07 preservation check. No structured M08 data is discarded.
    migrate(url,'head')
    sessions=sessionmaker(bind=engine)
    _import_content(sessions)
    for _ in range(3):migrate(url,'-1')
    with sessions.begin() as db:
        user=User(email=f'migration-{uuid4().hex[:8]}@example.com',password_hash=hash_password('IsolatedMigrationPass2026!'),role='learner',email_verified_at=AT)
        db.add(user);db.flush()
        db.add(UserProfile(user_id=user.id,display_name='Preserve existing learner'))
        db.execute(UserPreferences.__table__.insert().values(
            user_id=user.id,current_level='b2',daily_study_minutes=20))
        # Representative synthetic pre-M07 state, including a live auth session,
        # lesson progress, AI memory and immutable uncertain speech history.
        from datetime import timedelta
        from app.curriculum_models import Lesson
        from app.learning_models import LearningSession,LessonProgress
        from app.ai.models import Conversation,Message
        from app.speech.models import SpeechSession,SpeechTurn
        db.add(UserSession(user_id=user.id,token_hash=uuid4().hex+uuid4().hex,expires_at=AT+timedelta(days=14)))
        lesson=db.scalar(select(Lesson).where(Lesson.slug=='a1-001'))
        db.execute(text("""INSERT INTO learning_sessions (id,user_id,lesson_id,lesson_content_version,cefr_level,
            status,preview_mode,lesson_snapshot,total_exercises,max_score_points,score_points,current_section_position,
            current_exercise_position,started_at,last_activity_at) VALUES (:id,:uid,:lid,:version,'A1','in_progress',true,
            CAST(:snapshot AS jsonb),0,0,0,0,0,:at,:at)"""),dict(id=uuid4(),uid=user.id,lid=lesson.id,
            version=lesson.content_version,snapshot=json.dumps({'title':lesson.title,'fixture':'migration preservation'}),at=AT))
        db.add(LessonProgress(user_id=user.id,lesson_id=lesson.id,cefr_level='A1',status='in_progress'))
        conversation_id=uuid4()
        db.execute(Conversation.__table__.insert().values(
            id=conversation_id,user_id=user.id,title='Preserved test memory',mode='roleplay',cefr_level='B2'))
        db.add(Message(conversation_id=conversation_id,role='user',content='Bonjour',response_status='success'))
        speech=SpeechSession(user_id=user.id,ai_conversation_id=conversation_id,cefr_level='B2')
        db.add(speech);db.flush()
        db.add(SpeechTurn(user_id=user.id,speech_session_id=speech.id,request_id=uuid4(),input_checksum='a'*64,
            transcript='Bonjour, original reconnu.',transcription_status='uncertain',status='unusable'))
    before=fingerprint(engine)
    migrate(url,'20261104_0008')
    assert fingerprint(engine,list(before))==before
    with engine.connect() as db:
        assert db.execute(text('SELECT version_num FROM alembic_version')).scalar()=='20261104_0008'
    migrate(url,'-1')
    assert fingerprint(engine)==before
    migrate(url,'20261104_0008')
    assert fingerprint(engine,list(before))==before
    # A completely empty database upgraded straight to head is covered below
    # by the independent integration fixture's migration.

def test_postgres_transactions_concurrency_isolation_and_restart(database,monkeypatch,tmp_path):
    url,engine=database
    migrate(url,'head')
    sessions=sessionmaker(bind=engine,expire_on_commit=False)
    _import_content(sessions)
    monkeypatch.setattr(clock,'now',lambda:AT)
    monkeypatch.setattr('app.services.draft_preview.get_settings',lambda:Settings(_env_file=None,APP_ENV='development',ENABLE_DRAFT_LEARNING_PREVIEW=True))
    monkeypatch.setattr('app.services.rate_limit.redis_client',IsolatedRateLimitRedis())
    email=CapturedEmailService()
    def db_dep():
        with sessions() as db:yield db
    app.dependency_overrides[get_db]=db_dep
    app.dependency_overrides[get_email_service]=lambda:email
    account='study-pg-'+uuid4().hex[:10]+'@example.com'
    try:
        with TestClient(app,headers={'Origin':'http://localhost:3000'}) as client:
            _register_and_login(client,email,account)
            _set_role(sessions,account,'admin')
            with sessions() as db:uid=db.scalar(select(User.id).where(User.email==account))
            def generate():
                with sessions() as db:return plans.generate(db,db.get(User,uid),GeneratePlan(request_id=uuid4()))['id']
            with ThreadPoolExecutor(max_workers=2) as pool:
                result=list(pool.map(lambda _:generate(),range(2)))
            assert result[0]==result[1]
            with sessions() as db:
                assert db.scalar(select(func.count(DailyPlan.id)).where(DailyPlan.user_id==uid))==1
                user=db.get(User,uid)
                session=reviews.start(db,user,StartReview(request_id=uuid4(),limit=3))
                item=session['current_question']['item_id']
                key=db.get(ReviewItem,item).snapshot['answers'][0]
            sid=session['id']
            payload=AnswerReview(request_id=uuid4(),item_id=item,answer=key,recall_rating='normal')
            def submit():
                with sessions() as db:return reviews.submit(db,db.get(User,uid),sid,payload)
            with ThreadPoolExecutor(max_workers=2) as pool:
                attempts=list(pool.map(lambda _:submit(),range(2)))
            assert attempts[0]['id']==attempts[1]['id']
            with sessions() as db:
                assert db.scalar(select(func.count(ReviewAttempt.id)))==1
                first=db.get(ReviewItem,item)
                card=db.get(ReviewCard,first.card_id)
                assert card.repetition_count==1 and clock.utc(card.next_due_at).date().isoformat()=='2026-11-05'
                # Enforce uniqueness and owner consistency at the database layer.
                duplicate=ReviewCard(user_id=uid,word_sense_id=card.word_sense_id,cefr_level=card.cefr_level,
                    card_content_version=card.card_content_version,next_due_at=AT)
                db.add(duplicate)
                with pytest.raises(IntegrityError):db.commit()
                db.rollback()
            # A simulated storage failure must roll back both scheduling and attempt.
            with sessions() as db:
                nextq=reviews.view(db,db.get(User,uid),db.get(ReviewSession,sid))['current_question']
                nextitem=db.get(ReviewItem,nextq['item_id'])
                next_card_id=nextitem.card_id
                before_due=db.get(ReviewCard,next_card_id).next_due_at
                real_commit=db.commit
                def fail():
                    db.flush()  # write both records, then prove transaction rollback
                    raise RuntimeError('simulated commit failure')
                monkeypatch.setattr(db,'commit',fail)
                with pytest.raises(RuntimeError):reviews.submit(db,db.get(User,uid),sid,AnswerReview(request_id=uuid4(),item_id=nextitem.id,answer='wrong'))
                db.rollback();monkeypatch.setattr(db,'commit',real_commit)
            with sessions() as db:
                assert db.get(ReviewCard,next_card_id).next_due_at==before_due
                assert db.scalar(select(func.count(ReviewAttempt.id)))==1
            client.post('/api/v1/auth/logout',headers=_csrf(client))
            # New HTTP client and new SQLAlchemy connections resume saved state.
        with TestClient(app,headers={'Origin':'http://localhost:3000'}) as restarted:
            assert restarted.post('/api/v1/auth/login',json={'email':account,'password':'StrongLearningPass2026'}).status_code==200
            assert restarted.get('/api/v1/study/today').json()['id']==str(result[0])
            restored=restarted.get('/api/v1/review/sessions/'+str(sid))
            assert restored.json()['answered_cards']==1
            restarted.post('/api/v1/auth/logout',headers=_csrf(restarted))
            _register_and_login(restarted,email,'other-pg-'+uuid4().hex[:10]+'@example.com')
            assert restarted.get('/api/v1/study/plans/'+str(result[0])).status_code==404
            assert restarted.get('/api/v1/review/sessions/'+str(sid)).status_code==404
            assert restarted.get('/api/v1/review/due').json()['available_vocabulary_count']==0
    finally:
        app.dependency_overrides.clear()
