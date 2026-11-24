from uuid import uuid4
from sqlalchemy import select
from app.ai.models import Message
from app.ai.providers.base import Generation
from test_speech import voice, start, upload


def responses(tutor, replies):
    values=iter(replies)
    def generate(messages, **kwargs):
        tutor.calls.append(messages)
        return Generation(next(values), 'synthetic-format-test')
    tutor.generate=generate


def test_voice_format_retry_preserves_one_turn_and_synthesizes_only_valid_reply(voice):
    client,sessions,_,speech,tutor=voice
    bad="Bonjour ! Tu aimes la baguette ? Comment vas-tu ?"
    good="Bonjour ! Tu préfères une baguette ou un croissant ?"
    responses(tutor,[bad,good])
    sid=start(client);rid=str(uuid4())
    response=upload(client,sid,rid=rid)
    assert response.status_code==200,response.text
    assert response.json()['tutor']['answer']==good
    assert len(tutor.calls)==2 and speech.tts_calls==1
    assert upload(client,sid,rid=rid).status_code==200
    assert len(tutor.calls)==2 and speech.tts_calls==1
    with sessions() as db:
        messages=list(db.scalars(select(Message)))
        assert len([m for m in messages if m.role=='user'])==1
        assert [m.content for m in messages if m.role=='assistant']==[good]
        assert all(m.content!=bad for m in messages)


def test_voice_format_retry_is_bounded_and_does_not_save_or_speak_rejected_text(voice):
    client,sessions,_,speech,tutor=voice
    bad="Bonjour ! Tu aimes Paris ? Tu habites ici ?"
    responses(tutor,[bad,bad])
    assert upload(client,start(client)).status_code==503
    assert len(tutor.calls)==2 and speech.tts_calls==0
    with sessions() as db:
        assert not db.scalar(select(Message).where(Message.role=='assistant'))
        assert len(list(db.scalars(select(Message).where(Message.role=='user'))))==1


def test_voice_format_retry_still_enforces_source_and_security_validation(voice):
    client,sessions,_,speech,tutor=voice
    responses(tutor,["Bonjour ! Ça va ? Tu habites ici ?", "Lis https://example.com pour apprendre."])
    assert upload(client,start(client)).status_code==503
    assert len(tutor.calls)==2 and speech.tts_calls==0
    with sessions() as db:
        assert not db.scalar(select(Message).where(Message.role=='assistant'))
