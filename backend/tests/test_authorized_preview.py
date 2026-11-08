"""M08.1: trusted preview access and availability, without granting learner roles."""
from dataclasses import replace
from uuid import UUID
import pytest
from sqlalchemy import select
from app.config import Settings
from app.curriculum_models import ExerciseOption
from app.learning_models import LearningSessionExercise
from app.models import User
from app.interactive_content import load_pack,import_pack
from app.services.grading_service import grade_saved
from test_interactive_learning import interactive,start
from test_learning import _csrf


def test_access_and_real_counts_require_authenticated_preview(interactive):
    client,sessions,lid=interactive
    assert client.get('/api/v1/learning/access').json()=={'mode':'draft_preview','current_level':'A1'}
    catalog=client.get('/api/v1/learning/practice/catalog').json()
    assert {i['category']:i['available_exercises'] for i in catalog['items']}=={
        'grammar':3,'sentence_building':1,'listening':1,'mistakes':0}
    assert next(i for i in catalog['items'] if i['category']=='mistakes')['availability_reason']=='no_unresolved_mistakes'
    saved=start(client,lid)
    assert len(saved['exercises'][0]['options'])==4
    assert not any(k in str(saved) for k in ('correct_option_id','answer_pairs','accepted_orders','accepted_answers','text_fr'))
    client.cookies.clear()
    assert client.get('/api/v1/learning/access').status_code==401


@pytest.mark.parametrize('environment,enabled,role,verified,expected',[
    ('development',True,'admin',True,'draft_preview'),
    ('development',False,'admin',True,'published_only'),
    ('production',True,'admin',True,'published_only'),
    ('development',True,'learner',True,'published_only'),
    ('development',True,'admin',False,'published_only'),
])
def test_preview_configuration_and_account_matrix(interactive,monkeypatch,environment,enabled,role,verified,expected):
    client,sessions,lid=interactive
    with sessions.begin() as db:
        user=db.scalar(select(User).where(User.email=='interactive@example.com'))
        user.role=role
        if not verified:user.email_verified_at=None
    monkeypatch.setattr('app.services.draft_preview.get_settings',lambda:Settings(_env_file=None,
        APP_ENV=environment,COOKIE_SECURE=environment=='production',ENABLE_DRAFT_LEARNING_PREVIEW=enabled))
    assert client.get('/api/v1/learning/access').json()['mode']==expected
    catalog=client.get('/api/v1/learning/practice/catalog').json()
    if expected=='published_only':
        assert all(i['available_exercises']==0 for i in catalog['items'])
        assert client.get('/api/v1/learning/grammar').json()['items']==[]
        assert client.post('/api/v1/learning/practice/sessions',headers=_csrf(client),json={'category':'grammar'}).status_code==409
        assert client.post('/api/v1/learning/sessions',headers=_csrf(client),json={'lesson_id':lid}).status_code==404


def test_trusted_flag_revocation_blocks_existing_session_and_audio(interactive,monkeypatch):
    client,_,lid=interactive;saved=start(client,lid);sid=saved['id']
    monkeypatch.setattr('app.services.draft_preview.get_settings',lambda:Settings(_env_file=None,
        APP_ENV='development',ENABLE_DRAFT_LEARNING_PREVIEW=False))
    assert client.get(f'/api/v1/learning/sessions/{sid}').status_code==404
    assert client.post(f'/api/v1/learning/sessions/{sid}/resume',headers=_csrf(client)).status_code==404
    assert client.post(f"/api/v1/learning/sessions/{sid}/exercises/{saved['exercises'][4]['id']}/audio",headers=_csrf(client)).status_code==404


def test_fixture_revision_does_not_overwrite_frozen_keys_or_option_ids(interactive):
    client,sessions,lid=interactive;saved=start(client,lid)
    eid=UUID(saved['exercises'][0]['exercise_id'])
    with sessions.begin() as db:
        frozen=db.get(LearningSessionExercise,UUID(saved['exercises'][0]['id'])).exercise_snapshot
        original_ids=set(db.scalars(select(ExerciseOption.id).where(ExerciseOption.exercise_id==eid)))
        revised=load_pack().model_copy(deep=True);revised.version='0.1.2'
        revised.exercises[0].options.append('êtes')
        import_pack(db,revised)
        assert original_ids <= set(db.scalars(select(ExerciseOption.id).where(ExerciseOption.exercise_id==eid)))
        assert db.get(LearningSessionExercise,UUID(saved['exercises'][0]['id'])).exercise_snapshot==frozen
        assert grade_saved(frozen,{'selected_option_id':frozen['correct_option_id']})[0]
    resumed=client.get(f"/api/v1/learning/sessions/{saved['id']}").json()
    assert len(resumed['exercises'][0]['options'])==4
