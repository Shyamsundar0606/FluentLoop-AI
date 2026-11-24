from datetime import timedelta
from pathlib import Path
from uuid import UUID,uuid4
import os,time
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from app.config import Settings,get_settings
from app.models import User,utcnow
from app.speech.models import AudioAsset
from app.speech import storage
from test_speech import voice,start,upload
from test_learning import _csrf

@pytest.mark.parametrize('overrides',[
 {'APP_ENV':'production','COOKIE_SECURE':True},
 {'ENABLE_PERSONAL_LEARNING_PREVIEW':False},
 {'PERSONAL_PREVIEW_USER_IDS':[]},
 {'FRONTEND_ORIGIN':'https://example.com','CORS_ORIGINS':['https://example.com']},
])
def test_audio_preservation_cannot_enable_outside_personal_scope(overrides):
 values=dict(APP_ENV='development',ENABLE_PERSONAL_LEARNING_PREVIEW=True,PERSONAL_PREVIEW_USER_IDS=[uuid4()],PERSONAL_PRESERVE_RETAINED_AUDIO=True)
 values.update(overrides)
 with pytest.raises(ValidationError):Settings(_env_file=None,**values)

def test_personal_preservation_keeps_expired_assets_but_denies_access_and_allows_explicit_delete(voice,monkeypatch):
 client,sessions,_,_,_=voice
 sid=start(client);response=upload(client,sid,retain=True);assert response.status_code==200
 asset_id=response.json()['input_audio_id']
 root=Path(get_settings().speech_storage_path)
 with sessions.begin() as db:
  user=db.scalar(select(User).where(User.email=='voice@example.com'))
  assets=db.scalars(select(AudioAsset)).all()
  for asset in assets:asset.retention_expires_at=utcnow()-timedelta(seconds=1)
  asset=db.get(AudioAsset,UUID(asset_id))
  file=root/asset.storage_key
  settings=Settings(_env_file=None,APP_ENV='development',ENABLE_PERSONAL_LEARNING_PREVIEW=True,
    PERSONAL_PREVIEW_USER_IDS=[user.id],PERSONAL_PRESERVE_RETAINED_AUDIO=True,speech_storage_path=str(root))
 monkeypatch.setattr(storage,'get_settings',lambda:settings)
 orphan=root/'unowned-test.audio';orphan.write_bytes(b'only disposable test data');old=time.time()-90000;os.utime(orphan,(old,old))
 with sessions() as db:assert storage.cleanup(db)==0
 assert file.exists() and orphan.exists()
 with sessions() as db:assert all(a.deleted_at is None for a in db.scalars(select(AudioAsset)))
 assert client.get('/api/v1/speech/audio/'+asset_id).status_code==404
 assert client.delete('/api/v1/speech/audio/'+asset_id,headers=_csrf(client)).status_code==200
 assert not file.exists() and orphan.exists()

def test_default_retention_still_expires_disposable_audio(voice):
 client,sessions,_,_,_=voice
 response=upload(client,start(client),retain=True);assert response.status_code==200
 asset_id=UUID(response.json()['input_audio_id'])
 assert get_settings().personal_preserve_retained_audio is False
 with sessions.begin() as db:
  asset=db.get(AudioAsset,asset_id);asset.retention_expires_at=utcnow()-timedelta(seconds=1)
  file=storage.path_for(asset.storage_key)
 with sessions() as db:assert storage.cleanup(db)>=1
 assert not file.exists()
 with sessions() as db:assert db.get(AudioAsset,asset_id).deleted_at is not None
