"""Read-only preservation snapshots, and optional isolated-only rollback check.

Run from backend with PYTHONPATH=. and DATABASE_URL. Main/preview use snapshots
only. Rollback is restricted to the new disposable personalization database.
"""

import json
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from alembic import command
from alembic.config import Config

url = os.environ["DATABASE_URL"]
engine = create_engine(url)


def snapshot():
    tables = sorted(
        t for t in inspect(engine).get_table_names() if t != "alembic_version"
    )
    with engine.connect() as conn:
        # Exclude only the new nullable field to compare preexisting profile data.
        return {
            table: list(
                conn.execute(
                    text(
                        f"SELECT count(*), md5(coalesce(string_agg((to_jsonb(t) - 'registration_age_band')::text, '' ORDER BY (to_jsonb(t) - 'registration_age_band')::text), '')) FROM \"{table}\" t"
                    )
                ).one()
            )
            for table in tables
        }


if len(sys.argv) > 1 and sys.argv[1] == "rollback-test":
    assert make_url(url).database == "fluentloop_m05_personalization"
    config = Config("alembic.ini")
    before = snapshot()
    command.upgrade(config, "head")
    assert snapshot() == before
    command.downgrade(config, "20261102_0005")
    assert snapshot() == before
    command.upgrade(config, "head")
    assert snapshot() == before
    print(
        "PASS: additive profile migration, rollback and re-upgrade preserved every old table row"
    )
else:
    print(json.dumps(snapshot(), sort_keys=True))
engine.dispose()
