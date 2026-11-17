"""CLI-only controls for explicitly disposable RC tests; never an API route."""
import hashlib
import json
import os
from pathlib import Path
import sys

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]


def current_database():
    if os.getenv("RC_DISPOSABLE_TEST") != "1":
        raise SystemExit("Explicit disposable RC testing flag required.")
    state = json.loads((ROOT / ".publication-private/integration-wsl/state.json").read_text())
    fixture = json.loads((ROOT / ".publication-private/m08/m09-manual-fixture.json").read_text())
    if (state["postgres_port"], state["username"]) != (55432, "fluentloop_test"):
        raise SystemExit("Dedicated disposable cluster required.")
    options = dict(host="127.0.0.1", port=55432, user=state["username"], password=state["password"])
    readonly = {**options, "options": "-c default_transaction_read_only=on"}
    with psycopg.connect(dbname="postgres", **readonly) as db:
        names = db.execute("SELECT datname FROM pg_database WHERE datname LIKE 'fluentloop_m08_3_test_%'").fetchall()
    matches = []
    for (name,) in names:
        with psycopg.connect(dbname=name, **readonly) as db:
            if db.execute("SELECT EXISTS(SELECT 1 FROM users WHERE email=%s)", (fixture["email"],)).fetchone()[0]:
                matches.append(name)
    if len(matches) != 1:
        raise SystemExit("The active fixture must identify exactly one disposable demo.")
    return {**options, "dbname": matches[0]}


def main():
    payload = json.load(sys.stdin)
    if payload.get("action") != "expire" or payload.get("kind") not in ("verification", "reset"):
        raise SystemExit("Unsupported test operation.")
    email = payload["email"]
    if not email.startswith("rc-mail-") or not email.endswith("@example.com"):
        raise SystemExit("Only explicitly named synthetic RC mail accounts can change.")
    table = "email_verification_tokens" if payload["kind"] == "verification" else "password_reset_tokens"
    with psycopg.connect(**current_database()) as db:
        changed = db.execute(sql.SQL("UPDATE {} SET expires_at=now()-interval '1 minute' WHERE token_hash=%s "
            "AND user_id=(SELECT id FROM users WHERE email=%s)").format(sql.Identifier(table)),
            (hashlib.sha256(payload["token"].encode()).hexdigest(), email)).rowcount
        if changed != 1:
            raise SystemExit("Expected one owned synthetic token.")
    print("Synthetic token expiration applied.")


if __name__ == "__main__":
    main()
