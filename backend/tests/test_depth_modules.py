import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.assessment_content import load_assessment_pack,import_assessment_pack,AssessmentPack
from app.curriculum_models import Lesson
from app.services.exercise_formats import snapshot
from app.services.grading_service import grade_saved
from test_interactive_learning import interactive,answer_for

ROOT=Path(__file__).resolve().parents[1]
PATHS=sorted((ROOT/'content/depth').glob('*.json'))

@pytest.mark.parametrize('path',PATHS,ids=lambda p:p.stem)
def test_depth_dossier_keys_prerequisites_and_non_destructive_import(interactive,path):
    _,sessions,_=interactive;pack=load_assessment_pack(path)
    assert len(pack.tasks)==3 and pack.tasks[1].prerequisites==['input-1']
    assert pack.tasks[2].prerequisites==['input-1','input-2'] and pack.tasks[2].skill=='writing'
    for task in pack.tasks[:2]:
        for n,item in enumerate(task.exercises,1):
            exercise=SimpleNamespace(exercise_type=item.type,exercise_data=item.data,prompt=item.prompt,instructions=item.instructions,
                explanation=item.explanation,level=pack.level,sequence_order=n,learning_objective_id=None,grammar_topic_id=None)
            options=[SimpleNamespace(id=uuid4(),option_text=t,sequence_order=i+1,is_correct=i==item.correct_option) for i,t in enumerate(item.options)]
            saved=snapshot(exercise,options);assert grade_saved(saved,answer_for(saved))[0]
            wrong=next(o['id'] for o in saved['options'] if o['id']!=saved['correct_option_id'])
            assert not grade_saved(saved,{'selected_option_id':wrong})[0]
    with sessions.begin() as db:
        original=set(db.scalars(select(Lesson.id)))
        assert not import_assessment_pack(db,pack)['reused']
        assert import_assessment_pack(db,pack)['reused']
        assert original<=set(db.scalars(select(Lesson.id)))
        assert db.scalar(select(func.count(Lesson.id)).where(Lesson.status=='published'))==0

def test_depth_source_reproducibility_and_coverage_audit():
    spec=importlib.util.spec_from_file_location('depth_author',ROOT/'scripts/build_depth_modules.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for row,path in zip(module.MODULES,PATHS):
        assert load_assessment_pack(path)==AssessmentPack.model_validate(module.build(row))
        if row['stage'] in ('B2','C1','C2'):
            assert sum(len(part['text'].split()) for part in row['inputs'])>300
    spec=importlib.util.spec_from_file_location('coverage_author',ROOT/'scripts/audit_curriculum_coverage.py')
    coverage=importlib.util.module_from_spec(spec);spec.loader.exec_module(coverage)
    audit=coverage.audit();modules=[m for s in audit['stages'] for m in s['modules']]
    assert len(modules)==52 and sum(m['main_lessons'] for m in modules)==181
    assert sum(m['staged_lessons'] for m in modules)==5
    assert all(m['gaps'] and not m['competency_demonstrated'] for m in modules)
