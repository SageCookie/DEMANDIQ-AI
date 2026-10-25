"""add users and sessions

Revision ID: c48bc7184d59
Revises: 
Create Date: 2026-10-12 20:02:52.976086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c48bc7184d59'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is the first migration used by a hosted, empty database.  Earlier
    # local builds relied on SQLAlchemy's development-time create_all(), which
    # meant a clean deployment did not get the operational tables.
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())

    def create(name: str, *columns_and_constraints) -> bool:
        if name in existing_tables:
            return False
        op.create_table(name, *columns_and_constraints)
        return True

    if create('products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_code', sa.String(length=50), nullable=False),
        sa.Column('product_name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False, server_default='0'),
        sa.Column('lead_time_days', sa.Float(), nullable=False, server_default='7'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    ):
        op.create_index('ix_products_product_code', 'products', ['product_code'])
        op.create_index('ix_products_category', 'products', ['category'])
        op.create_index('ix_products_active', 'products', ['active'])

    if create('sales',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('sale_date', sa.DateTime(), nullable=False),
        sa.Column('quantity_sold', sa.Float(), nullable=False, server_default='0'),
        sa.Column('unit_price', sa.Float(), nullable=False, server_default='0'),
        sa.Column('revenue', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    ):
        op.create_index('ix_sales_product_id', 'sales', ['product_id'])
        op.create_index('ix_sales_sale_date', 'sales', ['sale_date'])
        op.create_index('idx_sales_product_date', 'sales', ['product_id', 'sale_date'])

    if create('inventory',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, unique=True),
        sa.Column('quantity_available', sa.Float(), nullable=False, server_default='0'),
        sa.Column('quantity_reserved', sa.Float(), nullable=False, server_default='0'),
        sa.Column('quantity_on_order', sa.Float(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    ):
        op.create_index('ix_inventory_product_id', 'inventory', ['product_id'])

    if create('forecasts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('forecast_date', sa.DateTime(), nullable=False),
        sa.Column('predicted_demand', sa.Float(), nullable=False),
        sa.Column('lower_bound', sa.Float(), nullable=True),
        sa.Column('upper_bound', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
    ):
        op.create_index('ix_forecasts_product_id', 'forecasts', ['product_id'])
        op.create_index('ix_forecasts_forecast_date', 'forecasts', ['forecast_date'])
        op.create_index('ix_forecasts_model_version', 'forecasts', ['model_version'])
        op.create_index('idx_forecast_product_date', 'forecasts', ['product_id', 'forecast_date'])

    if create('inventory_recommendations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('current_inventory', sa.Float(), nullable=False),
        sa.Column('forecast_demand', sa.Float(), nullable=False),
        sa.Column('lead_time_demand', sa.Float(), nullable=False),
        sa.Column('safety_stock', sa.Float(), nullable=False),
        sa.Column('reorder_point', sa.Float(), nullable=False),
        sa.Column('recommended_quantity', sa.Float(), nullable=False),
        sa.Column('stockout_risk', sa.String(length=20), nullable=False),
        sa.Column('recommendation', sa.String(length=50), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
    ):
        op.create_index('ix_inventory_recommendations_product_id', 'inventory_recommendations', ['product_id'])
        op.create_index('ix_inventory_recommendations_stockout_risk', 'inventory_recommendations', ['stockout_risk'])
        op.create_index('ix_inventory_recommendations_generated_at', 'inventory_recommendations', ['generated_at'])

    if create('model_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False, unique=True),
        sa.Column('training_dates', sa.String(length=100), nullable=True),
        sa.Column('mae', sa.Float(), nullable=False),
        sa.Column('rmse', sa.Float(), nullable=False),
        sa.Column('mape', sa.Float(), nullable=False),
        sa.Column('wape', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PRODUCTION'),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('artifact_path', sa.String(length=500), nullable=False),
    ):
        op.create_index('ix_model_runs_model_version', 'model_runs', ['model_version'])
        op.create_index('ix_model_runs_status', 'model_runs', ['status'])

    if create('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    ):
        op.create_index('ix_users_username', 'users', ['username'], unique=False)
        op.create_index('ix_users_id', 'users', ['id'], unique=False)
    if create('sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    ):
        op.create_index('ix_sessions_token_hash', 'sessions', ['token_hash'], unique=False)
        op.create_index('ix_sessions_user_id', 'sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_sessions_user_id', table_name='sessions')
    op.drop_index('ix_sessions_token_hash', table_name='sessions')
    op.drop_table('sessions')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
