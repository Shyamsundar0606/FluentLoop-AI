"""Fresh disposable admin browser stack. Does not modify personal/M08 databases.

prepare writes a private state file; serve reads that exact file. No cleanup,
privilege escalation, service startup or protected-schema migration is performed.
"""
import json,os,sys,subprocess,runpy,socket
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4
from datetime import datetime,timezone
from sqlalchemy import create_engine,select,text
from sqlalchemy.engine import make_url
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
def disposable(url):
    parsed=make_url(url)
    if parsed.host not in ('127.0.0.1','localhost') or not parsed.database.startswith('fluentloop_browser_admin_'):
        raise ValueError('Only a local fresh admin-browser disposable database is allowed')
    return parsed

def prepare():
    import shutil
    assert shutil.disk_usage('C:/').free>=30*2**30 and shutil.disk_usage('D:/').free>=50*2**30
    config=json.loads((ROOT/'.publication-private/personal-local/config.json').read_text())
    base=make_url(config['database_url']);assert base.database=='fluentloop'
    from redis import Redis
    redis_url='redis://127.0.0.1:6379/15'
    assert Redis.from_url(redis_url).dbsize()==0,'Test Redis DB15 is not empty; no flush is allowed'
    for port in (8002,3002):
        with socket.socket() as probe:assert probe.connect_ex(('127.0.0.1',port))!=0,'Test port is occupied'
    name='fluentloop_browser_admin_'+uuid4().hex[:12];target=base.set(database=name)
    disposable(target)
    env={**os.environ,**{k:v for k,v in dotenv_values(ROOT/'.env').items() if v is not None}}
    env.update(DATABASE_URL=target.render_as_string(hide_password=False),REDIS_URL=redis_url,APP_ENV='development',
        ENABLE_DRAFT_LEARNING_PREVIEW='true',ENABLE_PERSONAL_LEARNING_PREVIEW='false',PERSONAL_PREVIEW_USER_IDS='[]',
        FRONTEND_ORIGIN='http://127.0.0.1:3002',CORS_ORIGINS='["http://127.0.0.1:3002"]',
        SESSION_COOKIE_NAME='fluentloop_admin_test_session',CSRF_COOKIE_NAME='fluentloop_csrf',
        SMTP_HOST='127.0.0.1',SMTP_PORT='1025',OLLAMA_BASE_URL='http://127.0.0.1:11434',SPEECH_WORKER_URL='http://127.0.0.1:8090')
    folder=ROOT/'.publication-private'/('admin-browser-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:6]);folder.mkdir()
    with create_engine(base.set(database='postgres'),isolation_level='AUTOCOMMIT',connect_args={'connect_timeout':5}).connect() as db:
        db.execute(text('CREATE DATABASE "'+name+'"'))
    with (folder/'migration.log').open('w',encoding='utf-8') as log:
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    os.environ.update(env);sys.path.insert(0,str(ROOT/'backend'))
    from sqlalchemy.orm import Session
    from app.content_import import _import_data,load_content
    from app.interactive_content import import_pack,load_pack
    from app.models import User,UserProfile,UserPreferences,utcnow
    from app.curriculum_models import Lesson,CefrLevel
    from app.security import hash_password
    fixture={'password':token_urlsafe(24)}
    with Session(create_engine(target,connect_args={'connect_timeout':5})) as db,db.begin():
        for rank,level in enumerate(('A1','A2','B1','B2','C1','C2'),1):
            if not db.scalar(select(CefrLevel.id).where(CefrLevel.code==level)):
                db.add(CefrLevel(code=level,display_name=level,description=level,rank=rank))
        db.flush();_import_data(db,load_content(ROOT/'backend/content/a1/course.json'))
        pack=load_pack();assert pack.version=='0.1.1'
        import_pack(db,pack)
        for role in ('admin','learner'):
            email=f'admin-browser-{role}-{uuid4().hex[:8]}@example.com';fixture[role]=email
            from pydantic import TypeAdapter,EmailStr
            TypeAdapter(EmailStr).validate_python(email)
            user=User(email=email,role=role,password_hash=hash_password(fixture['password']),email_verified_at=utcnow())
            db.add(user);db.flush()
            db.add(UserProfile(user_id=user.id,display_name='Browser fixture',timezone='Europe/Paris',onboarding_completed_at=utcnow()))
            db.add(UserPreferences(user_id=user.id))
        fixture['lesson_id']=str(db.scalar(select(Lesson.id).where(Lesson.slug=='m08-etre-interactive-lesson')))
    (folder/'fixture.json').write_text(json.dumps(fixture),encoding='utf-8')
    # Only the environment necessary to this API; credentials remain ignored.
    state={'environment':{k:v for k,v in env.items() if k in dict(dotenv_values(ROOT/'.env')) or k in ('DATABASE_URL','REDIS_URL','APP_ENV','ENABLE_DRAFT_LEARNING_PREVIEW','ENABLE_PERSONAL_LEARNING_PREVIEW','PERSONAL_PREVIEW_USER_IDS','FRONTEND_ORIGIN','CORS_ORIGINS','SESSION_COOKIE_NAME','CSRF_COOKIE_NAME','SMTP_HOST','SMTP_PORT','OLLAMA_BASE_URL','SPEECH_WORKER_URL')},'database':name,'fixture':str(folder/'fixture.json')}
    (folder/'state.json').write_text(json.dumps(state),encoding='utf-8')
    print(str(folder/'state.json'))

def serve(path):
    path=Path(path).resolve();assert path.is_relative_to(ROOT/'.publication-private')
    state=json.loads(path.read_text());disposable(state['environment']['DATABASE_URL'])
    os.environ.update(state['environment']);sys.path.insert(0,str(ROOT/'backend'));os.chdir(ROOT/'backend')
    sys.argv=['personal_uvicorn.py','app.main:app','8002',str(path.parent/'stop')]
    runpy.run_path(str(ROOT/'scripts/personal_uvicorn.py'),run_name='__main__')

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='serve':serve(sys.argv[2])
    else:raise SystemExit('Use prepare or serve STATE_FILE')
