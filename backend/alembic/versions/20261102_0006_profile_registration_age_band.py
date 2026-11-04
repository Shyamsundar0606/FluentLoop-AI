"""Optional minimized registration age information (Milestone 05 enhancement).

No name backfill or existing-account eligibility changes.
"""

from alembic import op
import sqlalchemy as sa

revision = "20261102_0006"
down_revision = "20261102_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_profiles",
        sa.Column("registration_age_band", sa.String(16), nullable=True),
    )
    op.create_check_constraint(
        "ck_profile_registration_age_band",
        "user_profiles",
        "registration_age_band IS NULL OR registration_age_band IN ('under_18', '18_or_over')",
    )


def downgrade():
    op.drop_constraint(
        "ck_profile_registration_age_band", "user_profiles", type_="check"
    )
    op.drop_column("user_profiles", "registration_age_band")
