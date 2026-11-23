import importlib.util
import json
from pathlib import Path
import pytest
from app.assessment_content import load_assessment_pack,import_assessment_pack
from test_interactive_learning import interactive

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('file',sorted((ROOT/'content/writing-bridges').glob('*.json')),ids=lambda p:p.stem)
def test_future_writing_bridges_are_unscored_drafts_with_stable_prerequisites(interactive,file):
 _,sessions,_=interactive;pack=load_assessment_pack(file)
 assert all(t.skill=='writing' and not t.exercises and 'Review criteria:' in t.context for t in pack.tasks)
 assert (pack.learning_stage=='A0')==(pack.version=='0.9.0')
 with sessions.begin() as db:
  assert not import_assessment_pack(db,pack)['reused']
  assert import_assessment_pack(db,pack)['reused']

def test_bridge_source_models_reproduce():
 spec=importlib.util.spec_from_file_location('bridges',ROOT/'scripts/build_writing_bridges.py')
 author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
 assert len(author.ROWS)==5
 for pack in author.packs():
  file=ROOT/'content/writing-bridges'/f"{(pack.learning_stage or pack.level).lower()}-writing-{pack.version}.json"
  assert pack==load_assessment_pack(file)

def test_advanced_model_is_a_staged_example_not_a_proficiency_claim():
 body=json.loads((ROOT/'content/review-supplements/c2-museum-model-draft.json').read_text(encoding='utf-8'))
 assert body['qualified_human_review']=='pending'
 assert body['main_import_authorized'] is False and body['served_in_application'] is False
 assert 520<=len(body['model_essay'].split())<=620
 assert body['annotations'] and 'not a unique answer' in body['notice']
