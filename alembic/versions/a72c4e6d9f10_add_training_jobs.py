"""add persistent model training jobs

Revision ID: a72c4e6d9f10
Revises: f31a2b9c8d4e
"""

from alembic import op
import sqlalchemy as sa

revision = "a72c4e6d9f10"
down_revision = "f31a2b9c8d4e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "training_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("requested_by", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_training_jobs_status", "training_jobs", ["status"])
    op.create_index("ix_training_jobs_created_at", "training_jobs", ["created_at"])


def downgrade():
    op.drop_table("training_jobs")
