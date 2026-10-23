"""Add course media mode, quizzes, and learning analytics.

Revision ID: 1a9c7b2e4f10
Revises: 5990ebe7e21f
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = "1a9c7b2e4f10"
down_revision = "5990ebe7e21f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("course", sa.Column("course_type", sa.String(length=20), nullable=False, server_default="course"))
    op.add_column("lesson", sa.Column("module_name", sa.String(length=180), nullable=False, server_default=""))
    op.add_column("lesson", sa.Column("quiz_data", sa.JSON(), nullable=True))
    op.add_column("lesson", sa.Column("resources_json", sa.JSON(), nullable=True))
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lesson.id"), nullable=False),
        sa.Column("watched_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
    )
    op.create_index("ix_lesson_progress_user_id", "lesson_progress", ["user_id"])
    op.create_index("ix_lesson_progress_lesson_id", "lesson_progress", ["lesson_id"])
    op.create_table(
        "quiz_attempt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lesson.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("answers_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_quiz_attempt_user_id", "quiz_attempt", ["user_id"])
    op.create_index("ix_quiz_attempt_lesson_id", "quiz_attempt", ["lesson_id"])


def downgrade():
    op.drop_index("ix_quiz_attempt_lesson_id", table_name="quiz_attempt")
    op.drop_index("ix_quiz_attempt_user_id", table_name="quiz_attempt")
    op.drop_table("quiz_attempt")
    op.drop_index("ix_lesson_progress_lesson_id", table_name="lesson_progress")
    op.drop_index("ix_lesson_progress_user_id", table_name="lesson_progress")
    op.drop_table("lesson_progress")
    op.drop_column("lesson", "quiz_data")
    op.drop_column("lesson", "resources_json")
    op.drop_column("lesson", "module_name")
    op.drop_column("course", "course_type")
