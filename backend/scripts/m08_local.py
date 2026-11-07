"""Explicit isolated local M08 verification. Never migrates an application DB.

Run from the project root with .venv312/Scripts/python.exe backend/scripts/m08_local.py setup|api|worker|tests|preservation.
Private connection settings and synthetic browser expectations stay ignored.
"""
import json,os,re,subprocess,sys
from pathlib import Path
from uuid import uuid4
from secrets import token_urlsafe
from sqlalchemy.engine import make_url
import psycopg
from psycopg import sql

sys.stdout.reconfigure(encoding='utf-8',errors='replace')

ROOT=Path(__file__).resolve().parents[2]
PRIVATE=ROOT/'.publication-private/m08'
STATE=PRIVATE/'local.json'
env={m[1]:m[2].strip('\"\'') for line in (ROOT/'.env').read_text(encoding='utf-8-sig').splitlines() if (m:=re.match(r'([A-Z][A-Z0-9_]*)=(.*)',line))}
base=make_url(env['DATABASE_URL']).set(host='127.0.0.1')
secrets=[v for k,v in env.items() if any(s in k for s in ('PASSWORD','TOKEN','SECRET')) and v]
if base.password:secrets.append(base.password)


def safe(body):
    for secret in secrets:body=body.replace(secret,'[REDACTED]')
    return body


def run(args,extra,cwd=ROOT/'backend',log=None):
    result=subprocess.run(args,cwd=cwd,env={**os.environ,**env,**extra},capture_output=True,text=True,encoding='utf-8',errors='replace')
    output=safe(result.stdout+result.stderr)
    if log:(PRIVATE/log).write_text(output,encoding='utf-8')
    print(output)
    if result.returncode:raise SystemExit(result.returncode)


def database(prefix):
    assert prefix.startswith('fluentloop_m')
    name=prefix+uuid4().hex[:10]
    with psycopg.connect(host=base.host,port=base.port or 5432,user=base.username,password=base.password,dbname='postgres',autocommit=True) as db:
        db.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    return base.set(database=name).render_as_string(hide_password=False)


def setup():
    PRIVATE.mkdir(parents=True,exist_ok=True)
    if STATE.exists():raise SystemExit('An isolated M08 environment already exists. Reuse it; no application DB was changed.')
    extra=dict(DATABASE_URL=database('fluentloop_m08_local_'),PYTHONPATH=str(ROOT/'backend'),
        REDIS_URL='redis://127.0.0.1:6379/14',APP_ENV='development',
        FRONTEND_ORIGIN='http://127.0.0.1:3008',CORS_ORIGINS='["http://127.0.0.1:3008"]',
        SMTP_HOST='127.0.0.1',SMTP_PORT='1025',ENABLE_DRAFT_LEARNING_PREVIEW='true',
        OLLAMA_BASE_URL='http://127.0.0.1:11434',OLLAMA_MODEL=env.get('OLLAMA_MODEL','llama3.2:3b'),
        SPEECH_WORKER_URL='http://127.0.0.1:8098',SPEECH_MODEL_PATH=str(ROOT/'.speech-models'),
        SPEECH_ASR_MODEL='base',SPEECH_STORAGE_PATH=str(ROOT/'.speech-data/m08-local'))
    run([sys.executable,'-m','alembic','upgrade','head'],extra)
    os.environ.update({**env,**extra})
    sys.path.insert(0,str(ROOT/'backend'))
    from app.core.database import SessionLocal
    from app.curriculum_models import CefrLevel,Lesson,Exercise,ExerciseOption
    from app.content_import import _import_data,load_content
    from app.interactive_content import import_pack,load_pack
    from app.models import User,UserProfile,UserPreferences,utcnow
    from app.security import hash_password
    from sqlalchemy import select
    from app.services.interactive_learning import library
    fixture={'password':token_urlsafe(24)}
    with SessionLocal.begin() as db:
        for n,level in enumerate(('A1','A2','B1','B2','C1','C2'),1):
            if not db.scalar(select(CefrLevel).where(CefrLevel.code==level)):db.add(CefrLevel(code=level,display_name=level,description=level,rank=n))
        db.flush();_import_data(db,load_content(ROOT/'backend/content/a1/course.json'))
        print('Draft module import:',json.dumps(import_pack(db,load_pack())))
        print('Idempotent import:',json.dumps(import_pack(db,load_pack())))
        for role in ('admin','learner'):
            email=f'm08-{role}-{uuid4().hex[:8]}@example.com';fixture[role]=email
            user=User(email=email,role=role,password_hash=hash_password(fixture['password']),email_verified_at=utcnow())
            db.add(user);db.flush()
            db.add(UserProfile(user_id=user.id,display_name='Interactive learner',timezone='Europe/Paris',onboarding_completed_at=utcnow()))
            db.add(UserPreferences(user_id=user.id))
        lesson=db.scalar(select(Lesson).where(Lesson.slug=='m08-etre-interactive-lesson'))
        fixture['lesson_id']=str(lesson.id)
    STATE.write_text(json.dumps(extra),encoding='utf-8')
    folder=ROOT/'.speech-data';folder.mkdir(exist_ok=True)
    (folder/'m08-browser-fixture.json').write_text(json.dumps(fixture),encoding='utf-8')
    print('Isolated database ready. Main and preview schemas unchanged. Local browser account details remain in ignored .speech-data/m08-browser-fixture.json.')


