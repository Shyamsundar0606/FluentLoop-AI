from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select, func
from app.models import User
from app.study_models import ReviewCard, ReviewSession, ReviewItem, ReviewAttempt
from app.services import study_clock as clock, study_content as content
from app.services.review_grading_service import grade
from app.services.review_scheduler import schedule

def lock_user(db, user):
    db.scalar(select(User).where(User.id == user.id).with_for_update())

def level_for(user):
    return user.preferences.current_level.upper() if user.preferences else 'A1'

def due(db, user, level=None):
    level = level or level_for(user)
    available = content.vocabulary(db, user, level)
    cards = db.scalars(select(ReviewCard).where(ReviewCard.user_id == user.id, ReviewCard.cefr_level == level).order_by(ReviewCard.next_due_at, ReviewCard.id)).all()
    cards = [c for c in cards if c.word_sense_id in available]
    return dict(cefr_level=level, due_count=sum(clock.utc(c.next_due_at) <= clock.now() for c in cards),
                available_vocabulary_count=len(available),
                new_vocabulary_count=len(set(available) - {c.word_sense_id for c in cards}),
                next_due_at=min((clock.utc(c.next_due_at) for c in cards), default=None))

def owned(db, user, sid, lock=False):
    query = select(ReviewSession).where(ReviewSession.id == sid, ReviewSession.user_id == user.id)
    session = db.scalar(query.with_for_update() if lock else query)
    if not session:
        raise HTTPException(404, 'Review session not found.')
    return session

def items(db, sid):
    return db.scalars(select(ReviewItem).where(ReviewItem.session_id == sid).order_by(ReviewItem.sequence_order)).all()

def feedback(item, attempt):
    return dict(id=attempt.id, item_id=item.id, card_id=item.card_id, submitted_answer=attempt.submitted_answer,
                is_correct=attempt.is_correct, correct_answer=item.snapshot['answers'][0], explanation=item.snapshot['explanation'],
                recall_rating=attempt.recall_rating, next_due_at=attempt.new_due_at)

def view(db, user, session):
    available = content.vocabulary(db, user, session.cefr_level)
    rows = items(db, session.id)
    attempts = {a.item_id:a for a in db.scalars(select(ReviewAttempt).where(ReviewAttempt.session_id == session.id)).all()}
    current = None
    shown = []
    hidden = 0
    for item in rows:
        card = db.get(ReviewCard, item.card_id)
        source = available.get(card.word_sense_id)
        if source is None or source['version'] != item.snapshot['version']:
            hidden += 1
            continue
        if item.id in attempts:
            shown.append(feedback(item, attempts[item.id]))
        elif current is None and session.status == 'active':
            current = dict(item_id=item.id, card_id=card.id, sequence_order=item.sequence_order,
                           prompt=item.snapshot['prompt'], draft_preview=source['draft_preview'])
    return dict(id=session.id, cefr_level=session.cefr_level, status=session.status, total_cards=len(rows),
                answered_cards=len(attempts), unavailable_cards=hidden, current_question=current, feedback=shown)

def start(db, user, payload, *, commit=True):
    lock_user(db, user)
    level = level_for(user)
    previous = db.scalar(select(ReviewSession).where(ReviewSession.user_id == user.id, ReviewSession.request_id == payload.request_id))
    if previous:
        if previous.card_limit != payload.limit or previous.cefr_level != level:
            raise HTTPException(409, 'Request ID belongs to another review selection.')
        return view(db, user, previous)
    active = db.scalar(select(ReviewSession).where(ReviewSession.user_id == user.id, ReviewSession.cefr_level == level, ReviewSession.status == 'active'))
    if active:
        return view(db, user, active)
    available = content.vocabulary(db, user, level)
    at = clock.now()
    cards = db.scalars(select(ReviewCard).where(ReviewCard.user_id == user.id, ReviewCard.cefr_level == level).order_by(ReviewCard.next_due_at, ReviewCard.id)).all()
    selected = [c for c in cards if c.word_sense_id in available and clock.utc(c.next_due_at) <= at][:payload.limit]
    known = {c.word_sense_id for c in cards}
    for sense_id, data in available.items():
        if len(selected) >= payload.limit:
            break
        if sense_id not in known:
            card = ReviewCard(user_id=user.id, word_sense_id=sense_id, cefr_level=level,
                              card_content_version=data['version'], next_due_at=at)
            db.add(card)
            db.flush()
            selected.append(card)
    if not selected:
        raise HTTPException(409, 'No authorized vocabulary is due or available to enroll.')
    session = ReviewSession(user_id=user.id, cefr_level=level, request_id=payload.request_id,
                            card_limit=payload.limit, started_at=at)
    db.add(session)
    db.flush()
    for order, card in enumerate(selected, 1):
        data = available[card.word_sense_id]
        card.card_content_version = data['version']
        db.add(ReviewItem(user_id=user.id, session_id=session.id, card_id=card.id, sequence_order=order,
                           snapshot={k:v for k,v in data.items() if k != 'draft_preview'}))
    db.flush()
    if commit:
        db.commit()
    return view(db, user, session)

