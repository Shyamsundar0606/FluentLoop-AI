"""Real HTTP/ASR/Ollama/Piper integration on the guarded M07 test API only."""
import json
import os
from pathlib import Path
from uuid import uuid4
import httpx
from sqlalchemy.engine import make_url

assert os.getenv('STUDY_E2E_TEST_SERVER')=='1'
assert make_url(os.environ['DATABASE_URL']).database.startswith('fluentloop_m07_')
root=Path(__file__).resolve().parents[2]
result={}
with httpx.Client(base_url='http://127.0.0.1:8017/api/v1',headers={'Origin':'http://127.0.0.1:3017'},timeout=180) as client:
    login=client.post('/auth/login',json={'email':'study-browser@example.com','password':'IsolatedStudyTest2026!'})
    assert login.status_code==200,login.text
    client.headers['X-CSRF-Token']=client.cookies.get('fluentloop_csrf')
    plan=client.post('/study/today/generate',json={'request_id':str(uuid4())})
    assert plan.status_code==200,plan.text
    saved=plan.json()
    for kind in ('tutor','speaking'):
        activity=next(a for a in saved['activities'] if a['activity_type']==kind)
        started=client.post('/study/activities/'+activity['id']+'/start')
        assert started.status_code==200,started.text
        linked=started.json()['url'].split('/')[-1]
        rid=str(uuid4())
        for attempt in range(2):
            if kind=='tutor':
                response=client.post('/ai/conversations/'+linked+'/messages',json={'request_id':rid,'message':"Bonjour, je voudrais pratiquer le français."})
            else:
                response=client.post('/speech/sessions/'+linked+'/turns',data={'request_id':rid,'retain_audio':'false'},
                    files={'audio':('human-french.ogg',(root/'backend/tests/fixtures/speech/fr-bonjour.ogg').read_bytes(),'audio/ogg')})
            if response.status_code!=503:break
        assert response.status_code==200,response.text
        body=response.json()
        if kind=='speaking':
            assert body['transcription_status']=='transcribed',body
            assert body['tutor_audio']['status']=='ready',body
            audio=client.get('/speech/audio/'+body['tutor_audio']['asset_id'])
            assert audio.status_code==200 and audio.content.startswith(b'RIFF')
            result[kind]={'transcript':body['transcript'],'reply':body['tutor']['answer'],'tts_bytes':len(audio.content),'attempts':attempt+1}
        else:
            assert body['answer']
            result[kind]={'model':body['model'],'reply':body['answer'],'attempts':attempt+1}
        completion=client.post('/study/activities/'+activity['id']+'/complete')
        assert completion.status_code==200,completion.text
        assert next(a for a in completion.json()['activities'] if a['id']==activity['id'])['status']=='completed'
    result['plan_id']=saved['id']
    result['plan_after_interactions']=client.get('/study/today').json()
    assert result['plan_after_interactions']['id']==saved['id']
    assert all(a['status']=='completed' for a in result['plan_after_interactions']['activities'] if a['activity_type'] in ('tutor','speaking'))
    client.post('/auth/logout')
    assert client.post('/auth/login',json={'email':'study-browser@example.com','password':'IsolatedStudyTest2026!'}).status_code==200
    assert client.get('/study/today').json()['id']==saved['id']
    result['resumed_after_login']=True
(root/'docs/verification/MILESTONE_07_LIVE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: real linked tutor, human French ASR, Ollama, Piper audio, plan completion and login persistence.')
