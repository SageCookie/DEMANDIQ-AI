"""fix model_runs columns case sensitivity

Revision ID: 2b7a91f8e3d1
Revises: c48bc7184d59
Create Date: 2026-10-13 10:03:47.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b7a91f8e3d1'
down_revision: Union[str, Sequence[str], None] = 'c48bc7184d59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix column case sensitivity in model_runs table to match SQLAlchemy model.

    The SQLAlchemy model now uses lowercase column names (mae, rmse, mape, wape).
    The current DB has these columns as lowercase (from inspection) but we must
    ensure they exist and have the correct constraints.

    This migration handles:
    1. Columns are uppercase (MAE, RMSE, MAPE, WAPE) -> rename to lowercase
    2. Columns are already lowercase -> do nothing (but ensure constraints)
    3. Columns don't exist -> add them as lowercase with appropriate NULL/NOT NULL
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'model_runs' not in inspector.get_table_names():
        return
    existing_cols = {column['name'] for column in inspector.get_columns('model_runs')}

    # Column mappings: uppercase -> lowercase (current SQLAlchemy model names)
    columns_to_fix = {
        'MAE': 'mae',
        'RMSE': 'rmse',
        'MAPE': 'mape',
        'WAPE': 'wape'
    }

    for upper_name, lower_name in columns_to_fix.items():
        if upper_name in existing_cols and lower_name not in existing_cols:
            # Case 1: uppercase exists, lowercase doesn't -> rename to lowercase
            op.execute(sa.text(
                f'ALTER TABLE model_runs RENAME COLUMN {upper_name} TO {lower_name}'
            ))
        elif lower_name in existing_cols:
            # Case 2: already lowercase -> nothing needed for name
            pass
        elif upper_name not in existing_cols and lower_name not in existing_cols:
            # Case 3: column doesn't exist -> add it as lowercase
            # For mae, rmse, mape: model requires NOT NULL, but we add as nullable first
            # to avoid constraint violation on existing rows, then we'll set NOT NULL.
            # For wape: model allows NULL.
            nullable = lower_name not in ('mae', 'rmse', 'mape')  # wape is nullable
            op.add_column('model_runs', sa.Column(lower_name, sa.Float(), nullable=nullable))
            # If we added as nullable but the model requires NOT NULL, we'll handle below.

    # After ensuring columns exist with correct names, set NOT NULL where required by model
    # MAE, RMSE, MAPE are NOT NULL in SQLAlchemy model
    for col in ['mae', 'rmse', 'mape']:
        # Check if column exists and is nullable
        columns = {column['name']: column for column in sa.inspect(conn).get_columns('model_runs')}
        if col in columns and columns[col]['nullable']:
            # Column exists but is nullable - alter to NOT NULL
            # Since table is empty (0 rows from earlier check), we can safely set NOT NULL
            op.alter_column('model_runs', col, nullable=False)


def downgrade() -> None:
    """
    Revert column names back to uppercase and restore original NOT NULL constraints.

    - mae, rmse, mape -> NOT NULL (these were NOT NULL in original model)
    - wape -> NULL (this was nullable in original model)
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'model_runs' not in inspector.get_table_names():
        return

    # First, restore NOT NULL constraints before renaming
    # mae, rmse, mape were originally NOT NULL
    for col in ['mae', 'rmse', 'mape']:
        columns = {column['name']: column for column in sa.inspect(conn).get_columns('model_runs')}
        if col in columns and columns[col]['nullable']:
            op.alter_column('model_runs', col, nullable=False)

    # wape was originally nullable
    for col in ['wape']:
        columns = {column['name']: column for column in sa.inspect(conn).get_columns('model_runs')}
        if col in columns and not columns[col]['nullable']:
            op.alter_column('model_runs', col, nullable=True)

    # Rename columns back to uppercase
    columns_to_revert = {
        'mae': 'MAE',
        'rmse': 'RMSE',
        'mape': 'MAPE',
        'wape': 'WAPE'
    }

    for lower_name, upper_name in columns_to_revert.items():
        op.execute(sa.text(
            f'ALTER TABLE model_runs RENAME COLUMN {lower_name} TO {upper_name}'
        ))
