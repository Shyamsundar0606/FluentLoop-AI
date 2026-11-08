"""Add preferences and completion metadata to existing learner records."""
import sqlalchemy as sa
from alembic import op

revision = "20261108_0010"
down_revision = "20261104_0009"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {
        "user_preferences": [sa.Column("coach_corrections", sa.String(16), nullable=False, server_default="immediate")],
        "ai_conversations": [
            sa.Column("coach_difficulty", sa.String(16), nullable=False, server_default="normal"),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
        ],
    }
    for table, additions in columns.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        for column in additions:
            if column.name not in existing:
                op.add_column(table, column)


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM ai_conversations WHERE completed_at IS NOT NULL OR coach_difficulty <> 'normal') "
        "OR EXISTS (SELECT 1 FROM user_preferences WHERE coach_corrections <> 'immediate')"
    )).scalar_one():
        raise RuntimeError("Downgrade would discard saved coach data.")
    op.drop_column("ai_conversations", "completed_at")
    op.drop_column("ai_conversations", "coach_difficulty")
    op.drop_column("user_preferences", "coach_corrections")
