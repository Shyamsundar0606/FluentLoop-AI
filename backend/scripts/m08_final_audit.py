"""Generate a read-only curriculum report for the configured isolated M08 demo."""
import json
import sys

import m08_local as local
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session


def main():
    extra, _, _ = local.preview_account()
    sys.path.insert(0, str(local.ROOT / "backend"))
    from app.content_audit import CONTENT_PATH, audit
    from app.course_review import digest_packet, packet, provenance, readiness, validate_packet
    from app.curriculum_models import Course, Lesson

    engine = create_engine(extra["DATABASE_URL"])
    with Session(engine) as db:
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        canonical = audit(db, CONTENT_PATH)
        courses = []
        for course in db.scalars(select(Course).where(Course.level_id == "A1").order_by(Course.slug)):
            source = provenance(db, course)
            if source is None:
                courses.append({"course": course.slug, "issues": ["Missing versioned course provenance."]})
                continue
            content = packet(db, course, source)
            digest = digest_packet(content)
            history = source.review_metadata.get("independent_reviews", [])
            courses.append(dict(course=course.slug, version=course.content_version, status=course.status,
                lessons=len(content["lessons"]), exercises=sum(len(lesson["exercises"]) for lesson in content["lessons"]),
                issues=validate_packet(content), **readiness(history, digest, course.content_version)))
        published = db.scalar(select(Lesson.id).where(Lesson.status == "published").limit(1)) is not None
    report = dict(canonical=canonical, courses=courses, has_published_lessons=published)
    (local.PRIVATE / "m08_final_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"canonical_integrity": canonical["technical_integrity_passed"],
                      "courses": courses, "has_published_lessons": published}))
    return int(not canonical["technical_integrity_passed"] or any(course["issues"] for course in courses))


if __name__ == "__main__":
    sys.exit(main())
