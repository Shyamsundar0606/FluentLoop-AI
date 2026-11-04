"""The reviewer audit must report drift without repairing or approving content."""
from sqlalchemy import event, select
from scripts.a1_review_audit import audit
from app.curriculum_models import ExampleSentence, LexemeExample, LessonVocabulary, Lesson, ExerciseOption
from test_curriculum import _import, CONTENT_PATH
from app.content_import import load_content


def test_read_only_audit_detects_missing_links_and_wrong_answer_keys(api_client):
    _, sessions, _ = api_client
    _import(sessions)
    content = load_content(CONTENT_PATH)
    with sessions() as db:
        original = audit(db, CONTENT_PATH)
        assert original["published_lessons"] == 0
        assert original["publication_approved"] is False
        assert original["technical_integrity_passed"], original["lessons"]
        sentence = db.scalar(select(ExampleSentence).where(ExampleSentence.french_text == "J'habite à Lyon."))
        link = db.scalar(select(LexemeExample).where(LexemeExample.example_sentence_id == sentence.id))
        db.delete(link)
        db.flush()
        broken = audit(db, CONTENT_PATH)
        assert not broken["technical_integrity_passed"]
        assert any(i["check"].startswith("explicit example link:") for r in broken["lessons"] for i in r["issues"])
        db.rollback()
        clean = audit(db, CONTENT_PATH)
        assert clean["technical_integrity_passed"], clean["lessons"]
        assert clean["publication_approved"] is False
        option = db.scalar(select(ExerciseOption).where(ExerciseOption.is_correct.is_(True)))
        option.is_correct = False
        db.commit()
        statements = []
        engine = db.get_bind()
        def observe(_conn, _cursor, statement, *_args):
            statements.append(statement.lstrip().split()[0].upper())
        event.listen(engine, 'before_cursor_execute', observe)
        try:
            changed = audit(db, CONTENT_PATH)
        finally:
            event.remove(engine, 'before_cursor_execute', observe)
        assert not changed["technical_integrity_passed"]
        assert any(i["check"].startswith("options:") for r in changed["lessons"] for i in r["issues"])
        assert not set(statements) & {"INSERT", "UPDATE", "DELETE", "ALTER", "DROP"}
        assert changed["published_lessons"] == 0