def tests():
    extra=dict(PYTHONPATH=str(ROOT/'backend'),DATABASE_URL=base.render_as_string(hide_password=False),
        REDIS_URL='redis://127.0.0.1:6379/14',
        STUDY_TEST_ADMIN_DATABASE_URL=base.set(database='postgres').render_as_string(hide_password=False),
        A1_TEST_ADMIN_DATABASE_URL=base.set(database='postgres').render_as_string(hide_password=False),
        M08_TEST_ADMIN_DATABASE_URL=base.set(database='postgres').render_as_string(hide_password=False))
    for key,prefix in [('AI_TEST_DATABASE_URL','fluentloop_m05_m08_'),('SPEECH_TEST_DATABASE_URL','fluentloop_m06_m08_')]:
        extra[key]=database(prefix)
        run([sys.executable,'-m','alembic','upgrade','head'],{**extra,'DATABASE_URL':extra[key]})
    run([str(ROOT/'.venv-speech/Scripts/python.exe'),'-m','pytest','tests','-ra'],extra,log='backend-tests.log')


def preservation():
    before=json.loads((PRIVATE/'baseline.json').read_text())
    report={}
    for name,key,port in [('main','DATABASE_URL',5432),('preview','PREVIEW_DATABASE_URL',5433)]:
        url=make_url(env[key]);changed=[]
        with psycopg.connect(host='127.0.0.1',port=port,user=url.username,password=url.password,dbname=url.database) as db:
            for table,expected in before[name]['tables'].items():
                actual=list(db.execute(sql.SQL("SELECT count(*),md5(coalesce(string_agg(to_jsonb(t)::text,'' ORDER BY to_jsonb(t)::text),'')) FROM {} t").format(sql.Identifier(table))).fetchone())
                if actual!=expected:changed.append(table)
            revision=db.execute('SELECT version_num FROM alembic_version').fetchone()[0]
            draft,published=db.execute("SELECT count(*) FILTER(WHERE status='draft'),count(*) FILTER(WHERE status='published') FROM lessons").fetchone()
        report[name]=dict(tables_verified=len(before[name]['tables']),changed_tables=changed,revision=revision,
            revision_unchanged=revision==before[name]['revision'],draft_lessons=draft,published_lessons=published)
    (PRIVATE/'preservation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


def legacy(kind):
    """Existing guarded browser fixtures, each in its own new test database."""
    speech=kind=='legacy-speech'
    extra=dict(DATABASE_URL=database('fluentloop_m06_m08_browser_' if speech else 'fluentloop_m07_m08_browser_'),
        PYTHONPATH=str(ROOT/'backend'),APP_ENV='development',AI_E2E_TEST_SERVER='1',STUDY_E2E_TEST_SERVER='1',
        REDIS_URL='redis://127.0.0.1:6379/14',SMTP_HOST='127.0.0.1',SMTP_PORT='1025',
        FRONTEND_ORIGIN='http://127.0.0.1:3011',CORS_ORIGINS='["http://127.0.0.1:3011"]',
        ENABLE_DRAFT_LEARNING_PREVIEW='true',SPEECH_STORAGE_PATH=str(ROOT/'.speech-data/m08-browser'))
    run([sys.executable,'-m','alembic','upgrade','head'],extra)
    if not speech:
        run([sys.executable,'-m','app.content_import','--apply'],extra)
        run([sys.executable,'scripts/prepare_study_browser.py'],extra)
    (PRIVATE/f'{kind}.json').write_text(json.dumps(extra),encoding='utf-8')
    os.environ.update({**env,**extra});sys.path.insert(0,str(ROOT/'backend'))
    import uvicorn
    uvicorn.run('scripts.speech_e2e_server:app' if speech else 'scripts.study_e2e_server:app',host='127.0.0.1',port=8018 if speech else 8019)


def curriculum_browsers():
    from sqlalchemy import create_engine,select
    from sqlalchemy.orm import Session
    sys.path.insert(0,str(ROOT/'backend'))
    from app.curriculum_models import Lesson,Exercise,ExerciseOption
    from app.models import User,UserProfile,UserPreferences,utcnow
    from app.security import hash_password
    extra=json.loads((PRIVATE/'legacy-study.json').read_text())
    assert make_url(extra['DATABASE_URL']).database.startswith('fluentloop_m07_m08_browser_')
    fixture=json.loads((ROOT/'.speech-data/m07-browser-fixture.json').read_text())
    with Session(create_engine(extra['DATABASE_URL'])) as db:
        fixture={}
        for role in ('admin','learner'):
            email=f'm08-regression-{role}-{uuid4().hex[:8]}@example.com';fixture[role]=email
            user=User(email=email,role=role,password_hash=hash_password('IsolatedStudyTest2026!'),email_verified_at=utcnow())
            db.add(user);db.flush()
            db.add(UserProfile(user_id=user.id,display_name='Regression learner',onboarding_completed_at=utcnow()))
            db.add(UserPreferences(user_id=user.id))
        db.commit()
        lessons=db.scalars(select(Lesson).order_by(Lesson.slug)).all()
        lesson=next(l for l in lessons if l.slug=='a1-003')
        options=[]
        for exercise in db.scalars(select(Exercise).where(Exercise.lesson_id==lesson.id).order_by(Exercise.sequence_order)):
            rows=db.scalars(select(ExerciseOption).where(ExerciseOption.exercise_id==exercise.id)).all()
            options.append(dict(correct_id=str(next(o.id for o in rows if o.is_correct)),wrong_id=str(next(o.id for o in rows if not o.is_correct))))
        extra.update(PLAYWRIGHT_BASE_URL='http://127.0.0.1:3011',PLAYWRIGHT_API_BASE_URL='http://127.0.0.1:8019/api/v1',
            A1_E2E_REAL_API='1',A1_E2E_EMAIL=fixture['admin'],A1_E2E_PASSWORD='IsolatedStudyTest2026!',
            A1_E2E_LESSONS=json.dumps([dict(id=str(l.id),slug=l.slug,title=l.title) for l in lessons]),
            M04_LIVE_EMAIL=fixture['admin'],M04_LIVE_PASSWORD='IsolatedStudyTest2026!',
            M04_LEARNER_EMAIL=fixture['learner'],M04_LEARNER_PASSWORD='IsolatedStudyTest2026!',
            M04_LIVE_LESSON_ID=str(lesson.id),M04_LIVE_OPTIONS=json.dumps(options),
            M04_LIVE_API_BASE='http://127.0.0.1:8019/api/v1',M04_LIVE_FRONTEND_ORIGIN='http://127.0.0.1:3011')
    run(['npx.cmd','playwright','test','a1-curriculum.spec.ts','milestone04-live.spec.ts','--workers=1'],extra,ROOT/'frontend',log='curriculum-browser.log')


def preview_account():
    """Read-only validation of the pre-existing, verified synthetic admin."""
    extra=json.loads(STATE.read_text(encoding='utf-8'))
    url=make_url(extra['DATABASE_URL'])
    if not (url.host in ('localhost','127.0.0.1') and url.database.startswith('fluentloop_m08_local_')
            and extra.get('APP_ENV')=='development' and extra.get('FRONTEND_ORIGIN')=='http://127.0.0.1:3008'):
        raise SystemExit('Refusing access helper outside the isolated local M08 development environment.')
    fixture=json.loads((ROOT/'.speech-data/m08-browser-fixture.json').read_text(encoding='utf-8'))
    email=fixture['admin']
    if not (email.startswith('m08-admin-') and email.endswith('@example.com')):
        raise SystemExit('Designated account is not the existing synthetic M08 admin.')
    with psycopg.connect(host=url.host,port=url.port or 5432,user=url.username,password=url.password,dbname=url.database) as db:
        db.execute('SET TRANSACTION READ ONLY')
        row=db.execute('SELECT role,is_active,email_verified_at IS NOT NULL,password_hash FROM users WHERE email=%s',(email,)).fetchone()
        if not row or row[:3]!=('admin',True,True):
            raise SystemExit('The designated account must already be active, verified and authorized. No account permissions were changed.')
    return extra,email,row[3]


def prepare_preview():
    extra,_,_=preview_account()
    extra.update(ENABLE_DRAFT_LEARNING_PREVIEW='true',SESSION_COOKIE_NAME='fluentloop_m08_session',
        CSRF_COOKIE_NAME='fluentloop_m08_csrf')
    os.environ.update({**env,**extra});sys.path.insert(0,str(ROOT/'backend'))
    from app.core.database import SessionLocal
    from app.interactive_content import import_pack,load_pack
    from sqlalchemy import text
    with SessionLocal.begin() as db:
        if db.execute(text('SELECT version_num FROM alembic_version')).scalar()!='20261104_0009':
            raise SystemExit('M08 schema is not ready. No migration was applied to any application database.')
        result=import_pack(db,load_pack())
    STATE.write_text(json.dumps(extra),encoding='utf-8')
    print('Prepared existing isolated preview. Existing verified admin reused; learner roles and verification unchanged.')
    print(json.dumps(result))


def copy_signin(field):
    _,email,hashed=preview_account()
    # This is the pre-existing synthetic fixture password, never a production
    # credential. Validate it rather than changing an account behind the user.
    sys.path.insert(0,str(ROOT/'backend'))
    from app.security import verify_password
    value=email
    if field=='password':
        fixture=json.loads((ROOT/'.speech-data/m08-browser-fixture.json').read_text(encoding='utf-8'))
        value=fixture.get('password')
        if not value:
            raise SystemExit('The private fixture password is missing. Restore it from the local fixture backup.')
        if not verify_password(hashed,value):
            raise SystemExit('The fixture password changed. Use the normal email password-reset flow; no password was modified.')
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',
        '$value=[Console]::In.ReadToEnd(); Set-Clipboard -Value $value'],input=value,capture_output=True,text=True)
    if result.returncode:raise SystemExit('Clipboard access failed. No credential was printed.')
    print(f'Copied isolated preview {field} to the local clipboard. Paste into http://127.0.0.1:3008/login, then clear the clipboard.')


