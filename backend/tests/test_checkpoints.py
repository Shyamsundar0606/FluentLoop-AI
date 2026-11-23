from pathlib import Path
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select,func
from app.assessment_content import import_assessment_pack,load_assessment_pack
from app.learning_models import LearningSessionExercise,LessonProgress
from app.models import User
from test_interactive_learning import interactive,answer_for
from test_learning import _csrf,_set_role

@pytest.fixture
def all_source(interactive):
 client,sessions,_=interactive
 with sessions.begin() as db:
  for folder in ('personal','foundations','scenarios','depth','completion'):
   for file in sorted((Path(__file__).resolve().parents[1]/'content'/folder).glob('*.json')):import_assessment_pack(db,load_assessment_pack(file))
 return client,sessions

def test_module_and_level_plans_are_owned_read_only_and_unscored(all_source):
 client,sessions=all_source
 body=client.get('/api/v1/learning/checkpoints').json()
 assert len(body['plans'])==59 and sum(p['kind']=='module' for p in body['plans'])==52
 assert all(p['available'] and p['overall_score'] is None and not p['certification'] for p in body['plans'])
 assert all(p['speaking_lesson'] for p in body['plans'])
 assert all(p['rubrics']['writing'] and p['rubrics']['speaking'] for p in body['plans'])
 assert not any(key in str(body) for key in ('accepted_answers','correct_option_id','answer_pairs'))
 _set_role(sessions,'interactive@example.com','learner')
 ordinary=client.get('/api/v1/learning/checkpoints?stage=C2').json()
 assert all(not p['objective_checks'] and not p['writing_tasks'] and not p['speaking_lesson'] for p in ordinary['plans'])
 assert client.get('/api/v1/learning/checkpoints?stage=C3').status_code==422

def test_checkpoint_components_use_existing_frozen_persistence_and_do_not_complete_lessons(all_source):
 client,sessions=all_source
 plans=client.get('/api/v1/learning/checkpoints?stage=A2').json()['plans']
 component=next(p for p in plans if p['id']=='a2-05')['objective_checks'][0]
 payload=dict(skill=component['skill'],lesson_id=component['lesson_id'])
 one=client.post('/api/v1/learning/assessments/sessions',headers=_csrf(client),json=payload).json()
 assert client.post('/api/v1/learning/assessments/sessions',headers=_csrf(client),json=payload).json()['id']==one['id']
 with sessions() as db:keys={str(s.id):s.exercise_snapshot for s in db.scalars(select(LearningSessionExercise).where(LearningSessionExercise.learning_session_id==UUID(one['id'])))}
 for item in one['exercises']:
  response=client.post(f"/api/v1/learning/sessions/{one['id']}/answers",headers=_csrf(client),json=dict(session_exercise_id=item['id'],idempotency_key=str(uuid4()),**answer_for(keys[item['id']])))
  assert response.status_code==200
 assert client.post(f"/api/v1/learning/sessions/{one['id']}/complete",headers=_csrf(client)).status_code==200
 assert any(row['id']==one['id'] for row in client.get('/api/v1/learning/assessments/history').json()['items'])
 with sessions() as db:
  assert db.scalar(select(func.count(LessonProgress.id)))==0
  assert db.scalar(select(User).where(User.email=='interactive@example.com')).preferences.current_level=='a1'

def test_extended_writing_is_bounded_saved_and_idempotent(all_source):
 client,sessions=all_source
 item=next(i for i in client.get('/api/v1/learning/assessments?level=C2').json()['items'] if i['skill']=='writing')
 payload=dict(lesson_id=item['lesson_id'],idempotency_key=str(uuid4()),text='é'*8000)
 one=client.post('/api/v1/learning/assessments/writing',headers=_csrf(client),json=payload)
 assert one.status_code==200 and len(one.json()['original_text'])==8000
 assert client.post('/api/v1/learning/assessments/writing',headers=_csrf(client),json=payload).json()['id']==one.json()['id']
 assert client.post('/api/v1/learning/assessments/writing',headers=_csrf(client),json={**payload,'text':'é'*8001}).status_code==422
 assert client.post('/api/v1/learning/assessments/writing',headers=_csrf(client),content='x'*64001).status_code==413
 assert client.post('/api/v1/ai/conversations',headers=_csrf(client),content='x'*32001).status_code==413
 _set_role(sessions,'interactive@example.com','learner')
 assert client.get(f"/api/v1/learning/assessments/writing/{one.json()['id']}").status_code==404
