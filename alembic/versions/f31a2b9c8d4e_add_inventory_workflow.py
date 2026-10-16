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
    op.create_index("ix_inventory_transactions_product_id", "inventory_transactions", ["product_id"])
    op.create_index("ix_inventory_transactions_created_at", "inventory_transactions", ["created_at"])
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
    op.create_index("ix_purchase_orders_order_number", "purchase_orders", ["order_number"])
    op.create_index("ix_purchase_orders_product_id", "purchase_orders", ["product_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])
    op.create_index("ix_purchase_orders_created_at", "purchase_orders", ["created_at"])


def downgrade():
    op.drop_table("purchase_orders")
    op.drop_table("inventory_transactions")
