"""
Add stream health table

Revision ID: 04_stream_health
Revises: 03_alerts
Create Date: 2023-10-25 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '04_stream_health'
down_revision = '03_alerts'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database schema."""
    # Create stream_health table
    op.create_table(
        'stream_health',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.Float(), nullable=False),
        
        # OBS statistics
        sa.Column('fps', sa.Float(), nullable=True),
        sa.Column('render_total_frames', sa.Integer(), nullable=True),
        sa.Column('render_missed_frames', sa.Integer(), nullable=True),
        sa.Column('output_total_frames', sa.Integer(), nullable=True),
        sa.Column('output_skipped_frames', sa.Integer(), nullable=True),
        sa.Column('average_frame_time', sa.Float(), nullable=True),
        sa.Column('cpu_usage', sa.Float(), nullable=True),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('free_disk_space', sa.Float(), nullable=True),
        
        # Stream statistics
        sa.Column('bitrate', sa.Float(), nullable=True),
        sa.Column('num_dropped_frames', sa.Integer(), nullable=True),
        sa.Column('num_total_frames', sa.Integer(), nullable=True),
        sa.Column('strain', sa.Float(), nullable=True),
        sa.Column('stream_duration', sa.Float(), nullable=True),
        
        # Network statistics
        sa.Column('kbits_per_sec', sa.Float(), nullable=True),
        sa.Column('ping', sa.Float(), nullable=True),
        
        sa.Column('created_at', sa.Float(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['stream_sessions.id'], ),
    )
    
    # Create an index on session_id and timestamp for faster queries
    op.create_index(
        'ix_stream_health_session_id_timestamp',
        'stream_health',
        ['session_id', 'timestamp'],
        unique=False
    )


def downgrade():
    """Downgrade database schema."""
    # Drop the index first
    op.drop_index('ix_stream_health_session_id_timestamp', table_name='stream_health')
    
    # Drop the table
    op.drop_table('stream_health') 