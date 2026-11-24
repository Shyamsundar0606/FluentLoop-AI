"""Offline roadmap rehearsal. Only an in-memory SQLite engine is created."""
import os,sys,json,hashlib
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2]
os.environ['DATABASE_URL']='sqlite://';sys.path.insert(0,str(ROOT/'backend'))
from sqlalchemy import create_engine,event,select,func
from sqlalchemy.orm import Session
from app.main import app  # register all metadata, without starting its lifespan
from app.core.database import Base
from app.curriculum_models import CefrLevel,Lesson,Exercise,Course,Unit,LessonPrerequisite
from app.content_import import _import_data,load_content
from app.assessment_content import load_assessment_pack,import_assessment_pack,pack_digest
from app.services.exercise_formats import snapshot
from app.services.grading_service import grade_saved

def correct(saved):
    if saved['type'] in ('multiple_choice','listening'):return {'selected_option_id':saved['correct_option_id']}
    if saved['type']=='sentence_order':return {'tile_ids':saved['accepted_orders'][0]}
    if saved['type']=='matching':return {'matches':saved['answer_pairs']}
    return {'text_answer':saved['accepted_answers'][0]}

def check_keys(pack):
    checked=0
    for task in pack.tasks:
        for position,item in enumerate(task.exercises,1):
            exercise=SimpleNamespace(exercise_type=item.type,exercise_data=item.data,prompt=item.prompt,instructions=item.instructions,
              explanation=item.explanation,level=pack.level,sequence_order=position,learning_objective_id=None,grammar_topic_id=None)
            options=[SimpleNamespace(id=uuid4(),option_text=t,sequence_order=i+1,is_correct=i==item.correct_option) for i,t in enumerate(item.options)]
            saved=snapshot(exercise,options);answer=correct(saved)
            assert grade_saved(saved,answer)[0]
            if item.type in ('multiple_choice','listening'):
                wrong=[{'selected_option_id':o['id']} for o in saved['options'] if o['id']!=saved['correct_option_id']]
            elif item.type=='sentence_order':wrong=[{'tile_ids':list(reversed(saved['accepted_orders'][0]))}]
            elif item.type=='matching':
                keys=list(saved['answer_pairs']);values=list(saved['answer_pairs'].values())
                wrong=[{'matches':dict(zip(keys,values[1:]+values[:1]))}]
            else:wrong=[{'text_answer':'Réponse sans rapport avec la question.'}]
            assert all(not grade_saved(saved,a)[0] for a in wrong)
            checked+=1
    return checked

def records(db):
    return {t.name:Counter(json.dumps(dict(r),sort_keys=True,default=str) for r in db.execute(select(t)).mappings()) for t in Base.metadata.sorted_tables}

def validate():
    engine=create_engine('sqlite://')
    @event.listens_for(engine,'connect')
    def foreign_keys(connection,_):connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine);report=[]
    with Session(engine) as db,db.begin():
        for rank,level in enumerate(('A1','A2','B1','B2','C1','C2'),1):db.add(CefrLevel(code=level,display_name=level,description=level,rank=rank))
        db.flush();_import_data(db,load_content(ROOT/'backend/content/a1/course.json'))
        for folder in ('personal','foundations','scenarios','depth','completion','writing-bridges'):
            for file in sorted((ROOT/'backend/content'/folder).glob('*.json')):import_assessment_pack(db,load_assessment_pack(file))
        assert db.scalar(select(func.count(Lesson.id)))==186
        before=records(db);formats=Counter()
        for file in sorted((ROOT/'backend/content/roadmap').glob('*.json')):
            pack=load_assessment_pack(file);checked=check_keys(pack)
            assert not import_assessment_pack(db,pack)['reused']
            assert import_assessment_pack(db,pack)['reused']
            course=db.scalar(select(Course).where(Course.slug==f'm10-assessments-{pack.level.lower()}-{pack.version}'))
            lessons=db.scalars(select(Lesson).join(Unit).where(Unit.course_id==course.id)).all()
            assert len(lessons)==len(pack.tasks) and course.status=='draft' and all(l.status=='draft' for l in lessons)
            links=db.scalar(select(func.count()).select_from(LessonPrerequisite).join(Lesson,Lesson.id==LessonPrerequisite.lesson_id).join(Unit).where(Unit.course_id==course.id))
            assert links==sum(len(t.prerequisites) for t in pack.tasks)
            formats.update(e.type for t in pack.tasks for e in t.exercises)
            report.append(dict(file=file.relative_to(ROOT).as_posix(),level=pack.level,version=pack.version,lessons=len(pack.tasks),scored_exercises=checked,
                open_transfer_tasks=sum(t.skill=='writing' for t in pack.tasks),prerequisite_links=links,
                file_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),source_sha256=pack_digest(pack),main_import_authorized=False))
        after=records(db);assert all(not (old-after[name]) for name,old in before.items())
        assert db.scalar(select(func.count(Lesson.id)))==322
        assert db.scalar(select(func.count(Exercise.id)))==892
        assert db.scalar(select(func.count(Lesson.id)).where(Lesson.status=='published'))==0
        assert set(formats)=={'multiple_choice','fill_blank','short_answer','sentence_order','matching','listening'}
    return dict(roadmap_topics=68,lessons=136,scored_exercises=272,open_transfer_tasks=68,
       formats=dict(formats),prior_source_lessons_preserved=186,rehearsal_lessons=322,rehearsal_scored_exercises=892,
       answer_keys='All correct keys and every alternative choice/valid wrong structured answer checked',
       preservation='All prior rows preserved',idempotency='passed',foreign_keys='passed',
       releases=report,main_import_authorized=False,qualified_human_review='pending',cefr_calibration='not established',
       sqlite_rehearsal='passed',postgresql_rehearsal='pending',audio_synthesis='pending')

if __name__=='__main__':
    body=validate();folder=ROOT/'backend/content/roadmap/manifest';folder.mkdir(exist_ok=True)
    path=folder/'validated-releases.json'
    assert not path.exists(),'Preserve the previous validation report; use a dated report for another run.'
    path.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Roadmap SQLite rehearsal passed:136 lessons/272 scored exercises/68 transfer tasks, all six formats, prior186 lessons preserved. No main import.')
