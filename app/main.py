from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import safe_join

from .models import Course, Lesson, LessonProgress, QuizAttempt
from .services.course_service import published_courses
from .services.learning_access import course_states, require_lesson_access

bp = Blueprint("main", __name__)


@bp.get("/site.webmanifest")
def web_manifest():
    return send_from_directory(current_app.static_folder, "site.webmanifest", mimetype="application/manifest+json", max_age=3600)


@bp.get("/apple-touch-icon.png")
def apple_touch_icon():
    return send_from_directory(current_app.static_folder, "icons/icon-180.png", max_age=86400)


@bp.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("landing.html")


@bp.get("/dashboard")
@login_required
def dashboard():
    courses = published_courses()
    return render_template("dashboard.html", courses=courses)


@bp.get("/courses")
@login_required
def courses():
    return render_template("courses.html", courses=published_courses())


@bp.get("/courses/<int:course_id>")
@login_required
def course_detail(course_id):
    course = Course.query.filter_by(id=course_id, published=True).first_or_404()
    progress = {item.lesson_id: item for item in LessonProgress.query.filter_by(user_id=current_user.id).join(Lesson).filter(Lesson.course_id == course.id).all()}
    attempts = {}
    for item in QuizAttempt.query.filter_by(user_id=current_user.id).join(Lesson).filter(Lesson.course_id == course.id).order_by(QuizAttempt.created_at.desc()).all():
        attempts.setdefault(item.lesson_id, item)
    lesson_states = course_states(course)
    ordered_lessons = sorted(
        (lesson for lesson in course.lessons if not lesson.quiz_data),
        key=lambda lesson: (lesson.position, lesson.id),
    )
    next_lesson = next(
        (lesson for lesson in ordered_lessons
         if lesson_states[lesson.id]["unlocked"] and not lesson_states[lesson.id]["completed"]),
        ordered_lessons[-1] if ordered_lessons else None,
    )
    return render_template(
        "course_detail.html", course=course, progress=progress, attempts=attempts,
        lesson_states=lesson_states,
        active_module=next_lesson.module_name if next_lesson else None,
    )


@bp.get("/courses/<int:course_id>/lessons/<int:lesson_id>")
@login_required
def lesson_detail(course_id, lesson_id):
    course = Course.query.filter_by(id=course_id, published=True).first_or_404()
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    lesson_status = require_lesson_access(lesson)
    progress = LessonProgress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
    from .services.lesson_quiz import questions_for_lesson
    quiz_questions = questions_for_lesson(lesson)
    quiz_lesson = lesson
    from .services.quiz_flow import latest_attempt
    attempt = latest_attempt(lesson, quiz_questions) if quiz_questions else None
    quiz_passed = lesson_status["completed"] if quiz_questions else True
    previous = Lesson.query.filter_by(course_id=course.id).filter(Lesson.position < lesson.position, Lesson.quiz_data.is_(None)).order_by(Lesson.position.desc()).first()
    following = Lesson.query.filter_by(course_id=course.id).filter(Lesson.position > lesson.position, Lesson.quiz_data.is_(None)).order_by(Lesson.position.asc()).first()
    return render_template("lesson_detail.html", course=course, lesson=lesson, progress=progress, attempt=attempt, previous=previous, following=following, quiz_lesson=quiz_lesson, quiz_questions=quiz_questions, quiz_passed=quiz_passed, lesson_status=lesson_status)


@bp.get("/media/<path:filename>")
@login_required
def media_file(filename):
    media_root = current_app.config.get("MEDIA_ROOT", safe_join(current_app.instance_path, "media"))
    lesson = Lesson.query.join(Course).filter(Lesson.video_url == f"local:{filename}", Course.published.is_(True)).first_or_404()
    require_lesson_access(lesson)
    return send_from_directory(media_root, filename, conditional=True, max_age=0)


@bp.get("/lessons/<int:lesson_id>/resources/<path:filename>")
@login_required
def lesson_resource(lesson_id, filename):
    lesson = Lesson.query.join(Course).filter(Lesson.id == lesson_id, Course.published.is_(True)).first_or_404()
    require_lesson_access(lesson)
    if not any(resource.get("path") == filename for resource in (lesson.resources_json or [])):
        abort(404)
    media_root = current_app.config.get("MEDIA_ROOT", safe_join(current_app.instance_path, "media"))
    return send_from_directory(media_root, filename, as_attachment=True, conditional=True)


