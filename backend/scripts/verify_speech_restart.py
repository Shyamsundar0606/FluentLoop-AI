"""Continue an existing isolated speech session after an actual API restart."""
import os
from uuid import uuid4
import httpx
from sqlalchemy import select,exists
from sqlalchemy.engine import make_url
from app.core.database import SessionLocal
from app.models import User
from app.speech.models import SpeechSession,SpeechTurn

assert make_url(os.environ['DATABASE_URL']).database.startswith('fluentloop_m06_')
with SessionLocal() as db:
    uid=db.scalar(select(User.id).where(User.email=='ai-browser@example.com'))
    session=db.scalar(select(SpeechSession).where(SpeechSession.user_id==uid,SpeechSession.status=='active',
        exists(select(SpeechTurn.id).where(SpeechTurn.speech_session_id==SpeechSession.id,SpeechTurn.status=='success')))
        .order_by(SpeechSession.created_at).limit(1))
    assert session;sid=str(session.id)
with httpx.Client(base_url='http://127.0.0.1:8016',headers={'Origin':'http://127.0.0.1:3016'},timeout=30) as client:
    assert client.post('/api/v1/auth/login',json={'email':'ai-browser@example.com','password':'IsolatedBrowserTest2026!'}).status_code==200
    before=client.get('/api/v1/speech/sessions/'+sid);assert before.status_code==200 and before.json()['turns']
    rid=str(uuid4());payload={'message':'Bonjour, continuons après le redémarrage.','request_id':rid}
    headers={'X-CSRF-Token':client.cookies.get('fluentloop_csrf')}
    first=client.post('/api/v1/speech/sessions/'+sid+'/text',json=payload,headers=headers);assert first.status_code==200,first.text
    repeated=client.post('/api/v1/speech/sessions/'+sid+'/text',json=payload,headers=headers)
    assert repeated.json()['id']==first.json()['id']
print('PASS: old speech session survives API process restart and continues with idempotent replay')
