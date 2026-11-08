"""Prepare fresh isolated M07 browser accounts and privileged test expectations."""
import json
import os
from pathlib import Path
from uuid import uuid4
from sqlalchemy import create_engine,select,text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.models import User,UserProfile,UserPreferences,utcnow
from app.security import hash_password
from app.curriculum_models import Lesson,Exercise,ExerciseOption
from app.services.study_content import vocabulary

url=os.environ['DATABASE_URL']
assert make_url(url).database.startswith('fluentloop_m07_')
assert os.getenv('STUDY_E2E_TEST_SERVER')=='1'
with Session(create_engine(url)) as db:
    assert db.execute(text('SELECT version_num FROM alembic_version')).scalar() in ('20261104_0008','20261104_0009')
    emails=[]
    for role in ('admin','learner'):
        email=f'm07-{role}-{uuid4().hex[:10]}@example.com';emails.append(email)
        user=User(email=email,role=role,password_hash=hash_password('IsolatedStudyTest2026!'),email_verified_at=utcnow())
        db.add(user);db.flush()
        db.add(UserProfile(user_id=user.id,display_name='Study test',timezone='Europe/Paris',learning_goal='Daily conversations',onboarding_completed_at=utcnow()))
        db.add(UserPreferences(user_id=user.id))
    db.commit()
    user=db.scalar(select(User).where(User.email==emails[0]))
    answers={v['prompt']:v['answers'][0] for v in vocabulary(db,user,'A1').values()}
    assert answers,'Enable authorized development preview for this isolated test.'
    lesson=db.scalar(select(Lesson).where(Lesson.slug=='a1-001'))
    options=[str(db.scalar(select(ExerciseOption.id).where(ExerciseOption.exercise_id==e.id,ExerciseOption.is_correct.is_(True)))) for e in db.scalars(select(Exercise).where(Exercise.lesson_id==lesson.id).order_by(Exercise.sequence_order))]
    root=Path(__file__).resolve().parents[2]
    path=root/'.speech-data/m07-browser-fixture.json';path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({'admin':emails[0],'learner':emails[1],'answers':answers,'options':options}),encoding='utf-8')
    print('Created two isolated accounts and local privileged browser expectations.')