@bp.post("/lessons/<int:lesson_id>/progress")
@login_required
def update_lesson_progress(lesson_id):
    lesson = Lesson.query.join(Course).filter(Lesson.id == lesson_id, Course.published.is_(True)).first_or_404()
    require_lesson_access(lesson)
    try:
        watched = max(0, min(100, int(request.form.get("watched_percent", "0"))))
    except ValueError:
        abort(400)
    progress = LessonProgress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
    if progress is None:
        progress = LessonProgress(user_id=current_user.id, lesson_id=lesson.id)
        from .extensions import db
        db.session.add(progress)
    progress.watched_percent = max(progress.watched_percent, watched)
    if lesson.course.course_type == "library":
        progress.completed = progress.completed or watched >= 90
    progress.updated_at = datetime.utcnow()
    from .extensions import db
    db.session.commit()
    if request.form.get("return_to_lesson") == "1":
        return redirect(url_for("main.lesson_detail", course_id=lesson.course_id, lesson_id=lesson.id, _anchor="lesson-quiz"))
    return "", 204


def _check_lesson(lesson_id):
    lesson = Lesson.query.join(Course).filter(Lesson.id == lesson_id, Course.published.is_(True)).first_or_404()
    require_lesson_access(lesson)
    from .services.lesson_quiz import questions_for_lesson
    questions = questions_for_lesson(lesson)
    if not questions or lesson.course.course_type == "library":
        abort(404)
    return lesson, questions


@bp.get("/lessons/<int:lesson_id>/quiz")
@login_required
def lesson_check(lesson_id):
    from .services.quiz_flow import load_state, passing_score, latest_attempt
    from .services.celebration import celebration_for
    lesson, questions = _check_lesson(lesson_id)
    state = load_state(lesson, questions)
    feedback = bool(state['feedback'] and state['answers'])
    index = len(state['answers']) - 1 if feedback else len(state['answers'])
    following = Lesson.query.filter_by(course_id=lesson.course_id).filter(Lesson.position > lesson.position, Lesson.quiz_data.is_(None)).order_by(Lesson.position).first()
    attempt = latest_attempt(lesson, questions) if index >= len(questions) else None
    return render_template('lesson_check.html', course=lesson.course, lesson=lesson, questions=questions,
                           question=questions[index] if index < len(questions) else None,
                           index=index, feedback=feedback, state=state, attempt=attempt,
                           required_score=passing_score(questions), following=following,
                           celebration=celebration_for(attempt) if attempt and attempt.score >= passing_score(questions) else None)


@bp.post("/lessons/<int:lesson_id>/quiz/answer")
@login_required
def answer_lesson_check(lesson_id):
    from .services.quiz_flow import load_state, save_state, passing_score
    from .extensions import db
    lesson, questions = _check_lesson(lesson_id)
    state = load_state(lesson, questions)
    index = request.form.get('question_index', type=int)
    selected = request.form.get('answer', type=int)
    if state['feedback'] or index != len(state['answers']) or len(state['answers']) >= len(questions):
        return redirect(url_for('main.lesson_check', lesson_id=lesson.id))
    if selected is None or not 0 <= selected < len(questions[index]['options']):
        abort(400)
    state['answers'].append(selected)
    state['feedback'] = True
    if len(state['answers']) == len(questions):
        answers = [{'selected': choice, 'correct': choice == questions[i]['correct']} for i, choice in enumerate(state['answers'])]
        answers[0]['quiz_version'] = state['version']
        score = sum(answer['correct'] for answer in answers)
        db.session.add(QuizAttempt(user_id=current_user.id, lesson_id=lesson.id, score=score, question_count=len(questions), answers_json=answers))
        if score >= passing_score(questions):
            progress = LessonProgress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
            if progress is None:
                progress = LessonProgress(user_id=current_user.id, lesson_id=lesson.id)
                db.session.add(progress)
            progress.completed = True
            progress.updated_at = datetime.utcnow()
        db.session.commit()
    save_state(lesson, state)
    return redirect(url_for('main.lesson_check', lesson_id=lesson.id))


@bp.post("/lessons/<int:lesson_id>/quiz/next")
@login_required
def next_check_question(lesson_id):
    from .services.quiz_flow import load_state, save_state
    lesson, questions = _check_lesson(lesson_id)
    state = load_state(lesson, questions)
    state['feedback'] = False
    save_state(lesson, state)
    return redirect(url_for('main.lesson_check', lesson_id=lesson.id))


@bp.post("/lessons/<int:lesson_id>/quiz/restart")
@login_required
def restart_lesson_check(lesson_id):
    from .services.quiz_flow import load_state
    lesson, questions = _check_lesson(lesson_id)
    load_state(lesson, questions, reset=True)
    return redirect(url_for('main.lesson_check', lesson_id=lesson.id))
