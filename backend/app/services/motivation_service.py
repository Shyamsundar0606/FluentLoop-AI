"""Explicit, idempotent rewards derived from completed persisted activities."""
from datetime import timedelta

from sqlalchemy import func, literal, select

from app.ai.models import Conversation, Message
from app.learning_models import LearningSession, WritingSubmission
from app.services import spaced_repetition_service, study_clock as clock, study_content
from app.study_models import LearningAchievement, LearningReward, ReviewAttempt, ReviewCard, ReviewItem, ReviewSession

XP = dict(lesson=20, practice=10, assessment=15, writing=10, conversation=15, vocabulary_review=5)
ACHIEVEMENTS = (
    ("first_lesson", "First lesson completed", LearningReward.kind == "lesson", 1),
    ("first_conversation", "First conversation completed", LearningReward.kind == "conversation", 1),
    ("first_writing", "First writing activity", LearningReward.kind == "writing", 1),
    ("first_vocabulary_review", "First vocabulary review", LearningReward.kind == "vocabulary_review", 1),
    ("five_grammar", "Five grammar activities", LearningReward.activity_type.like("%:grammar:%"), 5),
)


def streaks(days, today):
    days = sorted({day for day in days if day <= today})
    best, run, previous = 0, 0, None
    for day in days:
        run = run + 1 if previous is not None and day == previous + timedelta(days=1) else 1
        best, previous = max(best, run), day
    available = set(days)
    cursor = today if today in available else today - timedelta(days=1)
    current = 0
    while cursor in available:
        current += 1
        cursor -= timedelta(days=1)
    return current, best


def summary(db, user):
    today, zone = clock.study_date(clock.now(), user.profile.timezone if user.profile else "UTC")
    days = db.scalars(select(LearningReward.study_date).where(LearningReward.user_id == user.id).distinct()).all()
    current, best = streaks(days, today)
    titles = {key: title for key, title, _, _ in ACHIEVEMENTS}
    earned = db.scalars(select(LearningAchievement).where(LearningAchievement.user_id == user.id)
        .order_by(LearningAchievement.earned_at, LearningAchievement.id)).all()
    return dict(enabled=user.preferences.motivation_enabled, timezone=zone,
        total_xp=db.scalar(select(func.coalesce(func.sum(LearningReward.xp), 0)).where(LearningReward.user_id == user.id)),
        today_activities=db.scalar(select(func.count()).select_from(LearningReward).where(
            LearningReward.user_id == user.id, LearningReward.study_date == today)),
        current_streak=current, best_streak=best, xp_policy=XP,
        achievements=[dict(key=row.achievement_key, title=titles.get(row.achievement_key, row.achievement_key), earned_at=row.earned_at) for row in earned],
        notice="XP records completed activities. It does not measure French proficiency.")


def sources(db, user):
    completed = select(LearningSession.id, LearningSession.completed_at.label("earned_at"), LearningSession.activity_key.label("activity_type")).where(
        LearningSession.user_id == user.id, LearningSession.status == "completed", LearningSession.preview_mode.is_(False),
        LearningSession.total_exercises > 0, LearningSession.current_exercise_position >= LearningSession.total_exercises)
    result = [
        ("lesson", LearningSession, completed.where(LearningSession.activity_key == "lesson")),
        ("practice", LearningSession, completed.where(LearningSession.activity_key.like("practice:%"))),
        ("assessment", LearningSession, completed.where(LearningSession.activity_key.like("assessment:%"))),
        ("writing", WritingSubmission, select(WritingSubmission.id, WritingSubmission.created_at.label("earned_at"), literal("writing").label("activity_type")).where(
            WritingSubmission.user_id == user.id, WritingSubmission.preview_mode.is_(False))),
    ]
    user_message = select(Message.id).where(Message.conversation_id == Conversation.id, Message.role == "user", Message.response_status == "success").exists()
    reply = select(Message.id).where(Message.conversation_id == Conversation.id, Message.role == "assistant",
        Message.response_status == "success", Message.model_name.is_not(None)).exists()
    result.append(("conversation", Conversation, select(Conversation.id, Conversation.completed_at.label("earned_at"), literal("conversation").label("activity_type")).where(
        Conversation.user_id == user.id, Conversation.completed_at.is_not(None), Conversation.preview_mode.is_(False), user_message, reply)))
    published_words = set()
    for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
        published_words.update(key for key, value in study_content.vocabulary(db, user, level).items() if not value["draft_preview"])
    invalid_item = select(ReviewItem.id).join(ReviewCard, ReviewCard.id == ReviewItem.card_id).where(
        ReviewItem.session_id == ReviewSession.id, ~ReviewCard.word_sense_id.in_(published_words)).exists()
    item_count = select(func.count(ReviewItem.id)).where(ReviewItem.session_id == ReviewSession.id).correlate(ReviewSession).scalar_subquery()
    answer_count = select(func.count(ReviewAttempt.id)).where(ReviewAttempt.session_id == ReviewSession.id,
        ReviewAttempt.user_id == user.id).correlate(ReviewSession).scalar_subquery()
    result.append(("vocabulary_review", ReviewSession, select(ReviewSession.id, ReviewSession.completed_at.label("earned_at"), literal("vocabulary_review").label("activity_type")).where(
        ReviewSession.user_id == user.id, ReviewSession.status == "completed", ReviewSession.completed_at.is_not(None),
        item_count > 0, answer_count >= item_count, ~invalid_item)))
    return result


def sync(db, user):
    spaced_repetition_service.lock_user(db, user)
    if not user.preferences.motivation_enabled:
        return summary(db, user)
    now = clock.now()
    zone = user.profile.timezone if user.profile else "UTC"
    has_more = False
    for kind, model, query in sources(db, user):
        rewarded = select(LearningReward.id).where(LearningReward.user_id == user.id,
            LearningReward.kind == kind, LearningReward.source_id == model.id).exists()
        timestamp = query.selected_columns.earned_at
        rows = db.execute(query.where(~rewarded, timestamp.is_not(None), timestamp <= now)
                          .order_by("earned_at", model.id).limit(1001)).all()
        has_more = has_more or len(rows) > 1000
        for row in rows[:1000]:
            day, timezone = clock.study_date(row.earned_at, zone)
            db.add(LearningReward(user_id=user.id, kind=kind, source_id=row.id, activity_type=row.activity_type,
                xp=XP[kind], earned_at=row.earned_at, study_date=day, timezone=timezone))
    db.flush()
    existing = set(db.scalars(select(LearningAchievement.achievement_key).where(LearningAchievement.user_id == user.id)).all())
    for key, _, condition, threshold in ACHIEVEMENTS:
        if key in existing:
            continue
        earned_at = db.scalar(select(LearningReward.earned_at).where(LearningReward.user_id == user.id, condition)
            .order_by(LearningReward.earned_at, LearningReward.id).offset(threshold - 1).limit(1))
        if earned_at is not None:
            db.add(LearningAchievement(user_id=user.id, achievement_key=key, earned_at=earned_at))
    db.commit()
    return {**summary(db, user), "has_more": has_more}


def history(db, user, limit, offset):
    rows = db.scalars(select(LearningReward).where(LearningReward.user_id == user.id)
        .order_by(LearningReward.earned_at.desc(), LearningReward.id.desc()).offset(offset).limit(limit + 1)).all()
    return dict(items=[dict(id=str(row.id), kind=row.kind, xp=row.xp, earned_at=row.earned_at,
                           study_date=row.study_date, timezone=row.timezone) for row in rows[:limit]],
                next_offset=offset + limit if len(rows) > limit else None)
