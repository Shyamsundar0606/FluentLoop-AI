"""Draft corrections, legacy identity repair and publication gates; synthetic data only."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from app.config import Settings
from app.core.database import Base, get_db
from app.main import app
from app import content_import as importer
from app.content_audit import audit
from app.content_schemas import ContentImportInput
from app.curriculum_models import CefrLevel, Lesson, Exercise, ExerciseOption, Lexeme, LessonVocabulary, GrammarTopic, LessonGrammar
from app.models import User
from app.publish_content import publish_course
from app.study_models import ReviewItem
from test_curriculum import _approved_test_review_record, _import, CONTENT_PATH
from test_learning import _register_and_login, _set_role, _csrf

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('raw,wanted', [('une table','table'),('une amie','amie'),('une clé','clé'),
    ('une sœur','sœur'),('les parents','parents'),('un livre','livre'),("l'eau",'eau'),('l’année','année'),
    ('lettre','lettre'),('université','université')])
def test_complete_noun_articles_and_word_boundaries(raw,wanted):
    assert importer._lemma_for_storage(raw,'noun') == wanted
    assert importer._lemma_for_storage(raw,'verb') == raw


def test_source_revision_and_answers_are_reviewable_and_explicit():
    previous = importer.load_content(CONTENT_PATH.parent/'archive/course-1.0.1.json')
    current = importer.load_content(CONTENT_PATH)
    assert current.version == '1.0.2'
    assert [(l.slug,l.title) for l in previous.course.lessons] == [(l.slug,l.title) for l in current.course.lessons]
    for old,new in zip(previous.course.lessons,current.course.lessons):
        assert [(e.options,e.correct_option) for e in old.exercises] == [(e.options,e.correct_option) for e in new.exercises]
        assert all(e.lexemes for e in new.examples)
    invalid = current.model_dump()
    invalid['course']['lessons'][8]['examples'][0]['lexemes']=['unrelated verb']
    with pytest.raises(ValueError,match='references'):
        ContentImportInput.model_validate(invalid)


def test_inflected_examples_reject_unrelated_verb_links(api_client):
    from app.curriculum_models import ExampleSentence, LexemeExample
    _,sessions,_=api_client;_import(sessions)
    with sessions.begin() as db:
        sentence=db.scalar(select(ExampleSentence).where(ExampleSentence.french_text=="J'habite à Lyon."))
        linked=list(db.scalars(select(Lexeme.normalized_lemma).join(LexemeExample).where(
            LexemeExample.example_sentence_id==sentence.id)))
        assert linked==['habiter']
        unrelated=db.scalar(select(Lexeme).where(Lexeme.normalized_lemma=='aimer'))
        db.add(LexemeExample(lexeme_id=unrelated.id,example_sentence_id=sentence.id));db.flush()
        assert not audit(db,CONTENT_PATH)['technical_integrity_passed']
    _import(sessions)
    with sessions() as db:assert audit(db,CONTENT_PATH)['technical_integrity_passed']


@pytest.fixture(params=['sqlite','postgres'])
def correction_database(api_client,request):
    client,sessions,email=api_client
    if request.param == 'sqlite':
        yield client,sessions,email
        return
    admin=os.getenv('A1_TEST_ADMIN_DATABASE_URL')
    if not admin:pytest.skip('Set A1_TEST_ADMIN_DATABASE_URL; creates fresh fluentloop_a1_* only.')
    url=make_url(admin)
    assert url.host in ('localhost','127.0.0.1')
    name='fluentloop_a1_'+uuid4().hex[:12]
    engine=create_engine(url,isolation_level='AUTOCOMMIT')
    with engine.connect() as db:db.execute(text(f'CREATE DATABASE "{name}"'))
    target=url.set(database=name).render_as_string(hide_password=False)
    migration=subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',
        env={**os.environ,'DATABASE_URL':target},capture_output=True,text=True)
    assert migration.returncode==0,migration.stderr
    test_engine=create_engine(target)
    pg_sessions=sessionmaker(bind=test_engine,expire_on_commit=False)
    original=app.dependency_overrides[get_db]
    def get_pg():
        with pg_sessions() as db:yield db
    app.dependency_overrides[get_db]=get_pg
    try:yield client,pg_sessions,email
    finally:
        app.dependency_overrides[get_db]=original
        test_engine.dispose();engine.dispose()
    # Leave the explicitly isolated database for inspection; never drop app data.


def fingerprints(sessions):
    from app import curriculum_models
    curriculum={value.__table__.name for value in vars(curriculum_models).values()
                if isinstance(value,type) and hasattr(value,'__table__')}
    with sessions() as db:
        return {table.name:hashlib.sha256(repr(sorted(
            [repr(tuple(row)) for row in db.execute(select(table)).all()])).encode()).hexdigest()
            for table in Base.metadata.sorted_tables if table.name not in curriculum}


def test_legacy_reimport_retains_ids_active_snapshots_scores_and_study_history(correction_database,monkeypatch):
    client,sessions,email=correction_database
    old=importer.load_content(CONTENT_PATH.parent/'archive/course-1.0.1.json')
    legacy=lambda value,pos:re.sub(r"^(?:un|une|le|la|l')\s*",'',value.strip(),flags=re.I) if pos=='noun' else value
    with monkeypatch.context() as patch:
        patch.setattr(importer,'_lemma_for_storage',legacy)
        with sessions.begin() as db:
            if not db.scalar(select(CefrLevel)):
                db.add_all([CefrLevel(code=level,display_name=level,description=level,rank=i)
                    for i,level in enumerate(('A1','A2','B1','B2','C1','C2'),1)])
                db.flush()
            importer._import_data(db,old)
    _register_and_login(client,email,'a1-preservation@example.com')
    _set_role(sessions,'a1-preservation@example.com','admin')
    monkeypatch.setattr('app.services.draft_preview.get_settings',lambda:Settings(
        _env_file=None,APP_ENV='development',ENABLE_DRAFT_LEARNING_PREVIEW=True))
    with sessions.begin() as db:
        lesson=db.scalar(select(Lesson).where(Lesson.slug=='a1-005'))
        lesson_id=str(lesson.id)
        extra=GrammarTopic(slug='legacy-extra-topic',title='Legacy shared topic',cefr_level='A1',summary='Retain this topic row.')
        db.add(extra);db.flush();extra_id=extra.id
        db.add(LessonGrammar(lesson_id=lesson.id,grammar_topic_id=extra.id))
        identities={model.__tablename__:set(db.scalars(select(model.id)).all())
            for model in (Lesson,Exercise,ExerciseOption,Lexeme)}
        old_lexemes={row.id:row.lemma for row in db.scalars(select(Lexeme))}
    def post(path,payload):return client.post('/api/v1/'+path,json=payload,headers=_csrf(client))
    started=post('learning/sessions',{'lesson_id':lesson_id});assert started.status_code==201,started.text
    saved=started.json();first=saved['exercises'][0]
    with sessions() as db:
        correct=db.scalar(select(ExerciseOption).join(Exercise).where(
            Exercise.lesson_id==UUID(lesson_id),Exercise.sequence_order==1,ExerciseOption.is_correct.is_(True)))
        option=str(correct.id)
    answered=post('learning/sessions/'+saved['id']+'/answers',{'session_exercise_id':first['id'],
        'selected_option_id':option,'idempotency_key':str(uuid4())})
    assert answered.status_code==200,answered.text
    assert post('study/today/generate',{'request_id':str(uuid4())}).status_code==200
    review=post('review/sessions',{'request_id':str(uuid4()),'limit':3});assert review.status_code==200,review.text
    question=review.json()['current_question']
    with sessions() as db:key=db.get(ReviewItem,UUID(question['item_id'])).snapshot['answers'][0]
    result=post('review/sessions/'+review.json()['id']+'/answers',{'request_id':str(uuid4()),
        'item_id':question['item_id'],'answer':key,'recall_rating':'normal'})
    assert result.status_code==200,result.text
    # Representative unchanged M05/M06 history alongside real lesson/review data.
    from app.ai.models import Conversation,Message
    from app.speech.models import SpeechSession,SpeechTurn
    with sessions.begin() as db:
        uid=db.scalar(select(User.id).where(User.email=='a1-preservation@example.com'))
        convo=Conversation(user_id=uid,title='Preserve',mode='roleplay',cefr_level='A1');db.add(convo);db.flush()
        db.add(Message(conversation_id=convo.id,role='user',content='Bonjour',response_status='success'))
        voice=SpeechSession(user_id=uid,ai_conversation_id=convo.id,cefr_level='A1');db.add(voice);db.flush()
        db.add(SpeechTurn(user_id=uid,speech_session_id=voice.id,request_id=uuid4(),input_checksum='a'*64,
            transcript='Original uncertain recognition',transcription_status='uncertain',status='unusable'))
    before=fingerprints(sessions)
    changed=_import(sessions);repeat=_import(sessions)
    assert fingerprints(sessions)==before
    assert repeat['inserted']==repeat['updated']==repeat['deleted']==repeat['rejected']==0,repeat
    with sessions() as db:
        assert all(set(db.scalars(select(model.id)).all())==identities[model.__tablename__]
                   for model in (Lesson,Exercise,ExerciseOption,Lexeme))
        assert db.get(GrammarTopic,extra_id) is not None
        for identifier,lemma in old_lexemes.items():
            if lemma.startswith('e ') or lemma=='s parents':
                assert db.get(Lexeme,identifier).lemma not in (lemma,)
        comparison=audit(db,CONTENT_PATH)
        assert comparison['technical_integrity_passed'],comparison['lessons']
        assert comparison['published_lessons']==0
    resumed=post('learning/sessions/'+saved['id']+'/resume',{})
    assert resumed.status_code==200,resumed.text
    assert resumed.json()['lesson_content_version']=='1.0.1'
    assert resumed.json()['exercises'][0]['prompt']==first['prompt']
    assert resumed.json()['score_points']==1
    print(json.dumps({'database':sessions.kw['bind'].dialect.name,'revision_import':changed,'repeat_import':repeat,
        'history_fingerprints_unchanged':True,'original_ids_preserved':True}))


@pytest.mark.parametrize('defect',['drift','translation','importer','administrator','dependencies','pending'])
def test_publication_rejects_drift_or_missing_authorized_approvals(api_client,defect):
    _,sessions,_=api_client;_import(sessions)
    record=_approved_test_review_record().model_dump(mode='json')
    with sessions.begin() as db:
        db.add(User(id=UUID(int=1),email='gate-test@example.com',password_hash='not-a-login-fixture',role='admin'))
        db.flush()
        if defect=='drift':db.scalar(select(Exercise)).prompt='Unreviewed edit after import'
        if defect=='translation':
            from app.curriculum_models import WordSense
            db.scalar(select(WordSense)).explanation_english='Unreviewed translation drift'
        if defect=='importer':record['importer_sha256']='0'*64
        if defect=='administrator':db.get(User,UUID(int=1)).role='learner'
        if defect=='dependencies':record['lessons'][1]['required_lesson_slugs']=[]
        if defect=='pending':record['lessons'][0]['dependencies']['status']='pending'
        db.flush()
        with pytest.raises(ValueError):publish_course(db,record)
        assert all(lesson.status=='draft' for lesson in db.scalars(select(Lesson)))
