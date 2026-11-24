"""Reproducible source audit, not a database import or CEFR accreditation."""
import json,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROFILES={
 'A0':dict(grammar=['Recognise je/tu in memorised chunks','Distinguish a question from a statement','Use un/une as part of a familiar noun phrase'],
  domains=['alphabet and spelling','sound discrimination','greetings and politeness','objects and numbers','classroom repair','typing and recording'],
  reading='Identify a familiar word or instruction with explicit support.',listening='Recognise a very short model with repeats and visual/text support.',writing='Copy accurately, then combine two modelled lines.',speaking='Say an invented name and a memorised polite request; ask for repetition.'),
 'A1':dict(grammar=['Present être/avoir and regular verbs','Common irregular present verbs','Articles, gender and adjective agreement','Questions and negation','Possessives and demonstratives','Quantity and partitives','Place/time prepositions and contractions','Imperative and near future'],
  domains=['identity and family','routine and time','food and money','transport and directions','study and basic work','housing','routine health appointment','simple forms and messages'],
  reading='Extract who, where, when and price from a short practical text.',listening='Follow a slow clear exchange and check one detail.',writing='Write a short intelligible message with day, time and purpose.',speaking='Complete a predictable exchange with support and clarification.'),
 'A2':dict(grammar=['Passé composé with avoir/être','Imparfait for familiar background','Near/simple future','Comparatives and superlatives','Object pronouns, y and en','Relative qui/que/où','Modal requests and basic conditions','Agreement and connected negation'],
  domains=['journeys and disruptions','housing and services','health appointments','social invitations','shopping returns','university arrangements','work schedules','everyday online messages'],
  reading='Understand linked routine messages and a short narrative.',listening='Track key details, changes of plan and a simple explanation.',writing='Explain an event and propose a practical next step.',speaking='Exchange routine information and repair a misunderstanding.'),
 'B1':dict(grammar=['Past narrative sequencing','Plus-que-parfait in a clear sequence','Future and conditional','Si clauses in familiar hypotheses','Subjunctive for common needs','Pronoun reference across sentences','Reported statements and questions','Cause, consequence and concession'],
  domains=['work and study choices','housing problems','travel complaints','news in familiar domains','community activities','health-service explanations','personal and formal correspondence'],
  reading='Follow a connected narrative and distinguish a claim from an assumption.',listening='Identify main points and relevant detail in clear extended speech.',writing='Write a coherent account or reasoned practical request.',speaking='Explain an experience, justify a choice and answer follow-up questions.'),
 'B2':dict(grammar=['Concession and restriction','Subjunctive/indicative stance distinctions','Conditional reporting and hypothesis','Complex relative clauses','Passive and impersonal framing','Cohesive reference and nominalisation','Modal force and register'],
  domains=['public policy','university and professional debates','formal complaints','media evidence','workplace negotiation','culture and social issues'],
  reading='Compare arguments, evidence limitations and implicit assumptions in complex texts.',listening='Follow extended argument and changing positions across speakers.',writing='Develop a structured position with evidence and a substantive counterargument.',speaking='Sustain and qualify an argument, negotiate and respond spontaneously.'),
 'C1':dict(grammar=['Temporal viewpoint in complex reporting','Modal qualification and evidentiality','Subtle concession and causal scope','Dense noun phrases and information structure','Register-sensitive reformulation','Complex cohesion and stylistic variation'],
  domains=['methodological reports','academic synthesis','professional decisions','cultural criticism','institutional negotiation','multi-source mediation'],
  reading='Interpret demanding prose, implicit stance and methodological qualification.',listening='Track implicit attitudes and qualifications in extended multi-speaker input.',writing='Synthesise sources coherently while preserving uncertainty and attribution.',speaking='Reformulate fluently and defend a precise qualified recommendation.'),
 'C2':dict(grammar=['Fine modal commitment and scope','Presupposition and implicature','Marked syntax and rhetorical emphasis','Irony and figurative interpretation','Genre-sensitive rhythm and register','Ambiguity, allusion and precise reformulation'],
  domains=['dense literary and non-literary texts','rhetorical criticism','public/professional mediation','spontaneous challenging debate','contrasting genres and audiences'],
  reading='Interpret subtle stylistic distinctions, allusion and competing plausible readings.',listening='Explain nuanced attitudes, humour and register in demanding varied speech.',writing='Produce precise extended synthesis adapted to audience, including stylistic justification.',speaking='Handle ambiguity and challenge flexibly without losing precision or nuance.'),
}

