"""Read-only path projection: source objectives plus live, permitted learning data."""
import json
from pathlib import Path
from sqlalchemy import select
from app.learning_models import LessonProgress, WritingSubmission, LearningSession
from app.services.progression_policy import evidence_for
from app.curriculum_models import LessonObjective, LearningObjective
from app.services import study_content

MAP_PATH=Path(__file__).resolve().parents[2]/'content/learning-path.json'


def path_for(db,user):
    plan=json.loads(MAP_PATH.read_text(encoding='utf-8'))
    visible={lesson.slug:(lesson,preview) for level in ('A1','A2','B1','B2','C1','C2')
             for lesson,preview in study_content.lessons(db,user,level)}
    ids=[lesson.id for lesson,_ in visible.values()]
    progress=dict(db.execute(select(LessonProgress.lesson_id,LessonProgress.status).where(
        LessonProgress.user_id==user.id,LessonProgress.lesson_id.in_(ids))).all()) if ids else {}
    written=set(db.scalars(select(WritingSubmission.lesson_id).where(
        WritingSubmission.user_id==user.id,WritingSubmission.lesson_id.in_(ids)))) if ids else set()
    writing_ids=set(db.scalars(select(LessonObjective.lesson_id).join(LearningObjective).where(
        LessonObjective.lesson_id.in_(ids),LearningObjective.skill_category=='writing'))) if ids else set()
    sessions=db.scalars(select(LearningSession).where(LearningSession.user_id==user.id,
        LearningSession.lesson_id.in_(ids),LearningSession.status=='completed',
        LearningSession.activity_key=='lesson')).all() if ids else []
    # Skill identity comes from permitted lesson objectives, not a slug suffix.
    stages=[]
    for stage in plan['stages']:
        modules=[]
        for module in stage['modules']:
            lessons=[]
            for slug in module['lesson_slugs']:
                if slug not in visible:continue
                lesson,preview=visible[slug];writing=lesson.id in writing_ids
                state='saved_submission' if writing and lesson.id in written else progress.get(lesson.id,'not_started')
                lessons.append(dict(id=str(lesson.id),title=lesson.title,level=lesson.difficulty_level,
                    status=state,draft_preview=preview,kind='writing' if writing else 'lesson',content_version=lesson.content_version,
                    href=f'/assessments/writing/{lesson.id}' if writing else f'/learn/{lesson.id}'))
            complete=sum(item['status'] in ('completed','saved_submission') for item in lessons)
            modules.append({key:value for key,value in module.items() if key!='lesson_slugs'} | dict(
                lessons=lessons,available_lessons=len(lessons),completed_activities=complete,
                remaining_activities=len(lessons)-complete,formative_evidence=evidence_for(lessons,sessions)))
        stages.append(dict(code=stage['code'],official_cefr=stage['official_cefr'],introduction=stage['introduction'],
            modules=modules,available_lessons=sum(m['available_lessons'] for m in modules),
            completed_activities=sum(m['completed_activities'] for m in modules),
            coverage_complete=False))
    next_activity=None
    for stage in stages:
        for module in stage['modules']:
            revisions=set(module['formative_evidence']['revision_lesson_ids'])
            candidate=next((lesson for lesson in module['lessons'] if lesson['id'] in revisions
                or lesson['status'] not in ('completed','saved_submission')),None)
            if candidate:
                next_activity=dict(stage=stage['code'],module_id=module['id'],lesson_id=candidate['id'],href=candidate['href'],
                    reason='practice_or_revision' if candidate['id'] in revisions else 'continue_productive_task')
                break
        if next_activity:break
    return dict(stages=stages,saved_level=user.preferences.current_level.upper(),certification=False,next_activity=next_activity,
                prerequisite_policy='Recommended preparation; not an automatic level award.',
                notice='Available practice is shown separately from planned coverage. Completing activities does not certify a CEFR level.')
