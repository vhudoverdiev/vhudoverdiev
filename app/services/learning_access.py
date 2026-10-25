"""Durable completion from actual past results and explicit admin overrides."""
from flask import request, abort
from flask_login import current_user
from ..models import LessonProgress, QuizAttempt, LearningOverride


def passed_attempt(row):
    return row.question_count > 0 and isinstance(row.answers_json, list) and len(row.answers_json) == row.question_count and 0 <= row.score <= row.question_count and row.score * 2 >= row.question_count


def course_states(course, user_id=None):
    user_id = user_id or current_user.id
    cache = request.environ.setdefault('vhiti.learning_states', {})
    key = (course.id, user_id)
    if key in cache:
        return cache[key]
    all_lessons = {lesson.id: lesson for lesson in course.lessons}
    lessons = sorted((lesson for lesson in all_lessons.values() if not lesson.quiz_data), key=lambda lesson: (lesson.position, lesson.id))
    ids = list(all_lessons)
    progress = {row.lesson_id: row for row in LessonProgress.query.filter(LessonProgress.user_id == user_id, LessonProgress.lesson_id.in_(ids)).all()}
    overrides = {row.lesson_id: row for row in LearningOverride.query.filter(LearningOverride.user_id == user_id, LearningOverride.lesson_id.in_(ids)).all()}
    attempts, topic_passes = {}, {}
    for row in QuizAttempt.query.filter(QuizAttempt.user_id == user_id, QuizAttempt.lesson_id.in_(ids)).order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc()):
        attempts.setdefault(row.lesson_id, []).append(row)
        source = all_lessons[row.lesson_id]
        if source.quiz_data and passed_attempt(row):
            topic_passes.setdefault(source.module_name, []).append(row)
    states = {}
    previous_completed = True
    for lesson in lessons:
        viewed = progress.get(lesson.id)
        override = overrides.get(lesson.id)
        actual = attempts.get(lesson.id, [])
        successes = [row for row in actual if passed_attempt(row)]
        inherited = topic_passes.get(lesson.module_name, [])
        best = max(successes or inherited or actual, key=lambda row: row.score / max(row.question_count, 1), default=None)
        manual = bool(override and override.manual_score is not None and override.manual_score >= 5)
        library = course.course_type == 'library'
        completed = bool(viewed and viewed.completed) if library else bool(manual or successes or inherited)
        unlocked = library or completed or previous_completed or bool(override and override.unlocked)
        source = 'Зачтено администратором' if manual else 'Ранее сдан тест темы' if inherited and not successes else ''
        states[lesson.id] = {
            'completed': completed, 'unlocked': bool(unlocked),
            'watched': viewed.watched_percent if viewed else 0,
            'score': override.manual_score if manual else best.score if best else None,
            'score_total': 10 if manual else best.question_count if best else 10,
            'source': source,
            'label': 'Завершён' if completed else 'Заблокирован' if not unlocked else 'Нужно пройти тест' if actual or (viewed and viewed.watched_percent >= 90) else 'Не завершён',
        }
        previous_completed = completed
    cache[key] = states
    return states


def require_lesson_access(lesson):
    state = course_states(lesson.course).get(lesson.id)
    if state is None or not state['unlocked']:
        request.environ['vhiti.locked_course_id'] = lesson.course_id
        abort(403, description='Сначала пройдите тест предыдущего урока: не менее 5 правильных ответов из 10.')
    return state
