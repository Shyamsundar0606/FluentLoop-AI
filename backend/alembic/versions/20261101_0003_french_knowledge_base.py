"""Create the French knowledge base and seed CEFR levels.

Revision ID: 20261101_0003
Revises: 20261101_0002
Create Date: 2026-11-01
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

from app.core.database import Base
from app import models  # noqa: F401

revision = "20261101_0003"
down_revision = "20261101_0002"
branch_labels = None
depends_on = None

CURRICULUM_TABLES = (
    "cefr_levels",
    "content_sources",
    "content_import_batches",
    "content_provenance",
    "courses",
    "units",
    "lessons",
    "lesson_sections",
    "learning_objectives",
    "lesson_objectives",
    "lexemes",
    "word_senses",
    "translations",
    "example_sentences",
    "lexeme_examples",
    "media_assets",
    "pronunciations",
    "lesson_vocabulary",
    "grammar_topics",
    "grammar_rules",
    "grammar_examples",
    "lesson_grammar",
    "verb_lemmas",
    "verb_conjugations",
    "phonemes",
    "dialogues",
    "dialogue_turns",
    "lesson_dialogues",
    "exercises",
    "exercise_options",
    "exercise_answers",
)

LEVELS = (
    ("A1", "A1 — Breakthrough", "Beginner French, including learners starting from no prior knowledge.", 1),
    ("A2", "A2 — Waystage", "Elementary French for familiar, everyday situations.", 2),
    ("B1", "B1 — Threshold", "Intermediate French for common topics and independent interaction.", 3),
    ("B2", "B2 — Vantage", "Upper-intermediate French for fluent interaction and detailed discussion.", 4),
    ("C1", "C1 — Effective Operational Proficiency", "Advanced French for flexible, nuanced communication.", 5),
    ("C2", "C2 — Mastery", "Proficient French for precise and nuanced communication.", 6),
)


def upgrade() -> None:
    bind = op.get_bind()
    tables = [Base.metadata.tables[name] for name in CURRICULUM_TABLES]
    Base.metadata.create_all(bind=bind, tables=tables, checkfirst=False)
    op.bulk_insert(
        Base.metadata.tables["cefr_levels"],
        [
            {
                "code": code,
                "display_name": display_name,
                "description": description,
                "rank": rank,
                "created_at": datetime.now(timezone.utc),
            }
            for code, display_name, description, rank in LEVELS
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(CURRICULUM_TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=False)
