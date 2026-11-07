from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.curriculum_models import (
    Course,
    Dialogue,
    DialogueTurn,
    Exercise,
    ExerciseOption,
    GrammarExample,
    GrammarRule,
    GrammarTopic,
    Lesson,
    LessonDialogue,
    LessonGrammar,
    LessonObjective,
    LessonSection,
    LessonVocabulary,
    LearningObjective,
    Lexeme,
    Pronunciation,
    Translation,
    Unit,
    WordSense,
)
from app.learning_models import (
    ExerciseAttempt,
    LearningActivityEvent,
    LearningSession,
    LearningSessionExercise,
    LessonProgress,
)
from app.learning_schemas import (
    AnswerResponse,
    CompletionResponse,
    ExerciseFeedback,
    LearningSessionResponse,
    SessionExerciseOption,
    SessionExerciseResponse,
    SessionListItem,
)
from app.models import User
from app.services.draft_preview import can_preview_drafts
from app.services.grading_service import grade_saved
from app.services import exercise_formats
from app.services.content_permissions import topic_allowed
from app.services.progress_service import ensure_lesson_progress, record_completion


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _percentage(score: int, maximum: int) -> float:
    if maximum <= 0:
        return 0.0
    return round(100 * score / maximum, 2)


def _visible_content_filter(include_preview: bool):
    if not include_preview:
        return and_(
            Lesson.status == "published",
            Unit.status == "published",
            Course.status == "published",
        )
    statuses = ("published", "draft", "review")
    return and_(
        Lesson.status.in_(statuses),
        Unit.status.in_(statuses),
        Course.status.in_(statuses),
    )


