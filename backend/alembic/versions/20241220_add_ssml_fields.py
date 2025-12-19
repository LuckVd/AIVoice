"""Add SSML fields to tts_requests table

Revision ID: 20241220_add_ssml_fields
Revises: 20241216_120000_create_initial_tts_requests_table
Create Date: 2025-12-20 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20241220_120000'
down_revision = '20241216_120000'
branch_labels = None
depends_on = None


def upgrade():
    # Add SSML related columns
    op.add_column('tts_requests', sa.Column('use_ssml', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('tts_requests', sa.Column('ssml_preset', sa.String(length=50), nullable=True))
    op.add_column('tts_requests', sa.Column('ssml_config', sa.JSON(), nullable=True))
    op.add_column('tts_requests', sa.Column('ssml_generated', sa.Text(), nullable=True))


def downgrade():
    # Remove SSML related columns
    op.drop_column('tts_requests', 'ssml_generated')
    op.drop_column('tts_requests', 'ssml_config')
    op.drop_column('tts_requests', 'ssml_preset')
    op.drop_column('tts_requests', 'use_ssml')