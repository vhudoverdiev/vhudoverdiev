"""Removal of the course explicitly retired by its owner."""
from ..extensions import db
from ..models import Course, Lesson, LessonProgress, QuizAttempt, LearningOverride

AI_COURSE_TITLE = 'AI Developer на Python: LLM в реальных приложениях'


def retire_ai_course():
    courses = Course.query.filter_by(title=AI_COURSE_TITLE).all()
    for course in courses:
        ids = [lesson.id for lesson in course.lessons]
        if ids:
            LearningOverride.query.filter(LearningOverride.lesson_id.in_(ids)).delete(synchronize_session=False)
            LessonProgress.query.filter(LessonProgress.lesson_id.in_(ids)).delete(synchronize_session=False)
            QuizAttempt.query.filter(QuizAttempt.lesson_id.in_(ids)).delete(synchronize_session=False)
        db.session.delete(course)
    db.session.commit()
    return len(courses)
