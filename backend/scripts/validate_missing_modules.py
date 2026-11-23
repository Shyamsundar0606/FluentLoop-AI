"""Offline disposable SQLite rehearsal; cannot accept a protected database URL."""
import os,sys,json,hashlib
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2]
os.environ['DATABASE_URL']='sqlite://';sys.path.insert(0,str(ROOT/'backend'))
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import Base
from app.curriculum_models import CefrLevel,Lesson,Exercise,LessonPrerequisite,Course,Unit
from app.content_import import _import_data,load_content
from app.assessment_content import load_assessment_pack,import_assessment_pack,pack_digest
from app.services.exercise_formats import snapshot
from app.services.grading_service import grade_saved

def all_rows(db):
    return {table.name:Counter(json.dumps(dict(r),sort_keys=True,default=str) for r in db.execute(select(table)).mappings())
            for table in Base.metadata.sorted_tables}

def correct(saved):
    if saved['type'] in ('multiple_choice','listening'):return {'selected_option_id':saved['correct_option_id']}
    if saved['type']=='matching':return {'matches':saved['answer_pairs']}
    return {'text_answer':saved['accepted_answers'][0]}

def validate():
    engine=create_engine('sqlite://')
    from sqlalchemy import event
    @event.listens_for(engine,'connect')
    def foreign_keys(connection,_):connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine);report=[];checked=0
    with Session(engine) as db,db.begin():
        for rank,level in enumerate(('A1','A2','B1','B2','C1','C2'),1):db.add(CefrLevel(code=level,display_name=level,description=level,rank=rank))
        db.flush();_import_data(db,load_content(ROOT/'backend/content/a1/course.json'))
        for folder in ('personal','foundations','scenarios','depth'):
            for file in sorted((ROOT/'backend/content'/folder).glob('*.json')):import_assessment_pack(db,load_assessment_pack(file))
        assert db.scalar(select(func.count(Lesson.id)))==130
        before=all_rows(db)
        for file in sorted((ROOT/'backend/content/completion').glob('*.json')):
            pack=load_assessment_pack(file)
            for task in pack.tasks:
                for number,item in enumerate(task.exercises,1):
                    exercise=SimpleNamespace(exercise_type=item.type,exercise_data=item.data,prompt=item.prompt,instructions=item.instructions,
                        explanation=item.explanation,level=pack.level,sequence_order=number,learning_objective_id=None,grammar_topic_id=None)
                    options=[SimpleNamespace(id=uuid4(),option_text=t,sequence_order=i+1,is_correct=i==item.correct_option) for i,t in enumerate(item.options)]
                    saved=snapshot(exercise,options);assert grade_saved(saved,correct(saved))[0]
                    if item.type in ('multiple_choice','listening'):
                        wrong={'selected_option_id':next(o['id'] for o in saved['options'] if o['id']!=saved['correct_option_id'])}
                    elif item.type=='matching':
                        keys=list(saved['answer_pairs']);values=list(saved['answer_pairs'].values());wrong={'matches':dict(zip(keys,values[1:]+values[:1]))}
                    else:wrong={'text_answer':'An unrelated incorrect phrase.'}
                    assert not grade_saved(saved,wrong)[0];checked+=1
            assert not import_assessment_pack(db,pack)['reused']
            assert import_assessment_pack(db,pack)['reused']
            course=db.scalar(select(Course).where(Course.slug==f'm10-assessments-{pack.level.lower()}-{pack.version}'))
            lessons=db.scalars(select(Lesson).join(Unit).where(Unit.course_id==course.id)).all()
            assert len(lessons)==3 and all(l.status=='draft' for l in lessons) and course.status=='draft'
            links=db.scalar(select(func.count()).select_from(LessonPrerequisite).join(Lesson,Lesson.id==LessonPrerequisite.lesson_id).join(Unit).where(Unit.course_id==course.id))
            assert links==3
            report.append(dict(file=str(file.relative_to(ROOT)),module=file.name.split('-completion')[0],level=pack.level,
                lessons=3,scored_exercises=6,open_transfer_tasks=1,file_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),source_sha256=pack_digest(pack),
                idempotency='passed',prerequisite_links=3,independent_human_review='pending',cefr_calibration='pending',main_import_authorized=False))
        db.flush();after=all_rows(db)
        assert all(not (rows-after[name]) for name,rows in before.items())
        assert db.scalar(select(func.count(Lesson.id)))==181
        assert db.scalar(select(func.count(Exercise.id)))==620
        assert checked==102 and len(report)==17
    return dict(modules=17,lessons=51,scored_exercises=102,open_transfer_tasks=17,releases=report,
        validation='passed in disposable SQLite with foreign keys, all 130 prior source lessons preserved',
        postgresql_rehearsal='pending: protected infrastructure restoration safety check refused; not bypassed',
        audio_runtime='pending: local speech worker unavailable; format/provider contract tested with stub',
        main_import_authorized=False,qualified_human_review='pending')

if __name__=='__main__':
    result=validate();folder=ROOT/'backend/content/completion/manifest';folder.mkdir(exist_ok=True)
    (folder/'validated-releases.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Disposable SQLite rehearsal passed:17 modules,51 lessons,102 correct/wrong checks; prior130 lessons unchanged. PostgreSQL/audio runtime pending.')