def import_grammar():
    extra, _, _ = preview_account()
    os.environ.update({**env, **extra})
    sys.path.insert(0, str(ROOT/'backend'))
    from sqlalchemy import text
    from app.core.database import SessionLocal
    from app.grammar_content import import_supplement, load_supplement

    if not (PRIVATE/'m08_3_baseline.json').is_file():
        raise SystemExit('Capture the isolated M08 baseline before applying the grammar release.')
    with SessionLocal.begin() as db:
        if db.execute(text('SELECT version_num FROM alembic_version')).scalar_one() != '20261104_0009':
            raise SystemExit('The isolated grammar release requires schema 0009.')
        # Serialize local imports so a concurrent retry observes the same batch.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext('fluentloop-m083-a1-grammar'))"))
        result = import_supplement(db, load_supplement())
    print(json.dumps(result))


if __name__=='__main__':
    action=sys.argv[1]
    if action=='setup':setup()
    elif action=='tests':tests()
    elif action=='preservation':preservation()
    elif action in ('legacy-speech','legacy-study'):legacy(action)
    elif action=='curriculum-browsers':curriculum_browsers()
    elif action=='prepare-preview':prepare_preview()
    elif action=='import-grammar':import_grammar()
    elif action in ('copy-email','copy-password'):copy_signin(action.removeprefix('copy-'))
    elif action=='study-accounts':
        extra=json.loads((PRIVATE/'legacy-study.json').read_text())
        run([sys.executable,'scripts/prepare_study_browser.py'],extra)
    else:
        extra=json.loads(STATE.read_text())
        assert make_url(extra['DATABASE_URL']).database.startswith('fluentloop_m08_local_')
        os.environ.update({**env,**extra});sys.path.insert(0,str(ROOT/'backend'))
        if action=='api':
            from app.services import rate_limit
            class Namespace:
                def __init__(self,client):self.client=client;self.prefix='m08-local:'+uuid4().hex+':'
                def eval(self,script,count,key,*args):return self.client.eval(script,count,self.prefix+key,*args)
                def ttl(self,key):return self.client.ttl(self.prefix+key)
            rate_limit.redis_client=Namespace(rate_limit.redis_client)
            import uvicorn
            uvicorn.run('app.main:app',host='127.0.0.1',port=8008)
        elif action=='worker':
            import uvicorn
            uvicorn.run('app.speech.worker:app',host='127.0.0.1',port=8098)
        else:raise SystemExit('Unknown action')