def _accessible_lesson(db: Session, lesson_id: UUID, user: User) -> tuple[Lesson, Unit, Course, bool]:
    row = db.execute(
        select(Lesson, Unit, Course)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(Lesson.id == lesson_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    lesson, unit, course = row
    if lesson.status == unit.status == course.status == "published":
        return lesson, unit, course, False
    previewable_statuses = {"draft", "review", "published"}
    has_unpublished_content = any(
        item.status != "published" for item in (lesson, unit, course)
    )
    if (
        can_preview_drafts(user)
        and has_unpublished_content
        and all(item.status in previewable_statuses for item in (lesson, unit, course))
    ):
        return lesson, unit, course, True
    raise HTTPException(status_code=404, detail="Lesson not found.")


def _lesson_snapshot(db: Session, lesson: Lesson, unit: Unit, course: Course, user: User | None = None) -> dict:
    objectives = db.scalars(
        select(LearningObjective)
        .join(LessonObjective, LearningObjective.id == LessonObjective.objective_id)
        .where(LessonObjective.lesson_id == lesson.id)
        .order_by(LearningObjective.code)
    ).all()
    sections = db.scalars(
        select(LessonSection)
        .where(LessonSection.lesson_id == lesson.id)
        .order_by(LessonSection.sequence_order)
    ).all()
    vocabulary: list[dict] = []
    lexemes = db.scalars(
        select(Lexeme)
        .join(LessonVocabulary, LessonVocabulary.lexeme_id == Lexeme.id)
        .where(LessonVocabulary.lesson_id == lesson.id)
        .order_by(LessonVocabulary.sequence_order)
    ).all()
    for lexeme in lexemes:
        sense = db.scalar(
            select(WordSense)
            .where(WordSense.lexeme_id == lexeme.id)
            .order_by(WordSense.sense_number)
        )
        if sense is None:
            continue
        translation = db.scalar(
            select(Translation.translated_text)
            .where(Translation.word_sense_id == sense.id, Translation.language_code == "en")
            .order_by(Translation.translated_text)
        )
        pronunciation = db.scalar(
            select(Pronunciation.ipa)
            .where(Pronunciation.lexeme_id == lexeme.id)
            .order_by(Pronunciation.accent_variant)
        )
        vocabulary.append(
            {
                "lemma": lexeme.lemma,
                "part_of_speech": lexeme.part_of_speech,
                "grammatical_gender": lexeme.grammatical_gender,
                "translation": translation or sense.explanation_english,
                "definition_french": sense.definition_french,
                "ipa": pronunciation,
            }
        )

    grammar: list[dict] = []
    topics = db.scalars(
        select(GrammarTopic)
        .join(LessonGrammar, LessonGrammar.grammar_topic_id == GrammarTopic.id)
        .where(LessonGrammar.lesson_id == lesson.id)
        .order_by(GrammarTopic.title, GrammarTopic.slug)
    ).all()
    for topic in topics:
        if user is None or not topic_allowed(topic,user):
            continue
        rules = db.scalars(
            select(GrammarRule).where(GrammarRule.topic_id == topic.id).order_by(GrammarRule.rule_code)
        ).all()
        if topic.teaching_metadata.get("curriculum_supplement"):
            authored_code = topic.teaching_metadata["rule_code"]
            preferred = lesson.slug == topic.teaching_metadata["preferred_lesson_slug"]
            rules = [rule for rule in rules if (rule.rule_code == authored_code) == preferred]
        grammar.append(
            {
                "id": str(topic.id),
                "title": topic.title,
                "summary": topic.summary,
                "rules": [
                    {
                        "code": rule.rule_code,
                        "exceptions": rule.exceptions,
                        "explanation": rule.explanation_english,
                        "explanation_fr": rule.explanation_french,
                        "examples": [
                            {
                                "french": example.french_sentence,
                                "english": example.english_translation,
                            }
                            for example in db.scalars(
                                select(GrammarExample)
                                .where(GrammarExample.rule_id == rule.id)
                                .order_by(GrammarExample.french_sentence)
                            ).all()
                        ],
                    }
                    for rule in rules
                ],
            }
        )

    dialogues: list[dict] = []
    dialogue_rows = db.scalars(
        select(Dialogue)
        .join(LessonDialogue, LessonDialogue.dialogue_id == Dialogue.id)
        .where(LessonDialogue.lesson_id == lesson.id)
        .order_by(Dialogue.slug)
    ).all()
    for dialogue in dialogue_rows:
        dialogues.append(
            {
                "title": dialogue.title,
                "context": dialogue.english_context,
                "turns": [
                    {
                        "speaker": turn.speaker_label,
                        "french": turn.french_text,
                        "english": turn.english_translation,
                    }
                    for turn in db.scalars(
                        select(DialogueTurn)
                        .where(DialogueTurn.dialogue_id == dialogue.id)
                        .order_by(DialogueTurn.sequence_order)
                    ).all()
                ],
            }
        )

    return {
        "id": str(lesson.id),
        "learning_flow_version": 1,
        "title": lesson.title,
        "description": lesson.description,
        "level": lesson.difficulty_level,
        "content_version": lesson.content_version,
        "estimated_minutes": lesson.estimated_minutes,
        "course_title": course.title,
        "unit_title": unit.title,
        "objectives": [
            {"id":str(item.id),"code":item.code,"title": item.title, "description": item.description}
            for item in objectives
        ],
        "sections": [
            {
                "type": item.section_type,
                "title": item.title,
                "content": item.body_content,
                "sequence_order": item.sequence_order,
            }
            for item in sections
        ],
        "vocabulary": vocabulary,
        "grammar": grammar,
        "dialogues": dialogues,
    }


def _event(
    db: Session,
    *,
    user_id: UUID,
    session_id: UUID | None,
    lesson_id: UUID | None,
    event_type: str,
    metadata: dict | None = None,
) -> None:
    db.add(
        LearningActivityEvent(
            user_id=user_id,
            session_id=session_id,
            lesson_id=lesson_id,
            event_type=event_type,
            event_metadata=metadata or {},
        )
    )


def _attempts_by_exercise(db: Session, session_id: UUID) -> dict[UUID, ExerciseAttempt]:
    attempts = db.scalars(
        select(ExerciseAttempt).where(ExerciseAttempt.learning_session_id == session_id)
    ).all()
    return {attempt.session_exercise_id: attempt for attempt in attempts}


def _session_response(
    db: Session,
    session: LearningSession,
    *,
    user: User,
) -> LearningSessionResponse:
    _accessible_lesson(db, session.lesson_id, user)
    _session_exercise_access(db,session,user)
    snapshots = db.scalars(
        select(LearningSessionExercise)
        .where(LearningSessionExercise.learning_session_id == session.id)
        .order_by(LearningSessionExercise.exercise_order)
    ).all()
    attempts = _attempts_by_exercise(db, session.id)
    exercise_responses: list[SessionExerciseResponse] = []
    for item in snapshots:
        snapshot = item.exercise_snapshot
        attempt = attempts.get(item.id)
        feedback = None
        if attempt:
            feedback = ExerciseFeedback(
                is_correct=attempt.is_correct,
                correct_answer=attempt.feedback["correct_answer"],
                explanation=attempt.feedback["explanation"],
                awarded_points=attempt.awarded_points,
                max_points=attempt.max_points,
                answered_at=attempt.submitted_at,
            )
        exercise_responses.append(
            SessionExerciseResponse(
                id=item.id,
                exercise_id=item.source_exercise_id,
                exercise_order=item.exercise_order,
                type=snapshot["type"],
                prompt=snapshot["prompt"],
                instructions=snapshot["instructions"],
                options=[
                    SessionExerciseOption(
                        id=UUID(option["id"]),
                        text=option["text"],
                        sequence_order=option["sequence_order"],
                    )
                    for option in snapshot["options"]
                ],
                answered=attempt is not None,
                feedback=feedback,
                submitted_answer=(attempt.answer_payload or {'selected_option_id':attempt.submitted_answer}) if attempt else None,
                learning_objective_id=snapshot.get('learning_objective_id'),
                grammar_topic_id=snapshot.get('grammar_topic_id'),
                **exercise_formats.public_fields(snapshot),
            )
        )
    answered = len(attempts)
    return LearningSessionResponse(
        id=session.id,
        lesson_id=session.lesson_id,
        lesson_content_version=session.lesson_content_version,
        cefr_level=session.cefr_level,  # type: ignore[arg-type]
        status=session.status,  # type: ignore[arg-type]
        preview_mode=session.preview_mode,
        started_at=session.started_at,
        last_activity_at=session.last_activity_at,
        completed_at=session.completed_at,
        current_section_position=session.current_section_position,
        current_exercise_position=session.current_exercise_position,
        total_exercises=session.total_exercises,
        answered_exercises=answered,
        score_points=session.score_points,
        max_score_points=session.max_score_points,
        percentage=_percentage(session.score_points, session.max_score_points),
        lesson=session.lesson_snapshot,
        exercises=exercise_responses,
        activity_key=session.activity_key,
    )


def _session_exercise_access(db,session,user):
    """Revalidate live source permissions; grade only the frozen private key."""
    rows=db.scalars(select(LearningSessionExercise).where(LearningSessionExercise.learning_session_id==session.id)).all()
    for saved in rows:
        source=db.get(Exercise,saved.source_exercise_id) if saved.source_exercise_id else None
        if source is None:
            if saved.exercise_snapshot.get('format_version')==2:
                raise HTTPException(404,'This exercise is no longer available.')
            continue  # Legacy frozen snapshots preserve their original behavior.
        if source.lesson_id!=session.lesson_id:
            raise HTTPException(404,'Session exercise not found.')
        topic=db.get(GrammarTopic,source.grammar_topic_id) if source.grammar_topic_id else None
        if topic and not topic_allowed(topic,user):
            raise HTTPException(404,'This grammar activity is not available.')
    for saved in session.lesson_snapshot.get('grammar',[]):
        if saved.get('id') and not topic_allowed(db.get(GrammarTopic,UUID(saved['id'])),user):
            raise HTTPException(404,'This grammar explanation is no longer available.')


def _session_for_user(
    db: Session,
    session_id: UUID,
    user: User,
    *,
    lock: bool = False,
) -> LearningSession:
    query = select(LearningSession).where(
        LearningSession.id == session_id,
        LearningSession.user_id == user.id,
    )
    if lock:
        query = query.with_for_update()
    session = db.scalar(query)
    if session is None:
        raise HTTPException(status_code=404, detail="Learning session not found.")
    _accessible_lesson(db, session.lesson_id, user)
    _session_exercise_access(db,session,user)
    return session


def _serialize_list_item(
    db: Session,
    session: LearningSession,
) -> SessionListItem:
    lesson = db.get(Lesson, session.lesson_id)
    attempts = db.scalar(
        select(func.count(ExerciseAttempt.id)).where(
            ExerciseAttempt.learning_session_id == session.id
        )
    ) or 0
    return SessionListItem(
        id=session.id,
        lesson_id=session.lesson_id,
        lesson_title=lesson.title if lesson else "Unavailable lesson",
        cefr_level=session.cefr_level,  # type: ignore[arg-type]
        lesson_content_version=session.lesson_content_version,
        status=session.status,  # type: ignore[arg-type]
        started_at=session.started_at,
        last_activity_at=session.last_activity_at,
        completed_at=session.completed_at,
        total_exercises=session.total_exercises,
        answered_exercises=attempts,
        percentage=_percentage(session.score_points, session.max_score_points),
        activity_key=session.activity_key,
    )


def start_session(db: Session, *, user: User, lesson_id: UUID, commit: bool = True,
                  activity_key: str = 'lesson', exercise_ids: list[UUID] | None = None) -> tuple[LearningSessionResponse, bool]:
    try:
        lesson, unit, course, preview_mode = _accessible_lesson(db, lesson_id, user)
        existing = db.scalar(
            select(LearningSession)
            .where(
                LearningSession.user_id == user.id,
                LearningSession.lesson_id == lesson_id,
                LearningSession.status == "in_progress",
                LearningSession.activity_key == activity_key,
            )
            .with_for_update()
        )
        if existing is not None:
            return _session_response(db, existing, user=user), False

        source_exercises = db.scalars(
            select(Exercise)
            .where(Exercise.lesson_id == lesson.id)
            .where(Exercise.id.in_(exercise_ids) if exercise_ids is not None else True)
            .order_by(Exercise.sequence_order)
        ).all()
        if not source_exercises:
            raise HTTPException(status_code=409, detail="This lesson has no gradable exercises.")

        exercise_snapshots: list[dict] = []
        for order, exercise in enumerate(source_exercises, start=1):
            if exercise.level!=lesson.difficulty_level:
                raise HTTPException(409,'This exercise has an inconsistent French level.')
            options = db.scalars(
                select(ExerciseOption)
                .where(ExerciseOption.exercise_id == exercise.id)
                .order_by(ExerciseOption.sequence_order)
            ).all()
            if exercise.learning_objective_id and not db.scalar(select(LessonObjective).where(
                    LessonObjective.lesson_id==lesson.id,LessonObjective.objective_id==exercise.learning_objective_id)):
                raise HTTPException(409,'This exercise has an invalid objective reference.')
            if exercise.grammar_topic_id:
                topic=db.get(GrammarTopic,exercise.grammar_topic_id)
                if not topic or topic.cefr_level!=lesson.difficulty_level:
                    raise HTTPException(409,'This exercise has an inconsistent grammar level.')
                if not db.scalar(select(LessonGrammar).where(LessonGrammar.lesson_id==lesson.id,
                        LessonGrammar.grammar_topic_id==exercise.grammar_topic_id)):
                    raise HTTPException(409,'This exercise has an invalid grammar reference.')
                if topic.publication_status not in ('inherited','published'):
                    if not (can_preview_drafts(user) and topic.publication_status in ('draft','review')):
                        raise HTTPException(404,'This grammar activity is not available.')
                    preview_mode=True
            exercise_snapshots.append(
                {
                    "exercise_id": exercise.id,
                    "order": order,
                    "version": lesson.content_version,
                    "snapshot": exercise_formats.snapshot(exercise,options),
                }
            )

        now = _now()
        session = LearningSession(
            user_id=user.id,
            lesson_id=lesson.id,
            lesson_content_version=lesson.content_version,
            cefr_level=lesson.difficulty_level,
            status="in_progress",
            preview_mode=preview_mode,
            activity_key=activity_key,
            lesson_snapshot=_lesson_snapshot(db, lesson, unit, course,user),
            started_at=now,
            last_activity_at=now,
            current_section_position=0,
            current_exercise_position=0,
            total_exercises=len(exercise_snapshots),
            score_points=0,
            max_score_points=len(exercise_snapshots),
        )
        db.add(session)
        db.flush()
        db.add_all(
            [
                LearningSessionExercise(
                    learning_session_id=session.id,
                    source_exercise_id=item["exercise_id"],
                    exercise_order=item["order"],
                    exercise_content_version=item["version"],
                    exercise_snapshot=item["snapshot"],
                    max_points=1,
                )
                for item in exercise_snapshots
            ]
        )
        if activity_key=='lesson':ensure_lesson_progress(
            db,
            user=user,
            lesson_id=lesson.id,
            cefr_level=lesson.difficulty_level,
            now=now,
        )
        _event(
            db,
            user_id=user.id,
            session_id=session.id,
            lesson_id=lesson.id,
            event_type="session_started" if activity_key=='lesson' else 'practice_started',
            metadata={"cefr_level": lesson.difficulty_level, "preview_mode": preview_mode},
        )
        if commit:
            db.commit()
            db.refresh(session)
        else:
            db.flush()
        return _session_response(db, session, user=user), True
    except IntegrityError:
        db.rollback()
        if not commit:
            raise HTTPException(status_code=409, detail="Retry starting this study activity.") from None
        existing = db.scalar(
            select(LearningSession).where(
                LearningSession.user_id == user.id,
                LearningSession.lesson_id == lesson_id,
                LearningSession.status == "in_progress",
                LearningSession.activity_key == activity_key,
            )
        )
        if existing is not None:
            return _session_response(db, existing, user=user), False
        raise HTTPException(status_code=409, detail="A learning session could not be started safely.")


def get_session(db: Session, *, user: User, session_id: UUID) -> LearningSessionResponse:
    session = _session_for_user(db, session_id, user)
    return _session_response(db, session, user=user)


def set_position(db: Session, *, user: User, session_id: UUID, position: int):
    session=_session_for_user(db,session_id,user,lock=True)
    if session.status!='in_progress':
        raise HTTPException(409,'This learning session is no longer active.')
    if session.activity_key!='lesson' or session.lesson_snapshot.get('learning_flow_version')!=1:
        raise HTTPException(409,'Continue the exercises in this saved activity.')
    session.current_section_position=position
    session.last_activity_at=_now()
    db.commit();db.refresh(session)
    return _session_response(db,session,user=user)


def resume_session(db: Session, *, user: User, session_id: UUID) -> LearningSessionResponse:
    session = _session_for_user(db, session_id, user, lock=True)
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="Only an in-progress lesson can be resumed.")
    session.last_activity_at = _now()
    _event(
        db,
        user_id=user.id,
        session_id=session.id,
        lesson_id=session.lesson_id,
        event_type="session_resumed",
    )
    db.commit()
    db.refresh(session)
    return _session_response(db, session, user=user)


def submit_answer(
    db: Session,
    *,
    user: User,
    session_id: UUID,
    session_exercise_id: UUID,
    selected_option_id: UUID | None = None,
    idempotency_key: UUID,
    answer_payload: dict | None = None,
) -> AnswerResponse:
    payload={'selected_option_id':str(selected_option_id)} if selected_option_id is not None else (answer_payload or {})
    def same(attempt):
        return (attempt.answer_payload or {'selected_option_id':attempt.submitted_answer})==payload
    try:
        session = _session_for_user(db, session_id, user, lock=True)
        if session.status != 'in_progress':
            raise HTTPException(409,'This learning session is no longer active.')
        exercise = db.scalar(
            select(LearningSessionExercise)
            .where(
                LearningSessionExercise.id == session_exercise_id,
                LearningSessionExercise.learning_session_id == session.id,
            )
            .with_for_update()
        )
        if exercise is None:
            raise HTTPException(status_code=404, detail="Session exercise not found.")

        prior_key = db.scalar(
            select(ExerciseAttempt).where(
                ExerciseAttempt.learning_session_id == session.id,
                ExerciseAttempt.idempotency_key == idempotency_key,
            )
        )
        if prior_key is not None:
            if (
                prior_key.session_exercise_id != exercise.id
                or not same(prior_key)
            ):
                raise HTTPException(
                    status_code=409,
                    detail="This idempotency key was already used for a different answer.",
                )
            return _answer_response(db, session, prior_key, idempotent=True)

        existing = db.scalar(
            select(ExerciseAttempt).where(ExerciseAttempt.session_exercise_id == exercise.id)
        )
        if existing is not None:
            if same(existing):
                return _answer_response(db, session, existing, idempotent=True)
            raise HTTPException(
                status_code=409,
                detail="This exercise has already been answered in this session.",
            )

        if session.status != 'in_progress':
            raise HTTPException(409,'This learning session is no longer active.')

        attempts = _attempts_by_exercise(db, session.id)
        next_exercise = db.scalar(
            select(LearningSessionExercise)
            .where(
                LearningSessionExercise.learning_session_id == session.id,
                ~LearningSessionExercise.id.in_(
                    select(ExerciseAttempt.session_exercise_id).where(
                        ExerciseAttempt.learning_session_id == session.id
                    )
                ),
            )
            .order_by(LearningSessionExercise.exercise_order)
        )
        if next_exercise is None or next_exercise.id != exercise.id:
            raise HTTPException(
                status_code=409,
                detail="Answer the next unanswered exercise in the saved session.",
            )
        if session_exercise_id in attempts:
            raise HTTPException(status_code=409, detail="This exercise has already been answered.")

        is_correct, correct_answer, explanation, normalized = grade_saved(exercise.exercise_snapshot,payload)
        awarded = 1 if is_correct else 0
        now = _now()
        attempt = ExerciseAttempt(
            user_id=user.id,
            learning_session_id=session.id,
            session_exercise_id=exercise.id,
            attempt_number=1,
            idempotency_key=idempotency_key,
            submitted_answer=str(selected_option_id) if selected_option_id is not None else 'payload:'+hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:28],
            answer_payload=None if selected_option_id is not None else payload,
            normalized_answer=normalized,
            is_correct=is_correct,
            awarded_points=awarded,
            max_points=exercise.max_points,
            feedback={
                "correct_answer": correct_answer,
                "explanation": explanation,
            },
            grading_version="multiple-choice-v1" if exercise.exercise_snapshot['type']=='multiple_choice' else 'deterministic-v2',
            submitted_at=now,
        )
        db.add(attempt)
        session.score_points += awarded
        session.current_exercise_position += 1
        if session.lesson_snapshot.get('learning_flow_version')==1:
            session.current_section_position=3
        session.last_activity_at = now
        progress = db.scalar(
            select(LessonProgress)
            .where(
                LessonProgress.user_id == user.id,
                LessonProgress.lesson_id == session.lesson_id,
            )
            .with_for_update()
        )
        if progress is not None and session.activity_key=='lesson':
            progress.last_studied_at = now
            progress.updated_at = now
        _event(
            db,
            user_id=user.id,
            session_id=session.id,
            lesson_id=session.lesson_id,
            event_type="exercise_answered" if session.activity_key=='lesson' else 'practice_answered',
            metadata={"exercise_order": exercise.exercise_order, "is_correct": is_correct,
                'learning_objective_id':exercise.exercise_snapshot.get('learning_objective_id')},
        )
        db.commit()
        db.refresh(attempt)
        db.refresh(session)
        return _answer_response(db, session, attempt, idempotent=False)
    except IntegrityError:
        db.rollback()
        session = _session_for_user(db, session_id, user)
        prior_key = db.scalar(
            select(ExerciseAttempt).where(
                ExerciseAttempt.learning_session_id == session.id,
                ExerciseAttempt.idempotency_key == idempotency_key,
            )
        )
        if (
            prior_key is not None
            and prior_key.session_exercise_id == session_exercise_id
            and same(prior_key)
        ):
            return _answer_response(db, session, prior_key, idempotent=True)
        raise HTTPException(
            status_code=409,
            detail="This answer conflicted with another submission. Refresh the session state.",
        )


