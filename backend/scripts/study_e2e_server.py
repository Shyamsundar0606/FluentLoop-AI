"""Guarded real-M07 API with isolated PostgreSQL; real AI/speech by default."""
import os
from uuid import uuid4
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.config import get_settings

settings=get_settings()
assert os.getenv('STUDY_E2E_TEST_SERVER')=='1'
assert make_url(settings.database_url).database.startswith('fluentloop_m07_')
assert settings.environment=='development'

from app.main import app
from app.core.database import SessionLocal
from app.models import User,UserProfile,UserPreferences,utcnow
from app.security import hash_password
from app.content_import import load_content,_import_data
from app.curriculum_models import CefrLevel
from app.services import rate_limit

# Real Redis and the unchanged rate-limit rules, scoped to this explicitly
# isolated test API instance so repeated test runs do not share auth buckets.
class TestRedisNamespace:
    def __init__(self,client):
        self.client=client
        self.prefix='m07-e2e:'+uuid4().hex+':'
    def eval(self,script,key_count,key,*args):
        assert key_count==1
        return self.client.eval(script,1,self.prefix+key,*args)
    def ttl(self,key):
        return self.client.ttl(self.prefix+key)

rate_limit.redis_client=TestRedisNamespace(rate_limit.redis_client)

with SessionLocal.begin() as db:
    for rank,level in enumerate(('A1','A2','B1','B2','C1','C2'),1):
        if not db.scalar(select(CefrLevel).where(CefrLevel.code==level)):
            db.add(CefrLevel(code=level,display_name=level,description=level,rank=rank))
    db.flush()
    _import_data(db,load_content(Path(__file__).resolve().parents[1]/'content/a1/course.json'))
    for email,role in [('study-browser@example.com','admin'),('study-learner@example.com','learner')]:
        if not db.scalar(select(User).where(User.email==email)):
            user=User(email=email,role=role,password_hash=hash_password('IsolatedStudyTest2026!'),email_verified_at=utcnow())
            db.add(user);db.flush()
            db.add(UserProfile(user_id=user.id,display_name='Study browser',timezone='Europe/Paris',learning_goal='Daily conversations',onboarding_completed_at=utcnow()))
            db.add(UserPreferences(user_id=user.id))
