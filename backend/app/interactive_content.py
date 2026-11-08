"""Explicit, draft-only M08 module import into the existing curriculum tables."""
import argparse
import hashlib
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select,delete
from app.core.database import SessionLocal
from app.content_import import _upsert, _provenance, COUNTER
from app.curriculum_models import (ContentSource,ImportBatch,Course,Unit,Lesson,LearningObjective,
    LessonObjective,LessonSection,LessonGrammar,GrammarTopic,GrammarRule,GrammarExample,
    LessonVocabulary,Exercise,ExerciseOption)
from app.services.exercise_formats import definition

CONTENT_PATH=Path(__file__).resolve().parents[1]/'content/practice/etre-interactive.json'


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


class ExerciseInput(Strict):
    key: str=Field(pattern=r'^[a-z][a-z0-9-]{2,60}$')
    type: Literal['multiple_choice','fill_blank','sentence_order','matching','listening','short_answer']
    prompt: str=Field(min_length=4,max_length=1000)
    instructions: str=Field(min_length=4,max_length=1000)
    explanation: str=Field(min_length=4,max_length=1000)
    options: list[str]=Field(default_factory=list,max_length=6)
    correct_option: int | None=None
    data: dict=Field(default_factory=dict)

    @model_validator(mode='after')
    def key_integrity(self):
        definition(self.type,self.data)
        if self.type in ('multiple_choice','listening'):
            if len(self.options)<2 or len(set(self.options))!=len(self.options) or self.correct_option is None or not 0<=self.correct_option<len(self.options):
                raise ValueError('Choice exercises need one in-range answer and unique options')
        elif self.options or self.correct_option is not None:
            raise ValueError('Non-choice formats cannot contain choice answer keys')
        return self


class Mistake(Strict):
    incorrect: str=Field(min_length=1,max_length=150)
    correct: str=Field(min_length=1,max_length=150)
    explanation: str=Field(min_length=8,max_length=500)


class InteractivePack(Strict):
    development_fixture: Literal[True] = True
    key: Literal['m08-etre-interactive']
    version: str=Field(pattern=r'^\d+\.\d+\.\d+$')
    status: Literal['draft']
    level: Literal['A1']
    title: str=Field(min_length=5,max_length=160)
    introduction: str=Field(min_length=30,max_length=2000)
    explanation: str=Field(min_length=30,max_length=2000)
    when_to_use: str=Field(min_length=10,max_length=1000)
    recap: str=Field(min_length=15,max_length=1000)
    common_mistakes: list[Mistake]=Field(min_length=1,max_length=5)
    examples: list[tuple[str,str]]=Field(min_length=2,max_length=3)
    grammar_slug: str
    objective_code: str
    source_license: str=Field(min_length=8,max_length=160)
    attribution: str=Field(min_length=8,max_length=1000)
    exercises: list[ExerciseInput]=Field(min_length=6,max_length=6)

    @model_validator(mode='after')
    def complete_formats(self):
        if len({e.key for e in self.exercises})!=6 or {e.type for e in self.exercises}!={'multiple_choice','fill_blank','sentence_order','matching','listening','short_answer'}:
            raise ValueError('This small draft must demonstrate each of the six formats once')
        return self


def load_pack(path=CONTENT_PATH):
    return InteractivePack.model_validate_json(path.read_text(encoding='utf-8'))