def _answer_response(
    db: Session,
    session: LearningSession,
    attempt: ExerciseAttempt,
    *,
    idempotent: bool,
) -> AnswerResponse:
    answered = db.scalar(
        select(func.count(ExerciseAttempt.id)).where(
            ExerciseAttempt.learning_session_id == session.id
        )
    ) or 0
    return AnswerResponse(
        session_id=session.id,
        session_exercise_id=attempt.session_exercise_id,
        is_correct=attempt.is_correct,
        correct_answer=attempt.feedback["correct_answer"],
        explanation=attempt.feedback["explanation"],
        awarded_points=attempt.awarded_points,
        max_points=attempt.max_points,
        answered_exercises=answered,
        total_exercises=session.total_exercises,
        score_points=session.score_points,
        max_score_points=session.max_score_points,
        percentage=_percentage(session.score_points, session.max_score_points),
        idempotent_replay=idempotent,
    )


def complete_session(
    db: Session,
    *,
    user: User,
    session_id: UUID,
) -> CompletionResponse:
    session = _session_for_user(db, session_id, user, lock=True)
    lesson = db.get(Lesson, session.lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    if session.status == "completed":
        return _completion_response(db, session, lesson)
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="This learning session cannot be completed.")
    attempts = db.scalars(
        select(ExerciseAttempt).where(ExerciseAttempt.learning_session_id == session.id)
    ).all()
    if len(attempts) != session.total_exercises:
        raise HTTPException(
            status_code=409,
            detail="Answer every required exercise before completing this lesson.",
        )
    now = _now()
    session.status = "completed"
    session.completed_at = now
    session.last_activity_at = now
    score = _percentage(session.score_points, session.max_score_points)
    progress = db.scalar(
        select(LessonProgress)
        .where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == session.lesson_id,
        )
        .with_for_update()
    )
    if progress is None and session.activity_key=='lesson':
        progress = ensure_lesson_progress(
            db,
            user=user,
            lesson_id=session.lesson_id,
            cefr_level=session.cefr_level,
            now=now,
        )
    if session.activity_key=='lesson':record_completion(progress, score_percentage=score, completed_at=now)
    _event(
        db,
        user_id=user.id,
        session_id=session.id,
        lesson_id=session.lesson_id,
        event_type="lesson_completed" if session.activity_key=='lesson' else 'practice_completed',
        metadata={"percentage": score, "total_exercises": session.total_exercises},
    )
    db.commit()
    db.refresh(session)
    return _completion_response(db, session, lesson)


