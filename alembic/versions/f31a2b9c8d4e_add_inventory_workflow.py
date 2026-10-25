"""add inventory workflow audit and purchase-order tables

Revision ID: f31a2b9c8d4e
Revises: 2b7a91f8e3d1
"""

from alembic import op
import sqlalchemy as sa

revision = "f31a2b9c8d4e"
down_revision = "2b7a91f8e3d1"
branch_labels = None
depends_on = None


def upgrade():
    # Some early local installs created these operational tables directly from
    # SQLAlchemy before this migration was introduced. Preserve those records
    # and allow Alembic to catch its history up instead of failing on creation.
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "inventory_transactions" not in tables:
        op.create_table(
            "inventory_transactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("quantity_delta", sa.Float(), nullable=False),
            sa.Column("quantity_before", sa.Float(), nullable=False),
            sa.Column("quantity_after", sa.Float(), nullable=False),
            sa.Column("reason", sa.String(length=50), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        tables.add("inventory_transactions")
    if "purchase_orders" not in tables:
        op.create_table(
            "purchase_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_number", sa.String(length=50), nullable=False, unique=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("expected_arrival_date", sa.DateTime(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # Index creation is also safe to resume if a previous setup created only
    # the tables. Re-read the inspector after any table creation.
    existing_indexes = {
        table: {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
        for table in ("inventory_transactions", "purchase_orders")
    }
    indexes = (
        ("inventory_transactions", "ix_inventory_transactions_product_id", ["product_id"]),
        ("inventory_transactions", "ix_inventory_transactions_created_at", ["created_at"]),
        ("purchase_orders", "ix_purchase_orders_order_number", ["order_number"]),
        ("purchase_orders", "ix_purchase_orders_product_id", ["product_id"]),
        ("purchase_orders", "ix_purchase_orders_status", ["status"]),
        ("purchase_orders", "ix_purchase_orders_created_at", ["created_at"]),
    )
    for table, name, columns in indexes:
        if name not in existing_indexes[table]:
            op.create_index(name, table, columns)


def downgrade():
    op.drop_table("purchase_orders")
    op.drop_table("inventory_transactions")
