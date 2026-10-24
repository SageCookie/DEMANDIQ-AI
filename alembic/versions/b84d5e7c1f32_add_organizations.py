"""add organization workspaces and isolate operational records

Revision ID: b84d5e7c1f32
Revises: a72c4e6d9f10
"""
from alembic import op
import sqlalchemy as sa

revision = "b84d5e7c1f32"
down_revision = "a72c4e6d9f10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),
    )
    op.create_index("ix_organization_memberships_organization_id", "organization_memberships", ["organization_id"])
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"])
    connection = op.get_bind()
    for table in ("products", "model_runs", "training_jobs"):
        op.add_column(table, sa.Column("organization_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
        if connection.dialect.name != "sqlite":
            op.create_foreign_key(f"fk_{table}_organization_id", table, "organizations", ["organization_id"], ["id"])

    # Product codes only need to be unique within a workspace. The initial
    # schema made them globally unique, which prevents two companies from both
    # using a common SKU such as P001.
    inspector = sa.inspect(connection)
    for constraint in inspector.get_unique_constraints("products"):
        columns = constraint.get("column_names") or []
        name = constraint.get("name")
        if columns == ["product_code"] and name:
            if connection.dialect.name == "sqlite":
                with op.batch_alter_table("products") as batch:
                    batch.drop_constraint(name, type_="unique")
            else:
                op.drop_constraint(name, "products", type_="unique")
    if connection.dialect.name == "sqlite":
        with op.batch_alter_table("products") as batch:
            batch.create_unique_constraint("uq_products_organization_code", ["organization_id", "product_code"])
    else:
        op.create_unique_constraint("uq_products_organization_code", "products", ["organization_id", "product_code"])

    connection.execute(sa.text("INSERT INTO organizations (id, name, slug, created_at) VALUES (1, 'Default Workspace', 'default-workspace', CURRENT_TIMESTAMP)"))
    connection.execute(sa.text("UPDATE products SET organization_id = 1 WHERE organization_id IS NULL"))
    connection.execute(sa.text("UPDATE model_runs SET organization_id = 1 WHERE organization_id IS NULL"))
    connection.execute(sa.text("UPDATE training_jobs SET organization_id = 1 WHERE organization_id IS NULL"))
    connection.execute(sa.text("INSERT INTO organization_memberships (organization_id, user_id, role, created_at) SELECT 1, id, role, CURRENT_TIMESTAMP FROM users"))


def downgrade():
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        with op.batch_alter_table("products") as batch:
            batch.drop_constraint("uq_products_organization_code", type_="unique")
    else:
        op.drop_constraint("uq_products_organization_code", "products", type_="unique")
    for table in ("training_jobs", "model_runs", "products"):
        if connection.dialect.name != "sqlite":
            op.drop_constraint(f"fk_{table}_organization_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        op.drop_column(table, "organization_id")
    op.drop_table("organization_memberships")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