def _completion_response(
    db: Session,
    session: LearningSession,
    lesson: Lesson,
) -> CompletionResponse:
    correct = db.scalar(
        select(func.count(ExerciseAttempt.id)).where(
            ExerciseAttempt.learning_session_id == session.id,
            ExerciseAttempt.is_correct.is_(True),
        )
    ) or 0
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == session.user_id,
            LessonProgress.lesson_id == session.lesson_id,
        )
    )
    return CompletionResponse(
        session_id=session.id,
        lesson_id=session.lesson_id,
        lesson_title=session.lesson_snapshot.get("title", lesson.title),
        cefr_level=session.cefr_level,  # type: ignore[arg-type]
        status="completed",
        correct_answers=correct,
        incorrect_answers=session.total_exercises - correct,
        total_questions=session.total_exercises,
        score_points=session.score_points,
        max_score_points=session.max_score_points,
        percentage=_percentage(session.score_points, session.max_score_points),
        completion_count=progress.completion_count if progress else (1 if session.activity_key=='lesson' else 0),
        completed_at=session.completed_at or session.last_activity_at,
        activity_key=session.activity_key,
    )


def get_completion_results(
    db: Session,
    *,
    user: User,
    session_id: UUID,
) -> CompletionResponse:
    session = _session_for_user(db, session_id, user)
    if session.status != "completed":
        raise HTTPException(status_code=409, detail="This learning session is not complete.")
    lesson = db.get(Lesson, session.lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    return _completion_response(db, session, lesson)


def abandon_session(db: Session, *, user: User, session_id: UUID) -> None:
    session = _session_for_user(db, session_id, user, lock=True)
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="Only an in-progress session can be abandoned.")
    now = _now()
    session.status = "abandoned"
    session.last_activity_at = now
    progress = db.scalar(
        select(LessonProgress)
        .where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == session.lesson_id,
        )
        .with_for_update()
    )
    if progress is not None and session.activity_key=='lesson':
        progress.status = "completed" if progress.completion_count else "not_started"
        progress.last_studied_at = now
        progress.updated_at = now
    _event(
        db,
        user_id=user.id,
        session_id=session.id,
        lesson_id=session.lesson_id,
        event_type="session_abandoned",
    )
    db.commit()


