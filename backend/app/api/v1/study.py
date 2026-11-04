from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import current_auth_context, require_csrf, AuthContext
from app.services.rate_limit import enforce_rate_limit
from app.services import daily_learning_service as plans, spaced_repetition_service as reviews
from app.study_models import DailyPlan
from app.study_schemas import (GeneratePlan, StartReview, AnswerReview, PlanView, PlanPage, RecommendationView,
    ActivityView, ReviewSessionView, ReviewFeedback, DueView, ReviewProgress, HistoryPage)

router=APIRouter(tags=['Daily study and vocabulary review'])

def read_context(request:Request, context:AuthContext=Depends(current_auth_context)):
    enforce_rate_limit(request,f'study-read:{context.user.id}',240,60)
    return context

def limited(request:Request, context:AuthContext=Depends(require_csrf)):
    enforce_rate_limit(request,f'study:{context.user.id}',60,60)
    return context

@router.get('/study/today',response_model=PlanView | None)
def today(context:AuthContext=Depends(read_context),db:Session=Depends(get_db)):
    return plans.today(db,context.user)

@router.post('/study/today/generate',response_model=PlanView)
def generate(payload:GeneratePlan,context:AuthContext=Depends(limited),db:Session=Depends(get_db)):
    return plans.generate(db,context.user,payload)

@router.get('/study/recommendations',response_model=list[RecommendationView])
def recommendations(context:AuthContext=Depends(read_context),db:Session=Depends(get_db)):
    return plans.recommendations(db,context.user)

@router.get('/study/plans',response_model=PlanPage)
def history(limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0,le=100000),context:AuthContext=Depends(read_context),db:Session=Depends(get_db)):
    rows=db.scalars(select(DailyPlan).where(DailyPlan.user_id==context.user.id).order_by(DailyPlan.local_study_date.desc(),DailyPlan.created_at.desc(),DailyPlan.id).offset(offset).limit(limit)).all()
    return dict(items=[plans.view(db,context.user,p) for p in rows],limit=limit,offset=offset)

@router.get('/study/plans/{plan_id}',response_model=PlanView)
def get_plan(plan_id:UUID,context:AuthContext=Depends(read_context),db:Session=Depends(get_db)):
    return plans.view(db,context.user,plans.owned(db,context.user,plan_id))

@router.post('/study/activities/{activity_id}/start',response_model=ActivityView)
def start_activity(activity_id:UUID,context:AuthContext=Depends(limited),db:Session=Depends(get_db)):
    return plans.start_activity(db,context.user,activity_id)

@router.post('/study/activities/{activity_id}/complete',response_model=PlanView)
def complete_activity(activity_id:UUID,context:AuthContext=Depends(limited),db:Session=Depends(get_db)):
    return plans.complete_activity(db,context.user,activity_id)

@router.get('/review/due',response_model=DueView)
def due(context:AuthContext=Depends(read_context),db:Session=Depends(get_db)):
    return reviews.due(db,context.user)

@router.post('/review/sessions',response_model=ReviewSessionView)
def start_review(payload:StartReview,context:AuthContext=Depends(limited),db:Session=Depends(get_db)):
    return reviews.start(db,context.user,payload)

@router.get('/review/sessions/{session_id}',response_model=ReviewSessionView)
def get_review(session_id:UUID,context:AuthContext=Depends(read_context),db:Session=Depends(get_db)):
    return reviews.view(db,context.user,reviews.owned(db,context.user,session_id))

@router.post('/review/sessions/{session_id}/answers',response_model=ReviewFeedback)
def answer(session_id:UUID,payload:AnswerReview,context:AuthContext=Depends(limited),db:Session=Depends(get_db)):
    return reviews.submit(db,context.user,session_id,payload)

@router.post('/review/sessions/{session_id}/complete',response_model=ReviewSessionView)
def complete(session_id:UUID,context:AuthContext=Depends(limited),db:Session=Depends(get_db)):
    return reviews.complete(db,context.user,session_id)

@router.get('/review/progress',response_model=ReviewProgress)
def progress(context:AuthContext=Depends(read_context),db:Session=Depends(get_db)):
    return reviews.progress(db,context.user)

@router.get('/review/history',response_model=HistoryPage)
def review_history(limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0,le=100000),context:AuthContext=Depends(read_context),db:Session=Depends(get_db)):
    return reviews.history(db,context.user,limit,offset)
