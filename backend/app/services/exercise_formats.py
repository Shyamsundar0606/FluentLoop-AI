"""Trusted exercise definitions and an explicit answer-free projection.

Definition metadata and saved answer keys are private server data. Public items
are copied individually; never serialize an exercise_data/snapshot dictionary.
"""
import random
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from fastapi import HTTPException


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Item(Strict):
    id: UUID
    text: str = Field(min_length=1,max_length=100)


class TextDefinition(Strict):
    accepted_answers: list[str] = Field(min_length=1,max_length=12)
    assessment_mode: str = 'deterministic'

    @model_validator(mode='after')
    def valid_answers(self):
        if self.assessment_mode != 'deterministic' or any(not value.strip() or len(value)>1000 for value in self.accepted_answers):
            raise ValueError('Automatic grading requires bounded, explicitly authored deterministic answers')
        return self


class OrderDefinition(Strict):
    tiles: list[Item] = Field(min_length=2,max_length=30)
    accepted_orders: list[list[UUID]] = Field(min_length=1,max_length=8)
    correct_sentence: str = Field(min_length=1,max_length=1000)

    @model_validator(mode='after')
    def permutations(self):
        identifiers=[item.id for item in self.tiles]
        if len(identifiers)!=len(set(identifiers)) or any(
                len(order)!=len(identifiers) or set(order)!=set(identifiers) for order in self.accepted_orders):
            raise ValueError('Each authored order must use all unique tile identifiers exactly once')
        return self


class MatchingDefinition(Strict):
    left_items: list[Item] = Field(min_length=2,max_length=12)
    right_items: list[Item] = Field(min_length=2,max_length=12)
    answer_pairs: dict[UUID,UUID]

    @model_validator(mode='after')
    def bijection(self):
        left=[item.id for item in self.left_items];right=[item.id for item in self.right_items]
        if (len(left)!=len(right) or len(set(left+right))!=len(left+right)
                or set(self.answer_pairs)!=set(left) or set(self.answer_pairs.values())!=set(right)):
            raise ValueError('Matching definitions require unique identifiers and a complete one-to-one mapping')
        return self


class ListeningDefinition(Strict):
    text_fr: str = Field(min_length=1,max_length=300)


def definition(kind,data):
    model={'fill_blank':TextDefinition,'short_answer':TextDefinition,'translation':TextDefinition,
           'sentence_order':OrderDefinition,'matching':MatchingDefinition,'listening':ListeningDefinition}.get(kind)
    if kind=='multiple_choice':
        if data:raise ValueError('Multiple choice uses its existing option answer key')
        return {}
    if not model:raise ValueError('Unsupported exercise type')
    return model.model_validate(data).model_dump(mode='json')


def snapshot(exercise,options):
    try:data=definition(exercise.exercise_type,exercise.exercise_data or {})
    except (ValueError,ValidationError):
        raise HTTPException(409,'This activity needs reviewed deterministic answers before it can be graded.') from None
    result=dict(type=exercise.exercise_type,prompt=exercise.prompt,instructions=exercise.instructions,
        explanation=exercise.explanation,level=exercise.level,sequence_order=exercise.sequence_order,
        options=[],format_version=2,
        learning_objective_id=str(exercise.learning_objective_id) if exercise.learning_objective_id else None,
        grammar_topic_id=str(exercise.grammar_topic_id) if exercise.grammar_topic_id else None)
    if exercise.exercise_type in ('multiple_choice','listening'):
        correct=[o for o in options if o.is_correct]
        if len(options)<2 or len(correct)!=1:
            raise HTTPException(409,'This activity has no unambiguous saved answer key.')
        result.update(options=[dict(id=str(o.id),text=o.option_text,sequence_order=o.sequence_order) for o in options],
                      correct_option_id=str(correct[0].id))
    result.update(data)
    # Shuffle the two sides independently and freeze them for stable resume.
    for key in ('tiles','left_items','right_items'):
        if key in result:random.SystemRandom().shuffle(result[key])
    return result


def public_fields(saved):
    return {key:[{'id':item['id'],'text':item['text']} for item in saved.get(key,[])]
            for key in ('tiles','left_items','right_items')}
