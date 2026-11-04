"""Add isolated AI tutor memory; existing curriculum and learning data are untouched."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261102_0005"
down_revision = "20261102_0004"
branch_labels = None
depends_on = None
JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def identity():
    return sa.Column("id", sa.Uuid(), primary_key=True)


def fk(name, target, nullable=False, delete="CASCADE"):
    return sa.Column(
        name, sa.Uuid(), sa.ForeignKey(target, ondelete=delete), nullable=nullable
    )


def stamp(name):
    return sa.Column(
        name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def text(name, size=None, nullable=False):
    return sa.Column(name, sa.String(size) if size else sa.Text(), nullable=nullable)


def upgrade():
    op.create_table(
        "ai_conversations",
        identity(),
        fk("user_id", "users.id"),
        text("title", 120),
        text("mode", 16),
        text("cefr_level", 2),
        text("scenario_id", 80, True),
        fk("linked_lesson_id", "lessons.id", True, "RESTRICT"),
        text("status", 16),
        stamp("created_at"),
        stamp("updated_at"),
        sa.Column("last_message_at", sa.DateTime(timezone=True)),
        text("model_provider", 32),
        text("model_name", 120),
        sa.Column("preview_mode", sa.Boolean(), nullable=False),
        text("content_version_reference", 32, True),
        sa.Column("active_request_id", sa.Uuid()),
        sa.Column("generation_started_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "cefr_level IN ('A1','A2','B1','B2','C1','C2')", name="ck_ai_level"
        ),
        sa.CheckConstraint(
            "mode IN ('tutor','vocabulary','grammar','correction','roleplay')",
            name="ck_ai_mode",
        ),
        sa.CheckConstraint("status IN ('active','archived')", name="ck_ai_status"),
    )
    op.create_index(
        "ix_ai_owner_updated", "ai_conversations", ["user_id", "updated_at"]
    )
    op.create_table(
        "ai_messages",
        identity(),
        fk("conversation_id", "ai_conversations.id"),
        text("role", 16),
        text("content"),
        stamp("created_at"),
        text("model_name", 120, True),
        text("response_status", 16),
        text("grounding_status", 32),
        sa.Column("model_metadata", JSON, nullable=False),
        sa.Column("request_id", sa.Uuid()),
        sa.CheckConstraint("role IN ('user','assistant')", name="ck_ai_message_role"),
        sa.CheckConstraint(
            "response_status IN ('pending','success','failed')",
            name="ck_ai_message_status",
        ),
        sa.CheckConstraint(
            "grounding_status IN ('general_knowledge','curriculum_context','draft_preview','unverified')",
            name="ck_ai_grounding",
        ),
        sa.UniqueConstraint(
            "conversation_id", "request_id", "role", name="uq_ai_turn_request_role"
        ),
    )
    op.create_index(
        "ix_ai_messages_conversation_created",
        "ai_messages",
        ["conversation_id", "created_at"],
    )
    op.create_table(
        "ai_message_sources",
        identity(),
        fk("message_id", "ai_messages.id"),
        text("source_type", 24),
        fk("source_record_id", "lessons.id", False, "RESTRICT"),
        text("content_version", 32),
        sa.Column("retrieval_score", sa.Integer()),
        stamp("created_at"),
        sa.UniqueConstraint(
            "message_id", "source_record_id", name="uq_ai_message_source"
        ),
    )
    op.create_index(
        "ix_ai_message_sources_message_id", "ai_message_sources", ["message_id"]
    )
    op.create_table(
        "ai_practice_feedback",
        identity(),
        fk("conversation_id", "ai_conversations.id"),
        fk("message_id", "ai_messages.id"),
        fk("user_id", "users.id"),
        text("cefr_level", 2),
        text("topic", 120),
        text("feedback_type", 32),
        text("corrected_text"),
        text("explanation"),
        fk("suggested_lesson_id", "lessons.id", True, "RESTRICT"),
        stamp("created_at"),
        sa.UniqueConstraint("message_id", name="uq_ai_feedback_message"),
    )
    op.create_index(
        "ix_ai_practice_feedback_conversation_id",
        "ai_practice_feedback",
        ["conversation_id"],
    )
    op.create_index(
        "ix_ai_practice_feedback_user_id", "ai_practice_feedback", ["user_id"]
    )
    op.create_table(
        "ai_learning_recommendations",
        identity(),
        fk("user_id", "users.id"),
        text("cefr_level", 2),
        text("recommendation_type", 32),
        text("topic", 120),
        text("reason"),
        fk("linked_lesson_id", "lessons.id", True, "RESTRICT"),
        text("status", 16),
        sa.Column("source_activity_reference", JSON, nullable=False),
        stamp("created_at"),
        stamp("updated_at"),
        sa.UniqueConstraint(
            "user_id", "cefr_level", "topic", name="uq_ai_recommendation_topic"
        ),
    )
    op.create_index(
        "ix_ai_learning_recommendations_user_id",
        "ai_learning_recommendations",
        ["user_id"],
    )


def downgrade():
    # Explicit rollback deletes only Milestone 05 memory, never users/curriculum/progress.
    for table in (
        "ai_learning_recommendations",
        "ai_practice_feedback",
        "ai_message_sources",
        "ai_messages",
        "ai_conversations",
    ):
        op.drop_table(table)
