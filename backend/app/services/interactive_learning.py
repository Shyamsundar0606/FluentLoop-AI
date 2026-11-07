"""Authorized projections and focused sessions using the persisted M04 engine."""
from uuid import UUID
from sqlalchemy import select
from fastapi import HTTPException
from app.curriculum_models import Exercise, GrammarTopic, LessonGrammar, LessonObjective, LearningObjective, Unit
from app.learning_models import ExerciseAttempt, LearningSession, LearningSessionExercise
from app.services import learning_service as learning, study_content
from app.services.content_permissions import topic_allowed


def library(db,user,level):
    result=[]
    for lesson,preview in study_content.lessons(db,user,level):
        progress=learning.get_lesson_progress(db,user=user,lesson_id=lesson.id)
        active=db.scalar(select(LearningSession).where(LearningSession.user_id==user.id,
            LearningSession.lesson_id==lesson.id,LearningSession.activity_key=='lesson',LearningSession.status=='in_progress'))
        objectives=db.scalars(select(LearningObjective).join(LessonObjective).where(LessonObjective.lesson_id==lesson.id)).all()
        result.append(dict(id=str(lesson.id),title=lesson.title,description=lesson.description,
            unit_id=str(lesson.unit_id),unit_title=db.get(Unit,lesson.unit_id).title,estimated_minutes=lesson.estimated_minutes,draft_preview=preview,
            objectives=[dict(id=str(o.id),title=o.title,description=o.description) for o in objectives],
            status=progress['status'],answered=active.current_exercise_position if active else 0,
            total=active.total_exercises if active else 0,session_id=str(active.id) if active else None))
    return dict(level=level,items=result)


def grammar(db,user,level):
    permitted={l.id:(l,p) for l,p in study_content.lessons(db,user,level)}
    if not permitted:return dict(level=level,items=[])
    rows=db.execute(select(GrammarTopic,LessonGrammar.lesson_id).join(LessonGrammar).where(
        LessonGrammar.lesson_id.in_(permitted),GrammarTopic.cefr_level==level).order_by(GrammarTopic.title)).all()
    result={}
    snapshots={}
    rows.sort(key=lambda row: permitted[row[1]][0].slug != row[0].teaching_metadata.get('preferred_lesson_slug'))
    for topic,lid in rows:
        if not topic_allowed(topic,user):continue
        if topic.id in result and topic.teaching_metadata.get('curriculum_supplement'):
            result[topic.id]['lesson_ids'].append(str(lid))
            continue
        lesson,preview=permitted[lid]
        if lid not in snapshots:
            _,unit,course,_=learning._accessible_lesson(db,lid,user)
            snapshots[lid]=learning._lesson_snapshot(db,lesson,unit,course,user)
        snapshot=snapshots[lid]
        saved=next(t for t in snapshot['grammar'] if t['id']==str(topic.id))
        authored=[r for r in saved['rules'] if r.get('code')==topic.teaching_metadata.get('rule_code')]
        word_examples=topic.teaching_metadata.get('vocabulary_examples')
        entry=result.setdefault(topic.id,dict(id=str(topic.id),title=topic.title,summary=topic.summary,
            rules=authored or saved['rules'],teaching=topic.teaching_metadata,level=level,
            publication_status=topic.publication_status,lesson_ids=[],objectives=[],
            vocabulary=[word for word in snapshot['vocabulary'] if not word_examples or word['lemma'] in word_examples],
            explanation_language=user.preferences.explanation_language,
            available_exercises=len(candidates(db,user,level,'grammar',topic.id))))
        entry['lesson_ids'].append(str(lid))
        objective_code=topic.teaching_metadata.get('objective_code')
        entry['objectives'].extend(o for o in snapshot['objectives'] if not objective_code or o['code']==objective_code)
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
    if not rows:raise HTTPException(409,'No authorized exercises are available for this practice yet.')
    # One real lesson per focused session keeps source permissions and snapshots
    # intact; subsequent lessons can be practiced separately.
    lid=rows[0].lesson_id
    ids=[e.id for e in rows if e.lesson_id==lid][:12]
    key=f'practice:{payload.category}:{payload.grammar_topic_id or "all"}:{payload.learning_objective_id or "all"}'
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
