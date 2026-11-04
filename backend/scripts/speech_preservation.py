"""Read-only fingerprints of all pre-M06 data, including registration age bands."""
import json
import os
from sqlalchemy import create_engine,inspect,text

NEW_TABLES={'speech_sessions','speech_turns','speech_audio_assets','pronunciation_attempts','speech_practice_progress'}


def snapshot(url):
    engine=create_engine(url)
    names=sorted(set(inspect(engine).get_table_names())-NEW_TABLES-{'alembic_version'})
    with engine.connect() as connection:
        result={name:list(connection.execute(text(f'SELECT count(*), md5(coalesce(string_agg(to_jsonb(t)::text, \'\' ORDER BY to_jsonb(t)::text),\'\')) FROM "{name}" t')).one()) for name in names}
    engine.dispose()
    return result


if __name__=='__main__':print(json.dumps(snapshot(os.environ['DATABASE_URL']),sort_keys=True))