def list_user_sessions(
    db: Session,
    *,
    user: User,
    limit: int,
    offset: int,
    status_filter: str | None = None,
) -> tuple[list[SessionListItem], int]:
    visible_filter = _visible_content_filter(can_preview_drafts(user))
    query = (
        select(LearningSession)
        .join(Lesson, LearningSession.lesson_id == Lesson.id)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(LearningSession.user_id == user.id, visible_filter)
    )
    if status_filter:
        query = query.where(LearningSession.status == status_filter)
    sessions = db.scalars(query.order_by(LearningSession.last_activity_at.desc())).all()
    visible=[]
    for session in sessions:
        try:
            _session_exercise_access(db,session,user)
        except HTTPException as error:
            if error.status_code==404:continue
            raise
        visible.append(session)
    return [_serialize_list_item(db,s) for s in visible[offset:offset+limit]],len(visible)



def get_progress_for_user(
    db: Session,
    *,
    user: User,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    visible_filter = _visible_content_filter(can_preview_drafts(user))
    query = (
        select(LessonProgress, Lesson)
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(LessonProgress.user_id == user.id)
        .where(visible_filter)
        .order_by(LessonProgress.updated_at.desc())
    )
    rows = db.execute(query.offset(offset).limit(limit)).all()
    items = []
    for progress, lesson in rows:
        try:
            _accessible_lesson(db, lesson.id, user)
        except HTTPException as error:
            if error.status_code == 404:
                continue
            raise
        items.append(
            {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "cefr_level": progress.cefr_level,
                "status": progress.status,
                "first_started_at": progress.first_started_at,
                "last_studied_at": progress.last_studied_at,
                "completed_at": progress.completed_at,
                "best_score": progress.best_score,
                "latest_score": progress.latest_score,
                "completion_count": progress.completion_count,
            }
        )
    total = db.scalar(
        select(func.count(LessonProgress.id))
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(LessonProgress.user_id == user.id, visible_filter)
    ) or 0
    return items, total


def get_lesson_progress(
    db: Session,
    *,
    user: User,
    lesson_id: UUID,
) -> dict:
    lesson, _unit, _course, _preview_mode = _accessible_lesson(db, lesson_id, user)
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == lesson.id,
        )
    )
    if progress is None:
        return {
            "lesson_id": lesson.id,
            "lesson_title": lesson.title,
            "cefr_level": lesson.difficulty_level,
            "status": "not_started",
            "first_started_at": None,
            "last_studied_at": None,
            "completed_at": None,
            "best_score": Decimal("0"),
            "latest_score": Decimal("0"),
            "completion_count": 0,
        }
    return {
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "cefr_level": progress.cefr_level,
        "status": progress.status,
        "first_started_at": progress.first_started_at,
        "last_studied_at": progress.last_studied_at,
        "completed_at": progress.completed_at,
        "best_score": progress.best_score,
        "latest_score": progress.latest_score,
        "completion_count": progress.completion_count,
    }


