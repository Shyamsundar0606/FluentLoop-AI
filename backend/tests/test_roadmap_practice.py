import importlib.util,json,unicodedata
from pathlib import Path
from uuid import UUID
import pytest
from sqlalchemy import select
from app.assessment_content import load_assessment_pack,import_assessment_pack,AssessmentPack
from app.curriculum_models import Lesson
from test_interactive_learning import interactive,start
from test_learning import _set_role

ROOT=Path(__file__).resolve().parents[1]
def script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

@pytest.mark.parametrize('level,count',zip(('A1','A2','B1','B2','C1','C2'),(12,12,12,12,10,10)))
def test_every_roadmap_topic_has_contextual_four_skill_practice(level,count):
    author=script('build_roadmap_practice');rows=author.rows()[level];assert len(rows)==count
    packs=[p for p in author.packs() if p.level==level]
    assert sum(len(p.tasks) for p in packs)==count*2
    for pack in packs:
        assert pack==load_assessment_pack(ROOT/'content/roadmap'/f'{level.lower()}-roadmap-{pack.version}.json')
        for index in range(0,len(pack.tasks),2):
            practice,transfer=pack.tasks[index:index+2]
            assert len(practice.exercises)==4 and practice.grammar
            assert transfer.skill=='writing' and transfer.prerequisites==[practice.key]
            assert 'Speak:' in transfer.context and 'Review:' in transfer.context
            for e in practice.exercises:
                assert unicodedata.normalize('NFC',e.prompt)==e.prompt
                if e.type=='listening':assert 20<len(e.data['text_fr'])<=600

def test_every_key_and_additive_rehearsal_with_all_old_sources():
    result=script('validate_roadmap_practice').validate()
    assert (result['lessons'],result['scored_exercises'],result['open_transfer_tasks'])==(136,272,68)
    assert result['rehearsal_lessons']==322 and result['rehearsal_scored_exercises']==892
    assert result['main_import_authorized'] is False and result['qualified_human_review']=='pending'

def test_advanced_practice_tests_scope_not_only_typographical_errors():
    author=script('build_roadmap_practice')
    for level,rows in author.contrasts().items():
        assert len(rows)==len(author.rows()[level])
        for number,options in enumerate(rows,1):
            pack=next(p for p in author.packs() if p.level==level and any(t.key==f'topic-{number:02d}-practice' for t in p.tasks))
            item=next(t for t in pack.tasks if t.key==f'topic-{number:02d}-practice').exercises[0]
            assert 'meaning and scope' in item.prompt and set(options)<set(item.options)
            assert item.options[item.correct_option]==author.rows()[level][number-1][2]

def test_roadmap_crosswalk_preserves_live_module_ids_and_has_acyclic_preparation():
    result=script('audit_roadmap_practice').audit();seen=set()
    for item in result['topics']:
        assert item['id'] not in seen
        assert all(value in seen or value=='A0 foundations where needed' for value in item['recommended_preparation'])
        assert not item['main_import_authorized'] and item['qualified_human_review']=='pending'
        seen.add(item['id'])
    assert len(seen)==68 and len(result['source_sha256'])==12

def test_roadmap_import_preserves_owned_frozen_session_and_denies_ordinary_learner(interactive):
    client,sessions,original_id=interactive
    original=start(client,original_id)
    pack=load_assessment_pack(ROOT/'content/roadmap/a1-roadmap-0.11.1.json')
    with sessions.begin() as db:import_assessment_pack(db,pack)
    resumed=client.get(f"/api/v1/learning/sessions/{original['id']}")
    assert resumed.status_code==200 and resumed.json()['exercises']==original['exercises']
    with sessions() as db:
        lesson=db.scalar(select(Lesson).where(Lesson.slug=='m10-assessments-a1-0.11.1-topic-01-practice'))
        lesson_id=str(lesson.id)
    visible=client.get(f'/api/v1/lessons/{lesson_id}')
    assert visible.status_code==200
    assert not any(key in str(visible.json()) for key in ('accepted_answers','correct_option_id','answer_pairs'))
    _set_role(sessions,'interactive@example.com','learner')
    assert client.get(f'/api/v1/lessons/{lesson_id}').status_code==404
