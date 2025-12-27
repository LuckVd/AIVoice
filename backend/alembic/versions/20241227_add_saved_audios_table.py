"""add saved_audios table

Revision ID: 20241227_add_saved_audios
Revises: 20241220_add_ssml_fields
Create Date: 2024-12-27 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241227_add_saved_audios'
down_revision = '20241220_120000'
branch_labels = None
depends_on = None


def upgrade():
    # Create saved_audios table
    op.create_table(
        'saved_audios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('original_task_id', sa.String(length=100), nullable=False),
        sa.Column('audio_path', sa.String(length=500), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('voice', sa.String(length=50), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_audios_id'), 'saved_audios', ['id'])


def downgrade():
    # Drop saved_audios table
    op.drop_index(op.f('ix_saved_audios_id'), table_name='saved_audios')
    op.drop_table('saved_audios')
