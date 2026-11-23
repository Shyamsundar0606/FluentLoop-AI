import importlib.util
from pathlib import Path
from uuid import UUID
import pytest
from pydantic import ValidationError
from app.services.exercise_formats import ListeningDefinition,MAX_LISTENING_CHARACTERS
from app.learning_models import LearningSessionExercise
from test_interactive_learning import interactive,start
from test_learning import _csrf,_set_role

ROOT=Path(__file__).resolve().parents[1]
def load_script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def test_all_previously_empty_modules_have_coherent_reproducible_source():
    from app.assessment_content import load_assessment_pack,AssessmentPack
    author=load_script('build_missing_modules')
    assert len(author.MODULES)==len({row['id'] for row in author.MODULES})==17
    for row in author.MODULES:
        body=author.build(row);pack=load_assessment_pack(ROOT/'content/completion'/f"{row['id']}-completion-{body['version']}.json")
        assert pack==AssessmentPack.model_validate(body)
        assert pack.tasks[1].prerequisites==['read-and-notice']
        assert pack.tasks[2].prerequisites==['read-and-notice','listen-and-integrate']
        assert len(pack.glossary)==3 and len(pack.tasks[0].grammar)==1
        assert all(option.strip() for task in pack.tasks for ex in task.exercises for option in ex.options)
    audit=load_script('audit_curriculum_coverage').audit()
    modules=[m for stage in audit['stages'] for m in stage['modules']]
    assert len(modules)==52 and all(m['main_lessons']+m['staged_lessons'] for m in modules)
    assert sum(m['main_lessons'] for m in modules)==181 and sum(m['staged_lessons'] for m in modules)==5
    assert all(not m['competency_demonstrated'] and m['qualified_human_review']=='pending' for m in modules)

def test_completion_import_preserves_all_prior_sources_and_answer_keys():
    body=load_script('validate_missing_modules').validate()
    assert body['modules']==17 and body['scored_exercises']==102
    assert body['main_import_authorized'] is False

def test_listening_limit_matches_existing_worker_contract():
    from app.speech.schemas import Synthesize
    assert MAX_LISTENING_CHARACTERS==600
    assert ListeningDefinition(text_fr='é'*600).text_fr==Synthesize(text='é'*600).text
    for length in (0,601):
        with pytest.raises(ValidationError):ListeningDefinition(text_fr='é'*length)

def test_longer_listening_route_keeps_boundaries_and_revocation(interactive,monkeypatch):
    client,sessions,lid=interactive;body=start(client,lid);item=body['exercises'][4]
    path=f"/api/v1/learning/sessions/{body['id']}/exercises/{item['id']}/audio"
    calls=[]
    class Speech:
        def synthesize(self,text):calls.append(text);return b'RIFF'+b'\0'*40
    monkeypatch.setattr('app.speech.providers.get_speech_provider',lambda:Speech())
    def set_script(length):
        with sessions.begin() as db:
            saved=db.get(LearningSessionExercise,UUID(item['id']));saved.exercise_snapshot={**saved.exercise_snapshot,'text_fr':'é'*length}
    set_script(600);assert client.post(path,headers=_csrf(client)).status_code==200 and len(calls[-1])==600
    set_script(601);assert client.post(path,headers=_csrf(client)).status_code==409 and len(calls)==1
    set_script(600);_set_role(sessions,'interactive@example.com','learner')
    assert client.post(path,headers=_csrf(client)).status_code==404 and len(calls)==1
