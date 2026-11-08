"""Authorized projections and focused sessions using the persisted M04 engine."""
from collections import Counter
from uuid import UUID
from sqlalchemy import select
from fastapi import HTTPException
from app.curriculum_models import Exercise, GrammarTopic, LessonGrammar, LessonObjective, LearningObjective, Unit
from app.learning_models import ExerciseAttempt, LearningSession, LearningSessionExercise, LessonProgress
from app.services import learning_service as learning, study_content
from app.services.content_permissions import topic_allowed


def library(db,user,level):
    lessons = study_content.lessons(db, user, level)
    if not lessons:
        return dict(level=level, items=[])
    ids = [lesson.id for lesson, _ in lessons]
    units = dict(db.execute(select(Unit.id, Unit.title).where(Unit.id.in_([lesson.unit_id for lesson, _ in lessons]))).all())
    progress = dict(db.execute(select(LessonProgress.lesson_id, LessonProgress.status)
        .where(LessonProgress.user_id == user.id, LessonProgress.lesson_id.in_(ids))).all())
    active_sessions = {session.lesson_id: session for session in db.scalars(select(LearningSession).where(
        LearningSession.user_id == user.id, LearningSession.lesson_id.in_(ids),
        LearningSession.activity_key == 'lesson', LearningSession.status == 'in_progress'))}
    objectives = {}
    for lesson_id, objective in db.execute(select(LessonObjective.lesson_id, LearningObjective)
        .join(LearningObjective).where(LessonObjective.lesson_id.in_(ids)).order_by(LearningObjective.code)):
        objectives.setdefault(lesson_id, []).append(dict(id=str(objective.id),title=objective.title,description=objective.description))
    result=[]
    for lesson,preview in lessons:
        active = active_sessions.get(lesson.id)
        result.append(dict(id=str(lesson.id),title=lesson.title,description=lesson.description,
            unit_id=str(lesson.unit_id),unit_title=units[lesson.unit_id],estimated_minutes=lesson.estimated_minutes,draft_preview=preview,
            objectives=objectives.get(lesson.id, []),
            status=progress.get(lesson.id, 'not_started'),answered=active.current_exercise_position if active else 0,
            total=active.total_exercises if active else 0,session_id=str(active.id) if active else None))
    return dict(level=level,items=result)


def grammar(db,user,level):
    permitted={l.id:(l,p) for l,p in study_content.lessons(db,user,level)}
    if not permitted:return dict(level=level,items=[])
    rows=db.execute(select(GrammarTopic,LessonGrammar.lesson_id).join(LessonGrammar).where(
        LessonGrammar.lesson_id.in_(permitted),GrammarTopic.cefr_level==level).order_by(GrammarTopic.title)).all()
    rows = [row for row in rows if topic_allowed(row[0], user)]
    if not rows:
        return dict(level=level, items=[])
    result={}
    lesson_ids = {lid for _, lid in rows}
    vocabulary = learning.lesson_vocabulary(db, lesson_ids)
    rules = learning.grammar_rules(db, {topic.id for topic, _ in rows})
    objectives = {}
    for lesson_id, objective in db.execute(select(LessonObjective.lesson_id, LearningObjective)
        .join(LearningObjective).where(LessonObjective.lesson_id.in_(lesson_ids)).order_by(LearningObjective.code)):
        objectives.setdefault(lesson_id, []).append(dict(id=str(objective.id), code=objective.code,
            title=objective.title, description=objective.description))
    rows.sort(key=lambda row: permitted[row[1]][0].slug != row[0].teaching_metadata.get('preferred_lesson_slug'))
    for topic,lid in rows:
        if topic.id in result and topic.teaching_metadata.get('curriculum_supplement'):
            result[topic.id]['lesson_ids'].append(str(lid))
            continue
        lesson = permitted[lid][0]
        visible_rules = learning.rules_for_lesson(topic, lesson, rules.get(topic.id, []))
        authored = [rule for rule in visible_rules if rule['code'] == topic.teaching_metadata.get('rule_code')]
        word_examples=topic.teaching_metadata.get('vocabulary_examples')
        entry=result.setdefault(topic.id,dict(id=str(topic.id),title=topic.title,summary=topic.summary,
            rules=authored or visible_rules,teaching=topic.teaching_metadata,level=level,
            publication_status=topic.publication_status,lesson_ids=[],objectives=[],
            vocabulary=[word for word in vocabulary.get(lid, []) if not word_examples or word['lemma'] in word_examples],
            explanation_language=user.preferences.explanation_language,
            available_exercises=0))
        entry['lesson_ids'].append(str(lid))
        objective_code=topic.teaching_metadata.get('objective_code')
        entry['objectives'].extend(o for o in objectives.get(lid, []) if not objective_code or o['code']==objective_code)
    if result:
        linked = {exercise.id: (exercise.grammar_topic_id, permitted[exercise.lesson_id][0].content_version)
                  for exercise in db.scalars(select(Exercise).where(Exercise.grammar_topic_id.in_(result),
                      Exercise.lesson_id.in_(permitted), Exercise.level == level))}
        available = Counter(topic for topic, _ in linked.values())
        recent = {}
        attempts = db.execute(select(LearningSessionExercise.source_exercise_id, LearningSession.lesson_content_version,
            ExerciseAttempt.is_correct).join(LearningSessionExercise,
                LearningSessionExercise.id == ExerciseAttempt.session_exercise_id)
            .join(LearningSession, LearningSession.id == ExerciseAttempt.learning_session_id)
            .where(ExerciseAttempt.user_id == user.id, LearningSessionExercise.source_exercise_id.in_(linked))
            .order_by(ExerciseAttempt.submitted_at.desc(), ExerciseAttempt.id).limit(200))
        for exercise_id, version, correct in attempts:
            if version == linked[exercise_id][1]:
                recent.setdefault(exercise_id, correct)
        counts = Counter((linked[exercise_id][0], correct) for exercise_id, correct in recent.items())
        for topic_id, entry in result.items():
            entry.update(available_exercises=available[topic_id],
                         recent_correct=counts[topic_id, True], recent_mistakes=counts[topic_id, False])
    return dict(level=level,items=sorted(result.values(),key=lambda item: item['teaching'].get('sequence', 0)))


