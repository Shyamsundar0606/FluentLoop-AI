"""FluentLoop SM-2-inspired v1; deliberately not the original SM-2 algorithm."""
from datetime import timedelta
from app.services.study_clock import utc

VERSION = "fl-sm2-v1"

def schedule(*, repetitions, interval, ease, lapses, correct, rating, at):
    at = utc(at)
    if not correct:
        return dict(state="relearning", repetition_count=0, interval_days=10 / 1440,
                    ease_factor=max(1.3, round(ease - .2, 2)), lapse_count=lapses + 1,
                    next_due_at=at + timedelta(minutes=10), algorithm_version=VERSION)
    ease = min(3., max(1.3, round(ease + {"easy": .15, "difficult": -.15}.get(rating, 0), 2)))
    days = 1 if repetitions == 0 else 3 if repetitions == 1 else min(365, max(1, round(interval * ease)))
    return dict(state="learning" if repetitions == 0 else "review", repetition_count=repetitions + 1,
                interval_days=float(days), ease_factor=ease, lapse_count=lapses,
                next_due_at=at + timedelta(days=days), algorithm_version=VERSION)
