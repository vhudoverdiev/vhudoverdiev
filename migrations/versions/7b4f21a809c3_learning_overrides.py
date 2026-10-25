"""Explicit administrator overrides; preserve attempts and video progress."""
from alembic import op
import sqlalchemy as sa
revision = '7b4f21a809c3'
down_revision = '1a9c7b2e4f10'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('learning_override',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('lesson_id', sa.Integer(), sa.ForeignKey('lesson.id'), nullable=False),
        sa.Column('unlocked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('manual_score', sa.Integer(), nullable=True),
        sa.Column('granted_by_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'lesson_id', name='uq_learning_override_user_lesson'))
    op.create_index('ix_learning_override_user_id','learning_override',['user_id'])
    op.create_index('ix_learning_override_lesson_id','learning_override',['lesson_id'])


def downgrade():
    op.drop_index('ix_learning_override_lesson_id', table_name='learning_override')
    op.drop_index('ix_learning_override_user_id', table_name='learning_override')
    op.drop_table('learning_override')
