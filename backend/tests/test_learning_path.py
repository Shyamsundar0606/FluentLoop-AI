"""Progressive path navigation without treating A0 as a database CEFR level."""
import json
from pathlib import Path
import pytest
from sqlalchemy import select
from app.assessment_content import import_assessment_pack,load_assessment_pack
from app.models import User
from app.services.learning_path import MAP_PATH
from test_interactive_learning import interactive
from test_learning import _csrf,_set_role


@pytest.fixture
def pathway(interactive):
    client,sessions,_=interactive
    with sessions.begin() as db:
        for path in sorted((Path(__file__).resolve().parents[1]/'content/personal').glob('*.json')):
            import_assessment_pack(db,load_assessment_pack(path))
    return client,sessions


def test_source_graph_and_stage_coverage():
    body=json.loads(MAP_PATH.read_text(encoding='utf-8'))
    assert [s['code'] for s in body['stages']]==['A0','A1','A2','B1','B2','C1','C2']
    earlier=set();references=[]
    for stage in body['stages']:
        assert stage['official_cefr']==(stage['code']!='A0')
        for module in stage['modules']:
            assert module['id'] not in earlier and set(module['prerequisites'])<=earlier
            assert module['objective'] and module['outcomes'] and module['revision'] and module['assessment']
            assert set(module['required_skills'])=={'grammar','vocabulary','reading','listening','writing','speaking'}
            earlier.add(module['id']);references.extend(module['lesson_slugs'])
    assert len(references)==len(set(references))==186


def test_authorized_path_counts_and_ordinary_denial(pathway):
    client,sessions=pathway
    response=client.get('/api/v1/learning/path');assert response.status_code==200
    body=response.json();assert body['certification'] is False
    assert body['next_activity']['stage']=='A1' and body['next_activity']['reason']=='practice_or_revision'
    assert [s['available_lessons'] for s in body['stages']]==[0,22,12,12,12,12,12]
    assert all(not s['coverage_complete'] for s in body['stages'])
    assert not any(key in str(body) for key in ('accepted_answers','correct_option_id','answer_pairs'))
    _set_role(sessions,'interactive@example.com','learner')
    ordinary=client.get('/api/v1/learning/path').json()
    assert sum(s['available_lessons'] for s in ordinary['stages'])==0
    assert ordinary['next_activity'] is None
    assert not any(m['lessons'] for s in ordinary['stages'] for m in s['modules'])


def test_browsed_assessment_and_writing_use_permitted_lesson_level(pathway):
    client,sessions=pathway
    catalog=client.get('/api/v1/learning/assessments?level=C2')
    assert catalog.status_code==200 and catalog.json()['level']=='C2'
    grammar=next(i for i in catalog.json()['items'] if i['skill']=='grammar')
    writing=next(i for i in catalog.json()['items'] if i['skill']=='writing')
    started=client.post('/api/v1/learning/assessments/sessions',headers=_csrf(client),json=dict(skill='grammar',lesson_id=grammar['lesson_id']))
    assert started.status_code==200 and started.json()['lesson']['level']=='C2'
    assert client.get(f"/api/v1/learning/assessments/writing/tasks/{writing['lesson_id']}").status_code==200
    with sessions() as db:
        user=db.scalar(select(User).where(User.email=='interactive@example.com'))
        assert user.preferences.current_level=='a1'
    assert client.get('/api/v1/learning/assessments?level=A0').status_code==422
    _set_role(sessions,'interactive@example.com','learner')
    assert client.get('/api/v1/learning/assessments?level=C2').json()['items']==[]
    assert client.get(f"/api/v1/learning/assessments/writing/tasks/{writing['lesson_id']}").status_code==404
