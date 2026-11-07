"""Persisted deterministic plans. No LLM calls and no fabricated topic links."""
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from app.study_models import DailyPlan, DailyActivity, ReviewSession, ReviewAttempt
from app.learning_models import LearningSession, LearningSessionExercise, ExerciseAttempt, LessonProgress
from app.curriculum_models import Exercise
from app.ai.models import Conversation, Message
from app.speech.models import SpeechSession, SpeechTurn
from app.config import get_settings
from app.services import study_clock as clock, study_content as content, spaced_repetition_service as reviews
from app.study_schemas import StartReview

def context(user):
    at = clock.now()
    day, zone = clock.study_date(at, user.profile.timezone if user.profile else 'UTC')
    return at, day, zone, reviews.level_for(user), user.preferences.daily_study_minutes if user.preferences else 15

def recommendations(db, user):
    level = reviews.level_for(user)
    permitted = {lesson.id:(lesson,preview) for lesson,preview in content.lessons(db,user,level)}
    result = []
    state = reviews.due(db,user,level)
    if state['due_count'] or state['new_vocabulary_count']:
        result.append(dict(activity_type='vocabulary_review', title='Review vocabulary', priority=100 if state['due_count'] else 60,
            reason=f"{state['due_count']} vocabulary cards due." if state['due_count'] else 'Learn up to three words from permitted vocabulary.',
            evidence_attempt_ids=[], draft_preview=any(preview for _,preview in permitted.values())))
    active = db.scalars(select(LearningSession).where(LearningSession.user_id==user.id,
        LearningSession.cefr_level==level, LearningSession.status=='in_progress',LearningSession.activity_key=='lesson').order_by(LearningSession.last_activity_at.desc(),LearningSession.id)).all()
    for session in active:
        if session.lesson_id in permitted:
            lesson, preview = permitted[session.lesson_id]
            result.append(dict(activity_type='continue_lesson', title=f'Continue {lesson.title}', priority=90,
                reason='Resume your saved unfinished lesson.', lesson_id=lesson.id, learning_session_id=session.id,
                evidence_attempt_ids=[], draft_preview=preview))
    # An exercise has only a lesson link in the existing schema. Do not infer a
    # specific grammar weakness from a lesson containing several topics.
    errors = db.execute(select(ExerciseAttempt, LearningSession.lesson_id, LearningSessionExercise.source_exercise_id, LearningSession.lesson_content_version)
        .join(LearningSession, ExerciseAttempt.learning_session_id==LearningSession.id)
        .join(LearningSessionExercise, ExerciseAttempt.session_exercise_id==LearningSessionExercise.id)
        .join(Exercise, LearningSessionExercise.source_exercise_id==Exercise.id)
        .where(ExerciseAttempt.user_id==user.id, LearningSession.cefr_level==level, Exercise.lesson_id==LearningSession.lesson_id)
        .order_by(ExerciseAttempt.submitted_at.desc(), ExerciseAttempt.id).limit(200)).all()
    by_lesson = {}
    unresolved = {}
    for attempt, lesson_id, exercise_id, version in errors:
        if lesson_id in permitted and version==permitted[lesson_id][0].content_version:
            key=(lesson_id,exercise_id)
            if key not in unresolved:
                unresolved[key]=not attempt.is_correct
            if attempt.is_correct:
                unresolved[key]=False
            if not unresolved[key]:
                continue
            by_lesson.setdefault(lesson_id,[]).append(attempt.id)
    for lesson_id, evidence in sorted(by_lesson.items(), key=lambda pair:(-len(pair[1]),str(pair[0]))):
        lesson, preview = permitted[lesson_id]
        # New formats have explicit stable objective links. Historical unmapped
        # answers retain lesson-level recommendations without guessed weaknesses.
        from app.services.interactive_learning import candidates
        from app.curriculum_models import LearningObjective,LessonObjective
        mapped={}
        for exercise in candidates(db,user,level,'mistakes',lesson_id=lesson_id):
            objective=exercise.learning_objective_id
            if objective and db.scalar(select(LessonObjective).where(LessonObjective.lesson_id==lesson_id,LessonObjective.objective_id==objective)):
                mapped.setdefault(objective,[]).append(exercise.id)
        for objective,exercise_ids in mapped.items():
            linked=db.get(LearningObjective,objective)
            objective_evidence=[aid for aid,saved in db.execute(select(ExerciseAttempt.id,LearningSessionExercise.exercise_snapshot).join(LearningSessionExercise,
                ExerciseAttempt.session_exercise_id==LearningSessionExercise.id).where(ExerciseAttempt.id.in_(evidence),
                LearningSessionExercise.source_exercise_id.in_(exercise_ids))).all()
                if saved.get('learning_objective_id')==str(objective)]
            if objective_evidence:
                result.append(dict(activity_type='lesson_review',title=f'Practice: {linked.title}',priority=85,
                    reason=f'{len(objective_evidence)} recorded errors linked to this learning objective remain unresolved.',
                    lesson_id=lesson_id,learning_objective_id=objective,practice_category='mistakes',
                    evidence_attempt_ids=objective_evidence,draft_preview=preview))
        result.append(dict(activity_type='lesson_review', title=f'Revisit {lesson.title}', priority=80,
            reason=f'{len(evidence)} recorded incorrect answers remain unresolved in the latest 200 attempts; revisit this lesson’s examples and explanations.',
            lesson_id=lesson_id, evidence_attempt_ids=evidence, draft_preview=preview))
    completed = set(db.scalars(select(LessonProgress.lesson_id).where(LessonProgress.user_id==user.id, LessonProgress.status=='completed')).all())
    active_ids = {s.lesson_id for s in active}
    for lesson, preview in permitted.values():
        if lesson.id not in completed and lesson.id not in active_ids:
            result.append(dict(activity_type='new_lesson', title=f'Learn {lesson.title}', priority=60,
                reason='Next available lesson in curriculum order at your saved French level.', lesson_id=lesson.id,
                evidence_attempt_ids=[], draft_preview=preview))
    focus = user.preferences.learning_focus if user.preferences else 'balanced'
    goal = user.profile.learning_goal if user.profile else None
    speaking_goal=goal in ('Daily conversations','Living in France')
    tutor_goal=goal in ('French for work','French for university','French examinations')
    practice = [dict(activity_type='tutor', title='Practice with your French tutor', priority=35 if focus in ('reading','writing') else 30 if tutor_goal else 20,
                    reason=f'Practice at {level} with {user.preferences.explanation_language if user.preferences else "English"} explanations' + (' toward your saved learning goal.' if goal else '.'), evidence_attempt_ids=[], draft_preview=False),
                dict(activity_type='speaking', title='Practice a short French conversation', priority=35 if focus in ('speaking','listening') else 25 if speaking_goal else 10,
                    reason='Use the existing microphone and transcript review workflow at your saved level.', evidence_attempt_ids=[], draft_preview=False)]
    result.extend(practice)
    return sorted(result,key=lambda r:-r['priority'])

