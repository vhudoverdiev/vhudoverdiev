"""Server-side grading and versioned, resumable single-question checks."""
import hashlib
import json
from flask import session
from flask_login import current_user
from ..models import QuizAttempt


def fingerprint(questions):
    return hashlib.sha256(json.dumps(questions, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def passing_score(questions):
    return (len(questions) + 1) // 2


def latest_attempt(lesson, questions):
    version = fingerprint(questions)
    for attempt in QuizAttempt.query.filter_by(user_id=current_user.id, lesson_id=lesson.id, question_count=len(questions)).order_by(QuizAttempt.created_at.desc()):
        if attempt.answers_json and attempt.answers_json[0].get('quiz_version') == version:
            return attempt
    return None


def load_state(lesson, questions, reset=False):
    states = session.get('lesson_checks', {})
    key = f'{current_user.id}:{lesson.id}'
    version = fingerprint(questions)
    state = states.get(key)
    if reset or not state or state.get('version') != version:
        state = {'version': version, 'answers': [], 'feedback': False}
    save_state(lesson, state)
    return state


def save_state(lesson, state):
    states = dict(session.get('lesson_checks', {}))
    key = f'{current_user.id}:{lesson.id}'
    states.pop(key, None)
    states[key] = state
    while len(states) > 5:
        states.pop(next(iter(states)))
    session['lesson_checks'] = states


def has_passed(lesson, questions):
    version = fingerprint(questions)
    for attempt in QuizAttempt.query.filter_by(user_id=current_user.id, lesson_id=lesson.id, question_count=len(questions)).filter(QuizAttempt.score >= passing_score(questions)):
        if attempt.answers_json and attempt.answers_json[0].get('quiz_version') == version:
            return True
    return False