def submit(db, user, sid, payload):
    session = owned(db, user, sid, lock=True)
    item = db.scalar(select(ReviewItem).where(ReviewItem.id == payload.item_id, ReviewItem.session_id == sid, ReviewItem.user_id == user.id))
    if not item:
        raise HTTPException(404, 'Review item not found.')
    card = db.scalar(select(ReviewCard).where(ReviewCard.id == item.card_id, ReviewCard.user_id == user.id).with_for_update())
    data = content.vocabulary(db, user, session.cefr_level).get(card.word_sense_id)
    if data is None:
        raise HTTPException(404, 'Review content is no longer available.')
    if data['version'] != item.snapshot['version']:
        raise HTTPException(409, 'Review content has changed. Finish this session and start a new one.')
    previous = db.scalar(select(ReviewAttempt).where(ReviewAttempt.session_id == sid, ReviewAttempt.request_id == payload.request_id))
    if previous:
        if previous.item_id != item.id or previous.submitted_answer != payload.answer or previous.recall_rating != payload.recall_rating:
            raise HTTPException(409, 'Request ID belongs to a different answer.')
        return feedback(item, previous)
    if session.status != 'active':
        raise HTTPException(409, 'Review session is complete.')
    if db.scalar(select(ReviewAttempt.id).where(ReviewAttempt.item_id == item.id)):
        raise HTTPException(409, 'This card has already been answered.')
    current = view(db, user, session)['current_question']
    if not current or current['item_id'] != item.id:
        raise HTTPException(409, 'Answer the current card first.')
    at = clock.now()
    correct = grade(payload.answer, item.snapshot['answers'])
    before = dict(state=card.state, repetitions=card.repetition_count, ease=card.ease_factor, interval=card.interval_days, lapses=card.lapse_count, algorithm_version=card.algorithm_version)
    updated = schedule(repetitions=card.repetition_count, interval=card.interval_days, ease=card.ease_factor,
                       lapses=card.lapse_count, correct=correct, rating=payload.recall_rating, at=at)
    attempt = ReviewAttempt(user_id=user.id, session_id=sid, card_id=card.id, item_id=item.id,
        request_id=payload.request_id, submitted_answer=payload.answer, is_correct=correct,
        recall_rating=payload.recall_rating, previous_due_at=card.next_due_at, new_due_at=updated['next_due_at'],
        previous_interval_days=card.interval_days, new_interval_days=updated['interval_days'], reviewed_at=at,
        algorithm_version=updated['algorithm_version'], schedule_before=before,
        schedule_after={k:v.isoformat() if hasattr(v, 'isoformat') else v for k,v in updated.items()})
    db.add(attempt)
    for key, value in updated.items():
        setattr(card, key, value)
    card.last_reviewed_at, card.recent_result, card.updated_at = at, correct, at
    db.commit()
    return feedback(item, attempt)

def complete(db, user, sid):
    session = owned(db, user, sid, lock=True)
    result = view(db, user, session)
    if result['current_question']:
        raise HTTPException(409, 'Answer the remaining available cards first.')
    if session.status == 'active':
        session.status, session.completed_at = 'completed', clock.now()
        db.commit()
    return view(db, user, session)

def progress(db, user):
    attempts = db.scalars(select(ReviewAttempt).where(ReviewAttempt.user_id == user.id)).all()
    studied=db.scalar(select(func.count(func.distinct(ReviewCard.word_sense_id))).join(ReviewAttempt,ReviewAttempt.card_id==ReviewCard.id).where(ReviewAttempt.user_id==user.id)) or 0
    return dict(reviews_completed=len(attempts), cards_due=due(db,user)['due_count'],
                vocabulary_items_studied=studied)

def history(db, user, limit, offset):
    rows = db.execute(select(ReviewAttempt, ReviewCard.cefr_level).join(ReviewCard, ReviewAttempt.card_id == ReviewCard.id)
        .where(ReviewAttempt.user_id == user.id).order_by(ReviewAttempt.reviewed_at.desc(), ReviewAttempt.id).offset(offset).limit(limit)).all()
    # Metadata only: keep historical evidence without exposing revoked curriculum.
    return dict(items=[dict(id=a.id, session_id=a.session_id, card_id=a.card_id, cefr_level=level,
                is_correct=a.is_correct, reviewed_at=a.reviewed_at, next_due_at=a.new_due_at,
                algorithm_version=a.algorithm_version) for a,level in rows], limit=limit, offset=offset)