def generate(db,user,payload):
    reviews.lock_user(db,user)
    at, day, zone, level, target = context(user)
    plan = db.scalar(select(DailyPlan).where(DailyPlan.user_id==user.id, DailyPlan.local_study_date==day, DailyPlan.cefr_level==level).with_for_update())
    if plan:
        if plan.generation_request_id == payload.request_id:
            if plan.generation_was_regeneration != payload.regenerate:
                raise HTTPException(409,'Request ID belongs to a different generation action.')
            return view(db,user,plan)
        if not payload.regenerate:
            return view(db,user,plan)
        existing = db.scalars(select(DailyActivity).where(DailyActivity.plan_id==plan.id, DailyActivity.generation==plan.generation)).all()
        if plan.status != 'ready' or any(a.status != 'pending' for a in existing):
            raise HTTPException(409,'A started plan cannot be regenerated. Resume the saved activities.')
        for activity in existing:
            activity.status='cancelled'
        plan.generation += 1
        plan.target_minutes, plan.generated_at, plan.updated_at = target, at, at
        plan.generation_request_id, plan.generation_was_regeneration = payload.request_id, True
    else:
        if payload.regenerate:
            raise HTTPException(409,'Create a plan before regenerating it.')
        plan=DailyPlan(user_id=user.id, cefr_level=level, local_study_date=day, timezone_name=zone,
            target_minutes=target, generated_at=at, generation_request_id=payload.request_id)
        db.add(plan)
        db.flush()
    ranked = recommendations(db,user)
    chosen=[]
    lesson_chosen=False
    remaining=target
    # Reserve realistic amounts for actual available tasks, not a fixed template.
    for candidate in ranked:
        kind=candidate['activity_type']
        if kind in ('continue_lesson','lesson_review','new_lesson'):
            if lesson_chosen:
                continue
            minutes=min(5,remaining)
            lesson_chosen=True
        elif kind=='vocabulary_review':
            minutes=min(2,remaining)  # up to three cards, not all due cards
        else:
            # At most ten minutes per conversation; retain a distinct speaking
            # opportunity when enough time is available, never clone fillers.
            minutes=min(10, remaining if len(chosen)==0 or candidate==ranked[-1] else max(1,(remaining+1)//2))
        if remaining<=0:
            break
        chosen.append((candidate,minutes))
        remaining-=minutes
    # Assign spare time to an existing real practice opportunity within its cap.
    for i,(candidate,minutes) in enumerate(chosen):
        if candidate['activity_type'] in ('tutor','speaking') and remaining:
            extra=min(10-minutes,remaining)
            chosen[i]=(candidate,minutes+extra)
            remaining-=extra
    for order,(candidate,minutes) in enumerate(chosen,1):
        db.add(DailyActivity(user_id=user.id,plan_id=plan.id,generation=plan.generation,
            activity_type=candidate['activity_type'],title=candidate['title'],reason=candidate['reason'],
            evidence={'attempt_ids':[str(a) for a in candidate['evidence_attempt_ids']],
                'learning_objective_id':str(candidate['learning_objective_id']) if candidate.get('learning_objective_id') else None,
                'practice_category':candidate.get('practice_category')},
            linked_lesson_id=candidate.get('lesson_id'),linked_learning_session_id=candidate.get('learning_session_id'),
            estimated_minutes=minutes,sequence_order=order))
    db.commit()
    return view(db,user,plan)

def owned(db,user,pid,lock=False):
    query=select(DailyPlan).where(DailyPlan.id==pid,DailyPlan.user_id==user.id)
    plan=db.scalar(query.with_for_update() if lock else query)
    if not plan:
        raise HTTPException(404,'Daily plan not found.')
    return plan

def permitted_activity(db,user,plan,activity):
    if activity.linked_learning_session_id:
        session=db.get(LearningSession,activity.linked_learning_session_id)
        if not session or session.user_id!=user.id or session.lesson_id!=activity.linked_lesson_id:
            return None
        from app.services.learning_service import _session_exercise_access
        try:_session_exercise_access(db,session,user)
        except HTTPException:return None
    if activity.linked_review_session_id:
        session=db.get(ReviewSession,activity.linked_review_session_id)
        if not session or session.user_id!=user.id or session.cefr_level!=plan.cefr_level:
            return None
    conversation_id=activity.linked_conversation_id
    if activity.linked_speech_session_id:
        session=db.get(SpeechSession,activity.linked_speech_session_id)
        if not session or session.user_id!=user.id:
            return None
        conversation_id=session.ai_conversation_id
    if conversation_id:
        from app.ai.orchestrator import owned as owned_conversation
        try:
            owned_conversation(db,user,conversation_id)
        except HTTPException:
            return None
    if activity.linked_lesson_id:
        return dict((l.id,p) for l,p in content.lessons(db,user,plan.cefr_level)).get(activity.linked_lesson_id)
    if activity.activity_type=='vocabulary_review':
        vocabulary=content.vocabulary(db,user,plan.cefr_level)
        return any(v['draft_preview'] for v in vocabulary.values()) if vocabulary else None
    return False

def finished(db,user,activity):
    if not activity.started_at:
        return False
    if activity.linked_review_session_id:
        session=db.get(ReviewSession,activity.linked_review_session_id)
        return bool(session and session.user_id==user.id and session.status=='completed' and
            db.scalar(select(ReviewAttempt.id).where(ReviewAttempt.session_id==session.id,ReviewAttempt.user_id==user.id).limit(1)))
    if activity.linked_learning_session_id:
        session=db.get(LearningSession,activity.linked_learning_session_id)
        return bool(session and session.user_id==user.id and session.status=='completed' and
                    session.completed_at and clock.utc(session.completed_at)>=clock.utc(activity.started_at))
    if activity.linked_speech_session_id:
        return db.scalar(select(SpeechTurn.id).where(SpeechTurn.speech_session_id==activity.linked_speech_session_id,
            SpeechTurn.user_id==user.id,SpeechTurn.status=='success',SpeechTurn.transcription_status.in_(('transcribed','user_confirmed')),
            SpeechTurn.created_at>=activity.started_at).limit(1)) is not None
    if activity.linked_conversation_id:
        return db.scalar(select(Message.id).join(Conversation,Message.conversation_id==Conversation.id).where(
            Conversation.user_id==user.id,Conversation.id==activity.linked_conversation_id,
            Message.role=='assistant',Message.response_status=='success',Message.created_at>=activity.started_at).limit(1)) is not None
    return False

def url(activity):
    if activity.linked_review_session_id:
        return f'/review/sessions/{activity.linked_review_session_id}'
    if activity.linked_speech_session_id:
        return f'/voice-practice/conversations/{activity.linked_speech_session_id}'
    if activity.linked_conversation_id:
        return f'/ai-tutor/{activity.linked_conversation_id}'
    if activity.linked_learning_session_id:
        return f'/learning/sessions/{activity.linked_learning_session_id}'
    return None

def view(db,user,plan):
    rows=db.scalars(select(DailyActivity).where(DailyActivity.plan_id==plan.id,DailyActivity.generation==plan.generation).order_by(DailyActivity.sequence_order)).all()
    shown=[]
    hidden=0
    changed=False
    for activity in rows:
        preview=permitted_activity(db,user,plan,activity)
        if preview is None:
            hidden+=1
            continue
        complete=finished(db,user,activity) if activity.status=='in_progress' else activity.status=='completed'
        if complete and activity.status!='completed':
            activity.status,activity.completed_at,activity.updated_at='completed',clock.now(),clock.now()
            changed=True
        shown.append(dict(id=activity.id,activity_type=activity.activity_type,title=activity.title,reason=activity.reason,
            estimated_minutes=activity.estimated_minutes,status=activity.status,sequence_order=activity.sequence_order,
            draft_preview=preview,url=url(activity),completion_available=complete))
    if rows and all(a.status=='completed' for a in rows) and plan.status!='completed':
        plan.status,plan.completed_at='completed',clock.now()
        changed=True
    if changed:
        plan.updated_at=clock.now()
        db.commit()
    return dict(id=plan.id,cefr_level=plan.cefr_level,local_study_date=plan.local_study_date,timezone_name=plan.timezone_name,
        target_minutes=plan.target_minutes,planned_minutes=sum(a['estimated_minutes'] for a in shown),status=plan.status,
        plan_version=plan.plan_version,generation=plan.generation,activities=shown,unavailable_activity_count=hidden,
        due_review_count=reviews.due(db,user,plan.cefr_level)['due_count'],generated_at=plan.generated_at,completed_at=plan.completed_at)

def today(db,user):
    _,day,_,level,_=context(user)
    plan=db.scalar(select(DailyPlan).where(DailyPlan.user_id==user.id,DailyPlan.local_study_date==day,DailyPlan.cefr_level==level))
    return view(db,user,plan) if plan else None

def start_activity(db,user,aid):
    reviews.lock_user(db,user)
    activity=db.scalar(select(DailyActivity).where(DailyActivity.id==aid,DailyActivity.user_id==user.id).with_for_update())
    if not activity:
        raise HTTPException(404,'Study activity not found.')
    plan=owned(db,user,activity.plan_id,lock=True)
    if activity.generation!=plan.generation or permitted_activity(db,user,plan,activity) is None:
        raise HTTPException(404,'Study activity is no longer available.')
    if reviews.level_for(user)!=plan.cefr_level:
        raise HTTPException(409,'Select this plan\'s French level before resuming its activities.')
    if activity.status!='pending':
        return next(a for a in view(db,user,plan)['activities'] if a['id']==aid)
    at=clock.now()
    if activity.activity_type=='vocabulary_review':
        started=reviews.start(db,user,StartReview(request_id=activity.id,limit=3),commit=False)
        activity.linked_review_session_id=started['id']
    elif activity.linked_lesson_id:
        from app.services.learning_service import start_session
        objective=activity.evidence.get('learning_objective_id')
        if objective and activity.evidence.get('practice_category')=='mistakes':
            from app.services.interactive_learning import candidates
            from uuid import UUID
            rows=candidates(db,user,plan.cefr_level,'mistakes',lesson_id=activity.linked_lesson_id,objective_id=UUID(objective))
            if not rows:raise HTTPException(409,'These mistakes have been resolved. Create a new plan when available.')
            started,_=start_session(db,user=user,lesson_id=activity.linked_lesson_id,commit=False,
                activity_key=f'practice:mistakes:all:{objective}',exercise_ids=[e.id for e in rows][:12])
        else:
            started,_=start_session(db,user=user,lesson_id=activity.linked_lesson_id,commit=False)
        activity.linked_learning_session_id=started.id
    else:
        settings=get_settings()
        conversation=Conversation(user_id=user.id,title=activity.title,mode='roleplay' if activity.activity_type=='speaking' else 'tutor',
            cefr_level=plan.cefr_level,preview_mode=False,model_provider=settings.ai_provider,model_name=settings.ollama_model)
        db.add(conversation)
        db.flush()
        if activity.activity_type=='speaking':
            speech=SpeechSession(user_id=user.id,ai_conversation_id=conversation.id,cefr_level=plan.cefr_level)
            db.add(speech)
            db.flush()
            activity.linked_speech_session_id=speech.id
        else:
            activity.linked_conversation_id=conversation.id
    activity.status,activity.started_at,activity.updated_at='in_progress',at,at
    plan.status,plan.updated_at='in_progress',at
    db.commit()
    return next(a for a in view(db,user,plan)['activities'] if a['id']==aid)

def complete_activity(db,user,aid):
    activity=db.scalar(select(DailyActivity).where(DailyActivity.id==aid,DailyActivity.user_id==user.id).with_for_update())
    if not activity:
        raise HTTPException(404,'Study activity not found.')
    plan=owned(db,user,activity.plan_id,lock=True)
    if activity.generation!=plan.generation or permitted_activity(db,user,plan,activity) is None:
        raise HTTPException(404,'Study activity is no longer available.')
    if activity.status!='completed' and not finished(db,user,activity):
        raise HTTPException(409,'Complete the linked practice before marking this activity complete.')
    if activity.status!='completed':
        activity.status,activity.completed_at='completed',clock.now()
    db.commit()
    return view(db,user,plan)