def audit():
    from sys import path
    path.insert(0,str(ROOT/'backend'))
    from app.assessment_content import load_assessment_pack,pack_digest
    plan=json.loads((ROOT/'backend/content/learning-path.json').read_text(encoding='utf-8'))
    sources={};hashes={}
    registry_file=ROOT/'backend/content/imported-personal-releases.json'
    registry={r['batch_key']:r['source_sha256'] for r in json.loads(registry_file.read_text(encoding='utf-8'))['releases']} if registry_file.exists() else {}
    base=ROOT/'backend/content/a1/course.json'
    for row in json.loads(base.read_text(encoding='utf-8'))['course']['lessons']:
        sources[row['slug']]=dict(state='main',context=row['introduction'],exercises=row['exercises'],skill='mixed',grammar=len(row['grammar']),vocabulary=len(row['vocabulary']))
    for folder in ('personal','foundations','scenarios','depth','completion','writing-bridges','roadmap'):
        for file in sorted((ROOT/'backend/content'/folder).glob('*.json')):
            pack=load_assessment_pack(file);hashes[str(file.relative_to(ROOT))]=hashlib.sha256(file.read_bytes()).hexdigest()
            identity=f'm10-assessments-{pack.level.lower()}-{pack.version}'
            imported=identity in registry if registry else folder in ('personal','foundations')
            if identity in registry:assert pack_digest(pack)==registry[identity],'Imported source changed; increment the release instead.'
            for task in pack.tasks:
                slug=f'm10-assessments-{pack.level.lower()}-{pack.version}-{task.key}'
                sources[slug]=dict(state='main' if imported else 'staged',context=task.context,
                    exercises=[e.model_dump() for e in task.exercises],skill=task.skill,grammar=len(task.grammar),vocabulary=len(task.vocabulary))
    stages=[]
    for stage in plan['stages']:
        modules=[]
        for module in stage['modules']:
            records=[sources[s] for s in module['lesson_slugs'] if s in sources]
            unknown=[s for s in module['lesson_slugs'] if s not in sources]
            assert not unknown,unknown
            scripts=[e.get('data',{}).get('text_fr','') for r in records for e in r['exercises'] if e.get('type')=='listening']
            gaps=[]
            if not records:gaps.append('No authored lesson input or productive task yet')
            if not any(r['grammar'] for r in records):gaps.append('No structured grammar rule linked; prose notes may still exist')
            if not any(r['skill']=='writing' for r in records):gaps.append('No dedicated open writing task')
            if not scripts:gaps.append('No scripted listening exercise')
            gaps.extend(['Independent productive-skill rating and unseen transfer evidence pending',
                'Varied-speaker and spontaneous listening not established by synthetic scripts',
                'Diagnostic/module/level-end empirical calibration pending'])
            modules.append(dict(id=module['id'],title=module['title'],objective=module['objective'],prerequisites=module['prerequisites'],
                main_lessons=sum(r['state']=='main' for r in records),staged_lessons=sum(r['state']=='staged' for r in records),
                structured_grammar_rules=sum(r['grammar'] for r in records),linked_vocabulary=sum(r['vocabulary'] for r in records),
                dedicated_writing_tasks=sum(r['skill']=='writing' for r in records),scripted_listening_items=len(scripts),
                longest_script_words=max([len(s.split()) for s in scripts] or [0]),
                longest_context_words=max([len(r['context'].split()) for r in records] or [0]),
                gaps=gaps,competency_demonstrated=False,qualified_human_review='pending'))
        stages.append(dict(stage=stage['code'],blueprint=PROFILES[stage['code']],modules=modules,
            full_coverage=False,cefr_calibration='not applicable' if stage['code']=='A0' else 'pending'))
    return dict(version='2.0.0',scope='Project competency blueprint and source inventory, not an exhaustive official CEFR descriptor inventory',
        references=['https://www.coe.int/en/web/common-european-framework-reference-languages/cefr-companion-volume-and-its-language-versions',
                    'https://www.coe.int/en/web/common-european-framework-reference-languages/tests-and-examinations'],
        status_method='Main release identities and digests from verified import registry; source counts do not imply competency approval',
        source_sha256=hashes,stages=stages,certification=False)

if __name__=='__main__':
    body=audit();dest=ROOT/'docs/learning/competency-audit.json'
    dest.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# A0–C2 competency and source audit','',body['scope']+'.','',
        'Every listed gap remains open. Input length is an inventory metric, not a difficulty or CEFR validation.','']
    for stage in body['stages']:
        lines.extend(['## '+stage['stage'],'','Grammar sequence: '+' → '.join(stage['blueprint']['grammar'])+'.','',
                      'Contexts: '+', '.join(stage['blueprint']['domains'])+'.',''])
        for skill in ('reading','listening','writing','speaking'):lines.append('- '+skill.title()+': '+stage['blueprint'][skill])
        lines.extend(['','| Module | Main / staged | Writing / listening | Outstanding evidence |','|---|---:|---:|---|'])
        for m in stage['modules']:
            lines.append(f"| {m['id']} {m['title']} | {m['main_lessons']} / {m['staged_lessons']} | {m['dedicated_writing_tasks']} / {m['scripted_listening_items']} | {'; '.join(m['gaps'])} |")
        lines.append('')
    (ROOT/'docs/learning/COMPETENCY-AUDIT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Audited all seven stages and every mapped module; no competency certified and no database modified.')