def candidates(db,user,level,category,topic_id=None,lesson_id=None,objective_id=None):
    permitted={l.id for l,_ in study_content.lessons(db,user,level)}
    if lesson_id:permitted &= {lesson_id}
    if not permitted:return []
    query=select(Exercise).where(Exercise.lesson_id.in_(permitted),Exercise.level==level)
    if topic_id:query=query.where(Exercise.grammar_topic_id==topic_id)
    if objective_id:query=query.where(Exercise.learning_objective_id==objective_id)
    types={'grammar':('multiple_choice','fill_blank','short_answer','translation'),
        'sentence_building':('sentence_order',),'listening':('listening',)}
    if category in types and not (category=='grammar' and topic_id):
        query=query.where(Exercise.exercise_type.in_(types[category]))
    if category=='grammar':query=query.where(Exercise.grammar_topic_id.is_not(None))
    rows=db.scalars(query.order_by(Exercise.lesson_id,Exercise.sequence_order,Exercise.id)).all()
    rows=[e for e in rows if not e.grammar_topic_id or topic_allowed(db.get(GrammarTopic,e.grammar_topic_id),user)]
    if category=='mistakes':
        # Only the latest attempt for each source exercise is evidence of an
        # unresolved mistake. Older incorrect attempts cannot undo later success.
        attempts=db.execute(select(ExerciseAttempt,LearningSessionExercise.source_exercise_id,LearningSession.lesson_content_version,LearningSessionExercise.exercise_snapshot)
            .join(LearningSessionExercise,ExerciseAttempt.session_exercise_id==LearningSessionExercise.id)
            .join(LearningSession,ExerciseAttempt.learning_session_id==LearningSession.id)
            .where(ExerciseAttempt.user_id==user.id,LearningSession.cefr_level==level)
            .order_by(ExerciseAttempt.submitted_at.desc(),ExerciseAttempt.id).limit(200)).all()
        latest={}
        for attempt,eid,version,saved in attempts:latest.setdefault(eid,(attempt.is_correct,version,saved.get('learning_objective_id')))
        versions={l.id:l.content_version for l,_ in study_content.lessons(db,user,level)}
        rows=[e for e in rows if e.id in latest and latest[e.id][:2]==(False,versions[e.lesson_id])
            and (objective_id is None or latest[e.id][2]==str(objective_id))]
    return rows


