"""Explicit live-fixture observations, not a pronunciation-scoring benchmark."""
import json
import time
import wave
from io import BytesIO
from pathlib import Path
import numpy as np
from app.speech.french_tts_provider import synthesize
from app.speech.faster_whisper_provider import transcribe
from app.speech.schemas import Transcription
from app.speech.pronunciation_service import assess


def pcm(samples,rate=16000):
    buf=BytesIO()
    with wave.open(buf,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(np.asarray(samples,dtype='<i2').tobytes())
    return buf.getvalue()


def speed(data,factor):
    with wave.open(BytesIO(data),'rb') as w:
        return pcm(np.frombuffer(w.readframes(w.getnframes()),dtype='<i2'),round(w.getframerate()*factor))


if __name__=='__main__':
    target='Bonjour, je voudrais une baguette, s’il vous plaît.'
    matching=synthesize(target)
    cases={'matching_synthetic_phrase':matching,'different_spoken_word':synthesize('Bonjour, je voudrais un café, s’il vous plaît.'),
        'silence':pcm(np.zeros(16000)),'background_noise':pcm(np.random.default_rng(42).normal(0,1200,16000)),
        'clipped_signal':pcm(np.full(16000,32767)),
        'short_human_word':(Path(__file__).resolve().parents[1]/'tests/fixtures/speech/fr-bonjour.ogg').read_bytes(),
        'slower_rate_fixture':speed(matching,.85),'faster_rate_fixture':speed(matching,1.15),
        'incomplete_phrase':synthesize('Bonjour, je voudrais...'),'unrelated_french':synthesize('Le chat dort dans le jardin.')}
    rows=[]
    for name,data in cases.items():
        start=time.monotonic();result=Transcription.model_validate(transcribe(data));feedback=assess(target,result)
        assert feedback['assessment_status'] in {'not_available','insufficient_audio'}
        if name=='silence':assert result.status=='no_speech'
        if name=='clipped_signal':assert result.status=='insufficient_audio'
        rows.append({'fixture':name,'transcription':result.model_dump(),'recognition_feedback':feedback,'elapsed_seconds':round(time.monotonic()-start,3)})
        print(name,result.status,'acoustic:',feedback['assessment_status'])
    destination=Path(__file__).resolve().parents[2]/'docs/verification/MILESTONE_06_SPEECH_OBSERVATIONS.json'
    destination.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved actual observations; no human-calibrated pronunciation scores were computed.')
