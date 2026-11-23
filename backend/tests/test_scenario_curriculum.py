"""Scenario releases remain original, bounded drafts with traceable answer keys."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.assessment_content import load_assessment_pack,import_assessment_pack,pack_digest
from app.services.exercise_formats import snapshot
from app.services.grading_service import grade_saved
from test_interactive_learning import interactive,answer_for

ROOT=Path(__file__).resolve().parents[1]
PATHS=sorted((ROOT/'content/scenarios').glob('*.json'))


@pytest.mark.parametrize('path',PATHS,ids=lambda p:p.stem)
def test_scenario_answer_keys_and_idempotent_import(interactive,path):
    _,sessions,_=interactive;pack=load_assessment_pack(path)
    assert len(pack.tasks)==2 and len(pack.tasks[0].exercises)==4
    assert pack.tasks[1].skill=='writing' and pack.tasks[1].prerequisites==[pack.tasks[0].key]
    assert 'not a calibrated' in pack.tasks[1].context
    assert 'reviews pending' in pack.source_license
    for number,item in enumerate(pack.tasks[0].exercises,1):
        exercise=SimpleNamespace(exercise_type=item.type,exercise_data=item.data,prompt=item.prompt,
            instructions=item.instructions,explanation=item.explanation,level=pack.level,
            sequence_order=number,learning_objective_id=None,grammar_topic_id=None)
        options=[SimpleNamespace(id=uuid4(),option_text=label,sequence_order=i+1,is_correct=i==item.correct_option)
                 for i,label in enumerate(item.options)]
        saved=snapshot(exercise,options)
        assert grade_saved(saved,answer_for(saved))[0]
        if item.type in ('multiple_choice','listening'):
            wrong={'selected_option_id':next(o['id'] for o in saved['options'] if o['id']!=saved['correct_option_id'])}
        else:
            keys=list(saved['answer_pairs']);values=list(saved['answer_pairs'].values())
            wrong={'matches':dict(zip(keys,values[1:]+values[:1]))}
        assert not grade_saved(saved,wrong)[0]
    with sessions.begin() as db:
        assert not import_assessment_pack(db,pack)['reused']
        assert import_assessment_pack(db,pack)==dict(reused=True,lessons=2,source_sha256=pack_digest(pack))


def test_scenario_sources_reproduce_and_advance_discourse_demands():
    spec=importlib.util.spec_from_file_location('scenario_author',ROOT/'scripts/build_scenario_curriculum.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    from app.assessment_content import AssessmentPack
    assert [r['stage'] for r in module.ROWS]==['A0','A1','A2','B1','B2','C1','C2']
    for row,path in zip(module.ROWS,PATHS):
        assert load_assessment_pack(path)==AssessmentPack.model_validate(module.build(row))
    assert len(module.ROWS[-1]['passage'].split())>150
    assert 'presupposition' in module.ROWS[-1]['outcome']
    assert 'selection' in module.ROWS[-2]['teaching']
    assert 'counterargument' in module.ROWS[-3]['outcome']