def get_dashboard(db: Session, *, user: User) -> dict:
    progress_rows = db.scalars(
        select(LessonProgress).where(LessonProgress.user_id == user.id)
    ).all()
    visible_progress = []
    for progress in progress_rows:
        try:
            _accessible_lesson(db, progress.lesson_id, user)
        except HTTPException as error:
            if error.status_code == 404:
                continue
            raise
        visible_progress.append(progress)

    active_sessions, _ = list_user_sessions(
        db, user=user, limit=10, offset=0, status_filter="in_progress"
    )
    visible_session_ids = [
        row[0]
        for row in db.execute(
            select(LearningSession.id)
            .join(Lesson, LearningSession.lesson_id == Lesson.id)
            .join(Unit, Lesson.unit_id == Unit.id)
            .join(Course, Unit.course_id == Course.id)
            .where(
                LearningSession.user_id == user.id,
                _visible_content_filter(can_preview_drafts(user)),
            )
        ).all()
    ]
    total_answers = db.scalar(
        select(func.count(ExerciseAttempt.id)).where(
            ExerciseAttempt.user_id == user.id,
            ExerciseAttempt.learning_session_id.in_(visible_session_ids),
        )
    ) or 0
    average_score = db.scalar(
        select(
            func.avg(
                100.0
                * LearningSession.score_points
                / func.nullif(LearningSession.max_score_points, 0)
            )
        ).where(
            LearningSession.user_id == user.id,
            LearningSession.status == "completed",
            LearningSession.activity_key == 'lesson',
            LearningSession.id.in_(visible_session_ids),
        )
    )
    recent_rows = db.scalars(
        select(LearningActivityEvent)
        .where(LearningActivityEvent.user_id == user.id)
        .order_by(LearningActivityEvent.created_at.desc())
        .limit(10)
    ).all()
    recent = []
    for event in recent_rows:
        if event.lesson_id is not None:
            try:
                _accessible_lesson(db, event.lesson_id, user)
            except HTTPException as error:
                if error.status_code == 404:
                    continue
                raise
        recent.append(
            {
                "event_type": event.event_type,
                "lesson_id": event.lesson_id,
                "created_at": event.created_at,
                "metadata": event.event_metadata,
            }
        )

    current_level = user.preferences.current_level.upper()
    lessons_query = (
        select(Lesson, Unit, Course)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(Course.level_id == current_level, _visible_content_filter(can_preview_drafts(user)))
        .order_by(Unit.sequence_order, Lesson.sequence_order)
        .limit(50)
    )
    path = [
        {
            "lesson_id": lesson.id,
            "title": lesson.title,
            "level": lesson.difficulty_level,
            "status": next(
                (
                    item.status
                    for item in visible_progress
                    if item.lesson_id == lesson.id
                ),
                "not_started",
            ),
        }
        for lesson, _unit, _course in db.execute(lessons_query).all()
    ]
    return {
        "current_level": current_level,
        "lessons_started": sum(item.first_started_at is not None for item in visible_progress),
        "lessons_completed": sum(item.status == "completed" for item in visible_progress),
        "lessons_in_progress": sum(item.status == "in_progress" for item in visible_progress),
        "active_sessions": active_sessions,
        "total_answered_exercises": total_answers,
        "average_completed_session_score": round(float(average_score or 0), 2),
        "recent_activity": recent,
        "learning_path": path,
    }
