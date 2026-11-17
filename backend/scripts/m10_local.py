"""Assessment demo wrapper around the existing guarded disposable runner."""
import argparse
import json
import socket
import sys
from pathlib import Path
from sqlalchemy.engine import URL

import m083_local as demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("serve", "verify", "copy-email", "copy-password", "copy-learner-email"))
    parser.add_argument("--suite", choices=("curriculum", "coach"), default="curriculum", help="Existing real browser suite for verify")
    parser.add_argument("--webpack", action="store_true", help="Explicitly use webpack for this local build")
    parser.add_argument("--mailpit", action="store_true", help="Use loopback-only disposable Mailpit SMTP on port 1025")
    parser.add_argument("--integration-state", type=Path, help="Private state of the disposable WSL integration services")
    args = parser.parse_args()
    if args.action.startswith("copy-"):
        field = {"copy-email": "email", "copy-password": "password", "copy-learner-email": "learner_email"}[args.action]
        demo.copy_coach(field)
        return 0
    redis_port, redis_url = 6379, None
    if args.integration_state:
        state = json.loads(args.integration_state.read_text(encoding="utf-8"))
        if (state.get("postgres_port"), state.get("redis_port"), state.get("username")) != (55432, 56379, "fluentloop_test"):
            raise SystemExit("Integration state must identify the dedicated disposable test services.")
        demo.local.secrets.append(state["password"])
        demo.local.base = URL.create("postgresql+psycopg", username=state["username"], password=state["password"],
                                    host="127.0.0.1", port=55432, database="postgres")
        redis_port = 56379
        redis_url = f"redis://:{state['password']}@127.0.0.1:56379/13"
    dependencies = [(demo.local.base.host, demo.local.base.port or 5432), ("127.0.0.1", redis_port)]
    if args.mailpit:
        dependencies.extend([("127.0.0.1", 1025), ("127.0.0.1", 8025)])
    for host, port in dependencies:
        try:
            with socket.create_connection((host, port), timeout=3):
                pass
        except OSError:
            raise SystemExit("Start local PostgreSQL and Redis before running the disposable assessment demo.") from None
    sys.argv = [sys.argv[0], "--assessments", *(["--serve-coach"] if args.action == "serve" else []),
                *(["--coach"] if args.action == "verify" and args.suite == "coach" else []),
                *(["--webpack"] if args.webpack else []), *(["--mailpit"] if args.mailpit else [])]
    try:
        return demo.main(redis_url=redis_url)
    except KeyboardInterrupt:
        print("Disposable assessment services stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