def import_pack(db,pack):
    """Never touches a published topic or creates a human approval."""
    topic=db.scalar(select(GrammarTopic).where(GrammarTopic.slug==pack.grammar_slug))
    objective=db.scalar(select(LearningObjective).where(LearningObjective.code==pack.objective_code))
    if topic is None or objective is None or topic.cefr_level!=pack.level or objective.level!=pack.level:
        raise ValueError('Import the existing A1 curriculum first; grammar/objective references must match A1.')
    published=db.scalar(select(Lesson).join(LessonGrammar).join(Unit).join(Course).where(
        LessonGrammar.grammar_topic_id==topic.id,Lesson.status=='published',Unit.status=='published',Course.status=='published'))
    if published or topic.publication_status=='published':
        raise ValueError('Draft enrichment cannot replace an already published grammar topic.')
    digest=hashlib.sha256(pack.model_dump_json().encode()).hexdigest()
    batch=db.scalar(select(ImportBatch).where(ImportBatch.batch_key==f'{pack.key}-{pack.version}'))
    if batch and batch.report.get('_source_sha256')!=digest:raise ValueError('Increment the module version before changing source content.')
    COUNTER.clear()
    source=_upsert(db,ContentSource,{'source_name':'FluentLoop M08 interactive draft'},dict(source_type='ai_assisted_draft',
        source_url=None,source_license=pack.source_license,attribution_requirements=pack.attribution))
    if batch is None:
        batch=ImportBatch(source_id=source.id,batch_key=f'{pack.key}-{pack.version}',content_version=pack.version,status='running',report={})
        db.add(batch);db.flush();COUNTER['inserted']+=1
    course=_upsert(db,Course,{'slug':pack.key},dict(level_id=pack.level,title='Interactive foundations — draft practice',
        description=pack.introduction,explanation_language='en',estimated_minutes=12,status='draft',content_version=pack.version),reopen_for_review=True)
    unit=_upsert(db,Unit,{'course_id':course.id,'slug':pack.key+'-unit'},dict(title='Understand → Practice → Speak → Remember',
        description=pack.introduction,sequence_order=1,status='draft'),reopen_for_review=True)
    lesson=_upsert(db,Lesson,{'unit_id':unit.id,'slug':pack.key+'-lesson'},dict(title=pack.title,description=pack.introduction,
        estimated_minutes=12,sequence_order=1,difficulty_level=pack.level,explanation_language='en',content_version=pack.version,status='draft'),reopen_for_review=True)
    _upsert(db,LessonObjective,{'lesson_id':lesson.id,'objective_id':objective.id},{})
    _upsert(db,LessonGrammar,{'lesson_id':lesson.id,'grammar_topic_id':topic.id},{})
    # Use existing vocabulary records; do not invent lexical identities or alter
    # enrolled review cards merely because another lesson reuses these words.
    vocabulary=db.scalars(select(LessonVocabulary).join(Lesson).where(Lesson.slug=='a1-006').order_by(LessonVocabulary.sequence_order)).all()
    for word in vocabulary:_upsert(db,LessonVocabulary,{'lesson_id':lesson.id,'lexeme_id':word.lexeme_id},
        {'sequence_order':word.sequence_order,'teaching_note':word.teaching_note})
    metadata=dict(version=pack.version,when_to_use=pack.when_to_use,common_mistakes=[m.model_dump() for m in pack.common_mistakes],
        recap=pack.recap,source_license=pack.source_license,attribution=pack.attribution,rule_code=pack.key,
        independent_human_review=False)
    metadata['development_fixture']=pack.development_fixture
    if not topic.teaching_metadata.get('curriculum_supplement'):
        _upsert(db,GrammarTopic,{'id':topic.id},{'publication_status':'draft','teaching_metadata':metadata})
    rule=_upsert(db,GrammarRule,{'topic_id':topic.id,'rule_code':pack.key},dict(explanation_english=pack.explanation,
        explanation_french=None,exceptions='\n'.join(m.explanation for m in pack.common_mistakes)))
    for fr,en in pack.examples:_upsert(db,GrammarExample,{'rule_id':rule.id,'french_sentence':fr,'english_translation':en},{'explanation':None})
    for order,(kind,body) in enumerate([('introduction',pack.introduction),('grammar',pack.explanation),
            ('explanation','\n'.join(f'{fr}\n{en}' for fr,en in pack.examples)),('recap',pack.recap)],1):
        _upsert(db,LessonSection,{'lesson_id':lesson.id,'sequence_order':order},
            dict(section_type=kind,title={'introduction':'Understand','grammar':'Explanation','explanation':'French examples','recap':'Remember'}[kind],body_content=body,content_metadata={}))
    for order,item in enumerate(pack.exercises,1):
        exercise=_upsert(db,Exercise,{'lesson_id':lesson.id,'sequence_order':order},dict(exercise_type=item.type,prompt=item.prompt,
            instructions=item.instructions,explanation=item.explanation,level=pack.level,exercise_data=definition(item.type,item.data),
            learning_objective_id=objective.id,grammar_topic_id=topic.id))
        stale=db.execute(delete(ExerciseOption).where(ExerciseOption.exercise_id==exercise.id,
            ExerciseOption.sequence_order>len(item.options)))
        COUNTER['deleted']+=stale.rowcount
        for n,label in enumerate(item.options,1):_upsert(db,ExerciseOption,{'exercise_id':exercise.id,'sequence_order':n},
            {'option_text':label,'is_correct':n-1==item.correct_option})
        _provenance(db,source,batch,'exercise',f'{pack.key}:{item.key}',pack.version)
    for kind,key in [('course',course.slug),('lesson',lesson.slug),('grammar_topic',topic.slug)]:
        _provenance(db,source,batch,kind,key,pack.version)
    report={k:COUNTER[k] for k in ('inserted','updated','unchanged','deleted')}
    report.update(_source_sha256=digest,review_status='pending',published_lessons=0,rejected=0)
    batch.status='completed';batch.report=report;db.flush()
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--content',type=Path,default=CONTENT_PATH)
    args=parser.parse_args();pack=load_pack(args.content)
    if args.apply:
        with SessionLocal.begin() as db:result=import_pack(db,pack)
    else:result={'formats':6,'status':'draft','review_status':'pending'}
    print(json.dumps(result))


if __name__=='__main__':main()
