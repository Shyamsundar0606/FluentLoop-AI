from __future__ import annotations

from uuid import UUID
import json
import re
import unicodedata

from fastapi import HTTPException, status


def grade_multiple_choice(
    snapshot: dict,
    selected_option_id: UUID,
) -> tuple[bool, str, str]:
    options = snapshot.get("options", [])
    selected = next(
        (option for option in options if option.get("id") == str(selected_option_id)),
        None,
    )
    if selected is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose an answer option from this exercise.",
        )
    correct_option_id = snapshot.get("correct_option_id")
    correct_option = next(
        (option for option in options if option.get("id") == correct_option_id),
        None,
    )
    if correct_option is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This exercise has no valid saved answer key.",
        )
    is_correct = selected["id"] == correct_option_id
    explanation = snapshot.get("explanation", "")
    return is_correct, correct_option["text"], explanation


def normalize_written(value: str) -> str:
    # No accent stripping, fuzzy spelling or semantic/LLM grading.
    value=unicodedata.normalize('NFC',value).casefold().replace('’',"'")
    value=re.sub(r"\s*'\s*","'",value)
    return re.sub(r'\s+',' ',value).strip().rstrip('.!?').rstrip()


def grade_saved(snapshot: dict, answer: dict) -> tuple[bool,str,str,str]:
    kind=snapshot['type']
    required={'multiple_choice':'selected_option_id','listening':'selected_option_id','fill_blank':'text_answer',
        'short_answer':'text_answer','translation':'text_answer','sentence_order':'tile_ids','matching':'matches'}.get(kind)
    if required is None or set(answer)!={required}:
        raise HTTPException(422,'Submit the answer format required by this exercise.')
    explanation=snapshot.get('explanation','')
    value=answer[required]
    if kind in ('multiple_choice','listening'):
        correct,display,explanation=grade_multiple_choice(snapshot,UUID(str(value)))
        selected=next(o['text'] for o in snapshot['options'] if o['id']==str(value))
        return correct,display,explanation,selected.strip().casefold()
    if kind in ('fill_blank','short_answer','translation'):
        if not isinstance(value,str) or not value.strip() or len(value)>1000:
            raise HTTPException(422,'Enter a short written answer.')
        accepted=snapshot.get('accepted_answers',[])
        if not accepted:raise HTTPException(409,'Reviewed answers are unavailable.')
        normalized=normalize_written(value)
        return normalized in {normalize_written(v) for v in accepted},accepted[0],explanation,normalized
    if kind=='sentence_order':
        expected={item['id'] for item in snapshot['tiles']}
        if not isinstance(value,list) or len(value)!=len(expected) or set(value)!=expected:
            raise HTTPException(422,'Use every word tile exactly once.')
        correct=value in snapshot['accepted_orders']
        return correct,snapshot['correct_sentence'],explanation,json.dumps(value,separators=(',',':'))
    left={item['id'] for item in snapshot['left_items']};right={item['id'] for item in snapshot['right_items']}
    if not isinstance(value,dict) or set(value)!=left or set(value.values())!=right or len(value)!=len(right):
        raise HTTPException(422,'Match every left item to a different right item.')
    words={item['id']:item['text'] for item in snapshot['left_items']+snapshot['right_items']}
    display='; '.join(f"{words[l]} → {words[r]}" for l,r in snapshot['answer_pairs'].items())
    return value==snapshot['answer_pairs'],display,explanation,json.dumps(value,sort_keys=True,separators=(',',':'))
