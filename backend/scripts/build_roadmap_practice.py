"""Reproducible future roadmap practice. Writes drafts only; never opens a DB."""
import json
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL

ROOT=Path(__file__).resolve().parents[2]
LEVELS=('A1','A2','B1','B2','C1','C2')
EXPECTED=(12,12,12,12,10,10)
LENGTHS={'A1':'40–60','A2':'80–110','B1':'140–180','B2':'220–280','C1':'350–450','C2':'500–650'}
LICENSE='Original AI-assisted roadmap practice. Independent language, pedagogy, phonetic, answer-key and CEFR review pending.'

def rows():
    import importlib.util
    spec=importlib.util.spec_from_file_location('roadmap_manuscripts',Path(__file__).with_name('roadmap_manuscripts.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.TOPICS

def contrasts():
    import importlib.util
    spec=importlib.util.spec_from_file_location('roadmap_contrasts',Path(__file__).with_name('roadmap_advanced_contrasts.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.CONTRASTS

def choice(key,kind,prompt,options,explanation,seed,data=None):
    # Rotate correct choices; do not train learners to always choose option one.
    offset=seed%len(options);rotated=options[offset:]+options[:offset]
    return dict(key=key,type=kind,prompt=prompt,instructions='Choose the one answer supported by this practice item.',
                explanation=explanation,options=rotated,correct_option=(-offset)%len(options),data=data or {})

def build(level,part,topics):
    from app.assessment_content import AssessmentPack
    tasks=[];previous=None
    for number,row in topics:
        identity=f'{level.lower()}-{number:02d}';seed=number+LEVELS.index(level)
        title,rule,model,translation,wrong,reading,reading_choices,audio,audio_choices,gap,words,transfer=row
        assert gap in model and len(words)==3 and len(audio)<=600
        context=f'French source (fictional teaching situation):\n{reading}\n\nNotice: {rule}\nModel: {model}\nMeaning: {translation}\n\nUseful expressions: '+ '; '.join(fr+' = '+en for fr,en in words)
        advanced=level in ('B2','C1','C2')
        distractors=contrasts()[level][number-1] if advanced else wrong
        exercises=[choice('form-and-meaning','multiple_choice',
          'Which sentence preserves the model’s meaning and scope?' if advanced else 'Which sentence correctly expresses the target form and meaning?',
          [model,*distractors],rule+' Model meaning: '+translation,seed)]
        mode=number%4
        if mode in (0,1):
            exercises.append(dict(key='retrieve-the-form',type='fill_blank' if mode==0 else 'short_answer',
                prompt=model.replace(gap,'___',1),instructions='Supply only the missing model word or phrase. Retain French accents; this is supported form practice, not free translation.',
                explanation=rule+' The model uses « '+gap+' ».',data={'accepted_answers':[gap]}))
        elif mode==2:
            tokens=model.split();ids=[str(uuid5(NAMESPACE_URL,f'fluentloop-roadmap/{identity}/tile/{i}')) for i in range(len(tokens))]
            exercises.append(dict(key='rebuild-the-model',type='sentence_order',prompt='Rebuild the taught model sentence.',
                instructions='Use every tile once in the model order. Other natural French orders are not assessed in this supported task.',
                explanation=rule,data=dict(tiles=[dict(id=i,text=t) for i,t in zip(ids,tokens)],accepted_orders=[ids],correct_sentence=model)))
        else:
            left=[dict(id=str(uuid5(NAMESPACE_URL,f'fluentloop-roadmap/{identity}/fr/{i}')),text=pair[0]) for i,pair in enumerate(words)]
            right=[dict(id=str(uuid5(NAMESPACE_URL,f'fluentloop-roadmap/{identity}/en/{i}')),text=pair[1]) for i,pair in enumerate(words)]
            exercises.append(dict(key='expressions-in-context',type='matching',prompt='Match these contextual expressions to their English meanings.',
                instructions='Use the meaning taught for this situation, not every possible dictionary meaning.',explanation='The expressions are glossed in the lesson context.',
                data=dict(left_items=left,right_items=right,answer_pairs={a['id']:b['id'] for a,b in zip(left,right)})))
        exercises.extend([
            choice('read-the-scope','multiple_choice','Which summary preserves the French source?',reading_choices,
                   'The source supports: '+reading_choices[0]+'. Do not infer an extra promise or reverse its time, speaker or scope.',seed+1),
            choice('hear-the-detail','listening','Listen, then choose the supported detail.',audio_choices,
                   'The script supports: '+audio_choices[0]+'. Transcript for review: '+audio,seed+2,{'text_fr':audio})])
        key=f'topic-{number:02d}-practice'
        tasks.append(dict(key=key,skill='grammar',module_title=title,title=f'{level} roadmap {number:02d}: {title}',
            objective='Use the roadmap topic in a contextual grammar, vocabulary, reading and scripted-listening practice set.',
            context=context,estimated_minutes=25,exercises=exercises,
            grammar=[dict(slug=f'roadmap-{identity}',title=title,summary=rule,rule_code=f'roadmap-{identity}',explanation_english=rule,examples=[(model,translation)])],
            prerequisites=[previous] if previous else []))
        tasks.append(dict(key=f'topic-{number:02d}-transfer',skill='writing',module_title=title,title=f'{level} transfer {number:02d}: {title}',
            objective='Reuse the topic in writing and spoken interaction, then revise after separate qualitative review.',
            context=f'Write approximately {LENGTHS[level]} French words. {transfer}\n\nSpeak: role-play the other participant with the Tutor. Ask a follow-up, repair one misunderstanding and summarise what is agreed or remains uncertain. Use invented personal details.\n\nReview: task fulfilment, grammatical meaning, vocabulary, cohesion, register and source fidelity; for speaking, add intelligibility, turn-taking and repair. AI feedback is advisory. A saved response is not a pass or a pronunciation score. Retrieve again on a later day with changed details. Qualified human review and empirical calibration pending.',
            estimated_minutes=40,exercises=[],prerequisites=[key]))
        previous=f'topic-{number:02d}-transfer'
    return AssessmentPack.model_validate(dict(version=f'0.11.{part}',level=level,status='draft',
        title=f'{level} roadmap practice, part {part}',source_license=LICENSE,tasks=tasks))

def packs():
    for level,total in zip(LEVELS,EXPECTED):
        topics=rows()[level];assert len(topics)==total
        for part,start in enumerate(range(0,total,6),1):
            yield build(level,part,list(enumerate(topics,start=1))[start:start+6])

def write():
    folder=ROOT/'backend/content/roadmap';folder.mkdir(exist_ok=True)
    for pack in packs():
        path=folder/f'{pack.level.lower()}-roadmap-{pack.version}.json'
        body=pack.model_dump_json(indent=2)+'\n'
        if path.exists():assert path.read_text(encoding='utf-8')==body,'Increment the release version before changing an existing draft.'
        else:path.write_text(body,encoding='utf-8')
    print('Staged68 roadmap topics:136 lessons,272 scored exercises,68 writing/speaking transfers. No database opened.')

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    write()
