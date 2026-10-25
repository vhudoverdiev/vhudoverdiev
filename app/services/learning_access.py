"""Course-wide completion and sequential access, independent of video position."""
from flask import request, abort
from flask_login import current_user
from ..models import LessonProgress, QuizAttempt
from .lesson_quiz import questions_for_lesson
from .quiz_flow import fingerprint, passing_score


def course_states(course):
    cache = request.environ.setdefault('vhiti.learning_states', {})
    if course.id in cache:
        return cache[course.id]
    lessons = sorted((lesson for lesson in course.lessons if not lesson.quiz_data), key=lambda lesson: (lesson.position, lesson.id))
    ids = [lesson.id for lesson in lessons]
    progress = {row.lesson_id: row for row in LessonProgress.query.filter(LessonProgress.user_id == current_user.id, LessonProgress.lesson_id.in_(ids)).all()}
    attempts = {}
    for row in QuizAttempt.query.filter(QuizAttempt.user_id == current_user.id, QuizAttempt.lesson_id.in_(ids)).order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc()):
        attempts.setdefault(row.lesson_id, []).append(row)
    states = {}
    prefix_complete = True
    for lesson in lessons:
        questions = questions_for_lesson(lesson)
        version = fingerprint(questions)
        valid = [row for row in attempts.get(lesson.id, []) if row.question_count == len(questions) and row.answers_json and row.answers_json[0].get('quiz_version') == version]
        passed = any(row.score >= passing_score(questions) for row in valid)
        viewed = progress.get(lesson.id)
        library = course.course_type == 'library'
        completed = bool(viewed and viewed.completed) if library else passed
        unlocked = True if library else prefix_complete
        states[lesson.id] = {'completed': completed, 'unlocked': unlocked,
                            'watched': viewed.watched_percent if viewed else 0,
                            'score': max((row.score for row in valid), default=None),
                            'label': 'Завершён' if completed else 'Заблокирован' if not unlocked else 'Нужно пройти тест' if valid or (viewed and viewed.watched_percent >= 90) else 'Не завершён'}
        if not library:
            prefix_complete = prefix_complete and completed
    cache[course.id] = states
    return states


def require_lesson_access(lesson):
    state = course_states(lesson.course).get(lesson.id)
    if state is None or not state['unlocked']:
        request.environ['vhiti.locked_course_id'] = lesson.course_id
        abort(403, description='Сначала пройдите тест предыдущего урока: не менее 5 правильных ответов из 10.')
    return state
