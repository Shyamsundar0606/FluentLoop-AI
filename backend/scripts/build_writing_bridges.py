"""Future draft writing/voice bridges for five audited beginner gaps. No import."""
from pathlib import Path

ROWS=[
 ('a0-01','letters-and-name-writing','Write and say an invented name',
  'Copy Bonjour. Then write Je m’appelle followed by an invented first name. Write its letters separately. Keep any accent in the name. Supported example: Bonjour. Je m’appelle Léa. L – É – A. The example is a model, not the only acceptable name. Say the greeting and name, then ask the Tutor to repeat slowly. Human listening is needed to judge letter pronunciation.',
  'Check the greeting, name phrase and letter sequence; copy first, then retrieve tomorrow without looking.'),
 ('a1-01','greet-introduce-close','Open and close a classroom exchange',
  'Write a short two-person exchange for a first French class. Greet politely, introduce an invented name, acknowledge the introduction and close when the class finishes. Model: « Bonjour, je m’appelle Amine. — Bonjour Amine, moi, c’est Léa. — Au revoir et bonne journée ! — Au revoir ! » Change the names, then practise both roles with the Tutor. Do not use real contact details.',
  'Check who speaks, a suitable greeting/closing and familiar versus polite address. Read the exchange aloud; transcription is not a pronunciation score.'),
 ('a1-03','first-sentences-writing','Build clear first sentences',
  'Write four short French sentences about an imaginary student: identify them, locate them, say one thing they are not and ask a question. Model: « Je suis étudiante. Je suis à Lyon. Je ne suis pas professeure. Et toi, tu es étudiant ? » Masculine and feminine forms can vary with the invented person; do not treat the model as a unique answer. Ask the Tutor to answer the question.',
  'Check the subject and être form, ne… pas around the verb, an intelligible question and accents. Retrieve two sentences on a later day.'),
 ('a1-04','people-and-possessions-writing','Describe people and their possessions',
  'Write 35–50 French words describing two invented people and one possession each. Use avoir and familiar colour adjectives. Model: « Mon frère a un sac bleu. Ma sœur a une veste rouge. Le sac est petit. La veste est grande. Le sac n’est pas rouge. » This is a supported example; other coherent details are acceptable. Describe one item aloud and ask the Tutor which person owns it.',
  'Check mon/ma with the possessed noun, avoir forms, adjective agreement and a clear owner for each object. Review by describing a different possession tomorrow.'),
 ('a1-05','routine-writing-and-repair','Describe a routine and clarify a time',
  'Write 40–60 French words about an invented weekday. Include three activities and two times. Model: « Je me lève à sept heures. Je prends le bus à huit heures. Je travaille le matin et je déjeune à midi. Le soir, je lis un peu, puis je prépare mon sac pour le lendemain. » Use familiar model chunks; do not assume all these verbs follow one rule. Ask the Tutor to mishear one time, then correct it politely.',
  'Check present forms, chronological order, the two times and the repair phrase. Repeat without the original text on a later day; AI suggestions remain advisory.'),
]

def packs():
 from app.assessment_content import AssessmentPack
 output=[]
 for stage,version in (('A0','0.9.0'),('A1','0.9.1')):
  tasks=[];previous=None
  for identity,key,title,prompt,review in ROWS:
   if identity.split('-')[0].upper()!=stage:continue
   tasks.append(dict(key=key,skill='writing',title=title,module_title='Beginner writing and speaking bridges',
    objective='Combine the module language in a short supported written exchange and a spoken repair task.',
    context=prompt+'\n\nReview criteria: '+review+'\n\nNo objective correctness, independent human approval or CEFR score is claimed.',
    estimated_minutes=20,exercises=[],prerequisites=[previous] if previous else []));previous=key
  body=dict(version=version,level='A1',status='draft',title=stage+' future writing and speaking bridges',
    source_license='Original AI-assisted beginner drafts; independent language, pedagogy and phonetic review pending.',tasks=tasks)
  if stage=='A0':body['learning_stage']='A0'
  output.append(AssessmentPack.model_validate(body))
 return output

if __name__=='__main__':
 import sys
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
 folder=Path(__file__).resolve().parents[1]/'content/writing-bridges';folder.mkdir(exist_ok=True)
 for pack in packs():
  file=folder/f"{(pack.learning_stage or pack.level).lower()}-writing-{pack.version}.json"
  body=pack.model_dump_json(indent=2)+'\n'
  if file.exists():assert file.read_text(encoding='utf-8')==body,'Increment a tested release version before edits.'
  else:file.write_text(body,encoding='utf-8')
 print('Staged five future writing/speaking bridge lessons; zero scored exercises; no database access.')
