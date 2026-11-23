"""Future introductory batch: source/fixtures only, never the personal database."""
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
from pydantic import ValidationError
from sqlalchemy import select,func
from app.assessment_content import load_assessment_pack,import_assessment_pack,pack_digest,AssessmentPack
from app.curriculum_models import Lesson,LessonPrerequisite
from app.services.exercise_formats import snapshot
from app.services.grading_service import grade_saved
from test_interactive_learning import interactive,answer_for
from test_learning import _csrf

PATH=Path(__file__).resolve().parents[1]/'content/foundations/a0-foundations-0.3.0.json'
PATHS=sorted(PATH.parent.glob('*.json'))


def test_a0_is_preparation_and_has_acyclic_prerequisites():
    pack=load_assessment_pack(PATH)
    assert pack.learning_stage=='A0' and pack.level=='A1' and len(pack.tasks)==7
    assert sum(len(t.exercises) for t in pack.tasks)==36
    seen=set()
    for task in pack.tasks:
        assert set(task.prerequisites)<=seen;seen.add(task.key)
        for number,item in enumerate(task.exercises,1):
            exercise=SimpleNamespace(exercise_type=item.type,exercise_data=item.data,prompt=item.prompt,instructions=item.instructions,
                explanation=item.explanation,level='A1',sequence_order=number,learning_objective_id=None,grammar_topic_id=None)
            options=[SimpleNamespace(id=uuid4(),option_text=label,sequence_order=i+1,is_correct=i==item.correct_option) for i,label in enumerate(item.options)]
            frozen=snapshot(exercise,options);assert grade_saved(frozen,answer_for(frozen))[0]
    body=pack.model_dump();body['level']='C2'
    with pytest.raises(ValidationError):AssessmentPack.model_validate(body)
    body=pack.model_dump();body['tasks'][0]['prerequisites']=[body['tasks'][-1]['key']]
    with pytest.raises(ValidationError):AssessmentPack.model_validate(body)


def test_optional_extensions_preserve_imported_release_digest():
    original=load_assessment_pack(Path(__file__).resolve().parents[1]/'content/personal/a1-personal-0.2.1.json')
    assert pack_digest(original)=='5a24789165897d26da6adbd1627f490ed681390ae0be2e7200839ae82badbac9'


@pytest.mark.parametrize('path',PATHS,ids=lambda path:path.stem)
def test_foundations_import_is_draft_idempotent_and_adds_prerequisites(interactive,path):
    _,sessions,_=interactive
    pack=load_assessment_pack(path)
    with sessions.begin() as db:
        count=db.scalar(select(func.count(Lesson.id)))
        assert not import_assessment_pack(db,pack)['reused']
        assert import_assessment_pack(db,pack)['reused']
        assert db.scalar(select(func.count(Lesson.id)))==count+len(pack.tasks)
        linked=db.scalars(select(LessonPrerequisite).join(Lesson,Lesson.id==LessonPrerequisite.lesson_id)
                          .where(Lesson.slug.like(f'm10-assessments-a1-{pack.version}-%'))).all()
        assert len(linked)==sum(len(task.prerequisites) for task in pack.tasks)


def test_intro_writing_routes_and_saved_activity_are_not_inferred_from_slug(interactive):
    client,sessions,_=interactive
    with sessions.begin() as db:
        for path in PATHS:import_assessment_pack(db,load_assessment_pack(path))
    before=client.get('/api/v1/learning/path').json()
    intro=next(stage for stage in before['stages'] if stage['code']=='A0')
    assert intro['available_lessons']==7
    writing=next(lesson for module in intro['modules'] for lesson in module['lessons'] if lesson['kind']=='writing')
    assert writing['href']==f"/assessments/writing/{writing['id']}"
    response=client.post('/api/v1/learning/assessments/writing',headers=_csrf(client),json=dict(
        lesson_id=writing['id'],idempotency_key=str(uuid4()),text='Bonjour. Je m’appelle Léa. Merci et au revoir.'))
    assert response.status_code==200
    after=client.get('/api/v1/learning/path').json()
    intro=next(stage for stage in after['stages'] if stage['code']=='A0')
    assert intro['completed_activities']==1
    saved=next(lesson for module in intro['modules'] for lesson in module['lessons'] if lesson['id']==writing['id'])
    assert saved['status']=='saved_submission'
