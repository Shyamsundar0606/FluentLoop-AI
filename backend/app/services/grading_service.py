from __future__ import annotations

from uuid import UUID

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
