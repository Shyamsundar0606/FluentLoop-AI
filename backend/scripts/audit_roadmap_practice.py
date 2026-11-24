"""Crosswalk the user's68-topic roadmap without rewriting the 52-module live map."""
import json,hashlib,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TARGETS={
 'A1':[1,1,2,2,3,3,3,5,4,6,7,9],
 'A2':[8,2,2,1,1,4,4,6,5,1,1,6],
 'B1':[1,4,4,3,5,5,6,2,6,7,6,8],
 'B2':[4,1,4,3,3,6,2,5,7,1,5,8],
 'C1':[4,4,4,4,6,6,5,2,4,8],
 'C2':[2,2,4,1,3,7,5,4,6,8],
}

def audit():
 spec=importlib.util.spec_from_file_location('roadmap_builder',Path(__file__).with_name('build_roadmap_practice.py'))
 author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
 source=author.rows();packs=list(author.packs());mapping=json.loads((ROOT/'backend/content/learning-path.json').read_text())
 live_modules={m['id'] for s in mapping['stages'] for m in s['modules']};topics=[];previous=None
 for level in author.LEVELS:
  for number,row in enumerate(source[level],1):
   identity=f'{level.lower()}-roadmap-{number:02d}';module=f'{level.lower()}-{TARGETS[level][number-1]:02d}'
   assert module in live_modules
   pack=next(p for p in packs if p.level==level and any(t.key==f'topic-{number:02d}-practice' for t in p.tasks))
   topic=dict(id=identity,level=level,title=row[0],existing_module_crosswalk=module,
    recommended_preparation=[previous] if previous else ['A0 foundations where needed'],
    release=pack.version,practice_slug=f'm10-assessments-{level.lower()}-{pack.version}-topic-{number:02d}-practice',
    transfer_slug=f'm10-assessments-{level.lower()}-{pack.version}-topic-{number:02d}-transfer',
    scored_exercises=4,writing_speaking_task=1,contextual_expressions=3,script_characters=len(row[7]),
    reading_words=len(row[5].split()),rule_and_model=True,main_import_authorized=False,qualified_human_review='pending',
    limits=['Supported practice, not unseen proficiency testing','Three contextual expressions, not a complete10–20-word vocabulary lesson',
     'Short synthetic script cannot establish spontaneous or varied-accent comprehension','Productive transfer requires qualitative human review'])
   topics.append(topic);previous=identity
 assert len(topics)==68 and len({t['id'] for t in topics})==68
 return dict(scope='Supplementary roadmap practice; existing52-module map, main181 lessons and prior5 staged bridges unchanged',
  levels={level:dict(topics=len(source[level]),lessons=2*len(source[level]),scored_exercises=4*len(source[level]),open_transfer_tasks=len(source[level])) for level in author.LEVELS},
  topics=topics,source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'backend/content/roadmap').glob('*.json'))},
  main_import_authorized=False,official_exam_simulation=False,cefr_calibration='not established',
  reference_notes='Roadmap grouping and estimated hours are planning suggestions, not official CEFR grammar requirements or guarantees. Garbled vocabulary graph not converted into invented targets. No account-level change.',
  references=['https://www.coe.int/en/web/common-european-framework-reference-languages/reference-level-descriptions',
    'https://www.france-education-international.fr/en/diplome/delf-tout-public/niveau-b2',
    'https://www.france-education-international.fr/diplome/dalf'])

if __name__=='__main__':
 import os,sys
 os.environ['DATABASE_URL']='sqlite://';sys.path.insert(0,str(ROOT/'backend'))
 body=audit();folder=ROOT/'docs/learning'
 (folder/'roadmap-practice-coverage.json').write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 lines=['# A1–C2 roadmap practice update','',body['scope']+'.','',
  '**Staged only:136 lessons,272 scored exercises,68 writing/speaking transfer tasks across68 roadmap topics. No main import.**','',
  'Every topic has a rule/model, original fictional reading, contextual expressions, a listening script and open transfer. All six supported exercise formats occur across the batch.','',
  'The crosswalk below is a thematic reference, not a replacement learning order. Follow the roadmap preparation chain for these future topics. Existing module IDs and stored progress are unchanged. Across release boundaries prerequisites are recommendations; the importer enforces only authored within-release links.','',
  '| Topic | Existing module | New scored / transfer | Reading words / script characters |','|---|---|---:|---:|']
 for t in body['topics']:lines.append(f"| {t['id']} {t['title']} | {t['existing_module_crosswalk']} | 4 / 1 | {t['reading_words']} / {t['script_characters']} |")
 lines.extend(['','## Review limits','',body['reference_notes'],'',
  'These are targeted practice sets, not complete modules with 10–20 independently reviewed new words each. The three expressions are taught in context; no new shared SRS glossary entries are authored. Advanced grammar choices sample supported form control; advanced reading/transfer target scope, attribution and nuance. Neither is evidence of mastery.','',
  'DELF/DALF topics contain original preparatory activities, not copied examination papers or full official-format mock tests. Study hours, lexical breadth, natural listening and spontaneous productive performance are not calibrated by these exercises.','',
  'Main remains181 unpublished lessons/620 scored exercises/50 open task lessons. With the earlier five writing bridges, future staged inventory is141 lessons/272 scored exercises/73 open tasks. A fresh reviewed backup and successful import rehearsal are required before separately authorizing any main import.','',
  'Qualified independent French, pedagogy, pronunciation and productive-task review remain pending.','', '## References',''])
 lines.extend('- '+url for url in body['references'])
 (folder/'ROADMAP-PRACTICE-UPDATE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print('Crosswalk and source audit written for all 68 roadmap topics; no live map or database changed.')
