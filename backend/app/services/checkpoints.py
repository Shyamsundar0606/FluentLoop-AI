"""Read-only formative module/level plans built from permitted existing activities.

Components persist through the existing owned engines. No cross-lesson snapshot
permissions or certified aggregate score is introduced.
"""
from app.services.learning_path import path_for
from app.services.assessment_service import catalog

RUBRICS={
 'A0':dict(writing=['Copy the supported model accurately, retaining accents.','Combine a greeting and one clear message.'],
           speaking=['Make the short supported message intelligible.','Request a slow repeat when needed.']),
 'A1':dict(writing=['Fulfil the short practical purpose with consistent details.','Use familiar verb forms, articles and spelling intelligibly.'],
           speaking=['Complete the predictable exchange.','Check a name, number, time or place and repair a misunderstanding.']),
 'A2':dict(writing=['Connect routine information and a simple event sequence.','Keep times, references and basic grammatical forms consistent.'],
           speaking=['Exchange practical information and explain a change.','Ask and answer a clarification rather than silently guessing.']),
 'B1':dict(writing=['Organise a connected account or reasoned request.','Attribute assumptions and distinguish them from confirmed facts.'],
           speaking=['Explain an experience and justify a choice.','Answer a follow-up and reformulate unclear references.']),
 'B2':dict(writing=['Develop a supported position with a substantive counterargument.','Control cohesion, conditional scope and an appropriate register.'],
           speaking=['Sustain an argument and negotiate a qualified option.','Respond to challenge without replacing uncertain evidence with certainty.']),
 'C1':dict(writing=['Integrate sources and methodological qualifications faithfully.','Design a precise structured text for the specified audience.'],
           speaking=['Mediate changing positions fluently and qualify commitments.','Use reformulation and prosody to support an intelligible distinction.']),
 'C2':dict(writing=['Delimit competing interpretations, presupposition and inference.','Preserve fine pragmatic nuance while changing genre or register.'],
           speaking=['Handle ambiguity and unpredictable challenge flexibly.','Reformulate precisely without flattening stance, humour or uncertainty.']),
}

def plans(db,user,stage=None):
    path=path_for(db,user);selected=[s for s in path['stages'] if stage is None or s['code']==stage]
    catalogs={level:catalog(db,user,level)['items'] for level in {('A1' if s['code']=='A0' else s['code']) for s in selected}}
    def make_plan(identity,title,code,lessons,prerequisites,kind):
        permitted={lesson['id'] for lesson in lessons}
        items=[item for item in catalogs['A1' if code=='A0' else code] if item['lesson_id'] in permitted]
        # A level check samples categories; it is not claimed to assess every
        # descriptor, and it never combines foreign lesson snapshots in one engine.
        if kind=='level_end':
            latest={}
            for item in items:latest[item['skill']]=item
            items=list(latest.values())
        objective=[item for item in items if item['skill']!='writing']
        writing=[item for item in items if item['skill']=='writing']
        speaking=next((lesson for lesson in lessons if lesson['kind']!='writing'),lessons[0] if lessons else None)
        return dict(id=identity,title=title,stage=code,kind=kind,prerequisites=prerequisites,
            objective_checks=objective,writing_tasks=writing,
            speaking_lesson=dict(id=speaking['id'],title=speaking['title'],href=f"/learn/{speaking['id']}") if speaking else None,
            available=bool(items or speaking),rubrics=RUBRICS[code],
            qualitative_rating_labels=['Needs support','Developing for this task','Consistent for this task'],
            unassessed_skills=['writing','speaking'],overall_score=None,certification=False,
            review='Attempt a new example without the model, review saved mistakes, then retrieve again on a later day.',
            persistence='Component results are saved in your existing assessment, writing and speech histories; no certified aggregate score is calculated.')
    result=[]
    for item in selected:
        all_lessons=[]
        for learning_module in item['modules']:
            lessons=learning_module['lessons'];all_lessons.extend(lessons)
            result.append(make_plan(learning_module['id'],learning_module['title'],item['code'],lessons,learning_module['prerequisites'],'module'))
        result.append(make_plan(item['code'].lower()+'-level-end',item['code']+' level-end practice review',item['code'],all_lessons,[],'level_end'))
    return dict(plans=result,saved_level=path['saved_level'],certification=False,
        notice='Formative component checks reuse practised material. These are not unseen or empirically calibrated proficiency exams. Writing/speaking require qualitative review.')
