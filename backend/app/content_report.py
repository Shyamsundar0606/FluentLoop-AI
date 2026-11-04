from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.curriculum_models import (
    Course,
    Exercise,
    ImportBatch,
    Lesson,
    Lexeme,
    Unit,
)


def build_report(db: Session) -> dict[str, object]:
    return {
        "courses": db.scalar(select(func.count(Course.id))) or 0,
        "units": db.scalar(select(func.count(Unit.id))) or 0,
        "lessons": db.scalar(select(func.count(Lesson.id))) or 0,
        "draft_lessons": db.scalar(select(func.count(Lesson.id)).where(Lesson.status == "draft")) or 0,
        "published_lessons": db.scalar(select(func.count(Lesson.id)).where(Lesson.status == "published")) or 0,
        "lexemes": db.scalar(select(func.count(Lexeme.id))) or 0,
        "exercises": db.scalar(select(func.count(Exercise.id))) or 0,
        "import_batches": [
            {
                "batch_key": batch.batch_key,
                "content_version": batch.content_version,
                "status": batch.status,
                "report": batch.report,
            }
            for batch in db.scalars(
                select(ImportBatch).order_by(ImportBatch.created_at.desc())
            ).all()
        ],
    }


def main() -> None:
    with SessionLocal() as db:
        report = build_report(db)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
