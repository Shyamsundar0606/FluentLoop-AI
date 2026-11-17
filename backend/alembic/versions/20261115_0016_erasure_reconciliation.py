"""Purpose-limited account reference for backup erasure reconciliation."""
from alembic import op
import sqlalchemy as sa

revision = "20261115_0016"
down_revision = "20261115_0015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("account_erasure_jobs", sa.Column("account_reference", sa.Uuid(), nullable=True))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM account_erasure_jobs WHERE account_reference IS NOT NULL)")).scalar_one():
        raise RuntimeError("Downgrade would discard backup erasure reconciliation records.")
    op.drop_column("account_erasure_jobs", "account_reference")