def start(db,user,payload):
    level=payload.level or user.preferences.current_level.upper()
    rows=candidates(db,user,level,payload.category,payload.grammar_topic_id,payload.lesson_id,payload.learning_objective_id)
    if payload.attempt_id is not None:
        if payload.category != 'mistakes':
            raise HTTPException(422,'Choose a mistake review to retry an attempt.')
        eligible = mistakes(db, user, level, payload.lesson_id)['items']
        if not any(item['attempt_id'] == str(payload.attempt_id) for item in eligible):
            raise HTTPException(404,'This mistake is no longer available for review.')
        source_id = db.scalar(select(LearningSessionExercise.source_exercise_id).join(ExerciseAttempt,
            ExerciseAttempt.session_exercise_id == LearningSessionExercise.id).where(
            ExerciseAttempt.id == payload.attempt_id, ExerciseAttempt.user_id == user.id))
        rows = [exercise for exercise in rows if exercise.id == source_id]
    if not rows:raise HTTPException(409,'No authorized exercises are available for this practice yet.')
    # One real lesson per focused session keeps source permissions and snapshots
    # intact; subsequent lessons can be practiced separately.
    lid=rows[0].lesson_id
    ids=[e.id for e in rows if e.lesson_id==lid][:12]
    key=f'practice:{payload.category}:{payload.grammar_topic_id or "all"}:{payload.learning_objective_id or "all"}'
    if payload.attempt_id is not None:
        key = f'practice:mistakes:attempt:{payload.attempt_id}'
    return learning.start_session(db,user=user,lesson_id=lid,activity_key=key,exercise_ids=ids)


def mistakes(db,user,level,lesson_id=None):
    """Latest unresolved errors, with frozen objective evidence only."""
    eligible={e.id:e for e in candidates(db,user,level,'mistakes',lesson_id=lesson_id)}
    if not eligible:return dict(level=level,items=[])
    rows=db.execute(select(ExerciseAttempt,LearningSessionExercise,LearningSession)
        .join(LearningSessionExercise,ExerciseAttempt.session_exercise_id==LearningSessionExercise.id)
        .join(LearningSession,ExerciseAttempt.learning_session_id==LearningSession.id)
        .where(ExerciseAttempt.user_id==user.id,LearningSession.cefr_level==level,
            LearningSessionExercise.source_exercise_id.in_(eligible))
        .order_by(ExerciseAttempt.submitted_at.desc(),ExerciseAttempt.id).limit(200)).all()
    seen=set();items=[]
    for attempt,saved,session in rows:
        eid=saved.source_exercise_id
        if eid in seen:continue
        seen.add(eid)
        if attempt.is_correct:continue
        try:learning._session_for_user(db,session.id,user)
        except HTTPException:continue
        source=eligible[eid]
        objective_id=saved.exercise_snapshot.get('learning_objective_id')
        objective=None
        if (objective_id and str(source.learning_objective_id)==objective_id
                and db.scalar(select(LessonObjective).where(LessonObjective.lesson_id==session.lesson_id,
                    LessonObjective.objective_id==UUID(objective_id)))):
            objective=next((o for o in session.lesson_snapshot.get('objectives',[]) if o.get('id')==objective_id),None)
        items.append(dict(attempt_id=str(attempt.id),lesson_id=str(session.lesson_id),
            lesson_title=session.lesson_snapshot['title'],prompt=saved.exercise_snapshot['prompt'],
            explanation=attempt.feedback.get('explanation',''),
            learning_objective_id=objective_id if objective else None,
            objective_title=objective['title'] if objective else None,
            practice_available=True))
    return dict(level=level,items=items)


def session_review(db,user,session_id):
    session=learning._session_for_user(db,session_id,user)
    active=mistakes(db,user,session.cefr_level,session.lesson_id)['items']
    active_ids={i['attempt_id']:i for i in active}
    attempts=db.scalars(select(ExerciseAttempt).where(ExerciseAttempt.learning_session_id==session.id,
        ExerciseAttempt.user_id==user.id,ExerciseAttempt.is_correct.is_(False)).order_by(ExerciseAttempt.submitted_at)).all()
    items=[]
    for attempt in attempts:
        saved=db.get(LearningSessionExercise,attempt.session_exercise_id)
        linked=active_ids.get(str(attempt.id),{})
        items.append(dict(session_exercise_id=str(saved.id),prompt=saved.exercise_snapshot['prompt'],
            objective_title=linked.get('objective_title'),learning_objective_id=linked.get('learning_objective_id'),
            practice_available=bool(linked),explanation=attempt.feedback.get('explanation','')))
    return dict(session_id=str(session.id),level=session.cefr_level,lesson_id=str(session.lesson_id),items=items)
