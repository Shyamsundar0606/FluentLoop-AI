"""Run only against a disposable fluentloop_m05_* database, never main/preview.

Downgrade discards AI test memory. It must preserve every pre-M05 row byte-for-byte.
"""

import os
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = os.environ["DATABASE_URL"]
assert make_url(url).database.startswith(
    "fluentloop_m05_"
), "Refusing non-isolated database"
engine = create_engine(url)
tables = (
    "users",
    "user_profiles",
    "user_preferences",
    "lessons",
    "courses",
    "units",
    "learning_sessions",
    "learning_session_exercises",
    "exercise_attempts",
    "lesson_progress",
    "learning_activity_events",
)


def snapshot():
    with engine.connect() as connection:
        return {
            table: connection.execute(
                text(
                    f"SELECT count(*), md5(coalesce(string_agg(row_to_json(t)::text, '' ORDER BY id),'')) FROM {table} t"
                )
            ).one()
            for table in tables
        }


config = Config("alembic.ini")
before = snapshot()
command.upgrade(config, "head")
assert snapshot() == before
command.downgrade(config, "20261102_0004")
assert snapshot() == before
command.upgrade(config, "head")
assert snapshot() == before
print(
    "PASS: populated upgrade / downgrade / re-upgrade; all pre-M05 row counts and content hashes unchanged"
)
print({table: row[0] for table, row in before.items()})
engine.dispose()
