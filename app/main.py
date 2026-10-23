from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import safe_join

from .models import Course, Lesson, LessonProgress, QuizAttempt
from .services.course_service import published_courses

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
    return render_template("course_detail.html", course=course, progress=progress, attempts=attempts)


@bp.get("/courses/<int:course_id>/lessons/<int:lesson_id>")
@login_required
def lesson_detail(course_id, lesson_id):
    course = Course.query.filter_by(id=course_id, published=True).first_or_404()
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    progress = LessonProgress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
    from .services.lesson_quiz import questions_for_lesson
    quiz_questions = questions_for_lesson(lesson)
    quiz_lesson = lesson
    attempt = None if request.args.get("retake") == "1" else QuizAttempt.query.filter_by(user_id=current_user.id, lesson_id=lesson.id, question_count=len(quiz_questions)).order_by(QuizAttempt.created_at.desc()).first()
    previous = Lesson.query.filter_by(course_id=course.id).filter(Lesson.position < lesson.position, Lesson.quiz_data.is_(None)).order_by(Lesson.position.desc()).first()
    following = Lesson.query.filter_by(course_id=course.id).filter(Lesson.position > lesson.position, Lesson.quiz_data.is_(None)).order_by(Lesson.position.asc()).first()
    return render_template("lesson_detail.html", course=course, lesson=lesson, progress=progress, attempt=attempt, previous=previous, following=following, quiz_lesson=quiz_lesson, quiz_questions=quiz_questions)


@bp.get("/media/<path:filename>")
@login_required
def media_file(filename):
    media_root = current_app.config.get("MEDIA_ROOT", safe_join(current_app.instance_path, "media"))
    if not Lesson.query.join(Course).filter(Lesson.video_url == f"local:{filename}", Course.published.is_(True)).first():
        abort(404)
    return send_from_directory(media_root, filename, conditional=True, max_age=0)


@bp.get("/lessons/<int:lesson_id>/resources/<path:filename>")
@login_required
def lesson_resource(lesson_id, filename):
    lesson = Lesson.query.join(Course).filter(Lesson.id == lesson_id, Course.published.is_(True)).first_or_404()
    if not any(resource.get("path") == filename for resource in (lesson.resources_json or [])):
        abort(404)
    media_root = current_app.config.get("MEDIA_ROOT", safe_join(current_app.instance_path, "media"))
    return send_from_directory(media_root, filename, as_attachment=True, conditional=True)


@bp.post("/lessons/<int:lesson_id>/progress")
@login_required
def update_lesson_progress(lesson_id):
    lesson = Lesson.query.join(Course).filter(Lesson.id == lesson_id, Course.published.is_(True)).first_or_404()
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
    progress.completed = progress.completed or watched >= 90
    progress.updated_at = datetime.utcnow()
    from .extensions import db
    db.session.commit()
    if request.form.get("return_to_lesson") == "1":
        return redirect(url_for("main.lesson_detail", course_id=lesson.course_id, lesson_id=lesson.id, _anchor="lesson-quiz"))
    return "", 204


@bp.post("/lessons/<int:lesson_id>/quiz")
@login_required
def submit_lesson_quiz(lesson_id):
    lesson = Lesson.query.join(Course).filter(Lesson.id == lesson_id, Course.published.is_(True)).first_or_404()
    from .services.lesson_quiz import questions_for_lesson
    questions = questions_for_lesson(lesson)
    if not questions or lesson.course.course_type == "library":
        abort(404)
    return_lesson = Lesson.query.filter_by(id=request.form.get("return_lesson_id", type=int), course_id=lesson.course_id).first()
    return_lesson = return_lesson or lesson
    answers = []
    score = 0
    for index, question in enumerate(questions):
        try:
            selected = int(request.form.get(f"question-{index}", "-1"))
        except ValueError:
            selected = -1
        if selected < 0 or selected >= len(question["options"]):
            flash("Ответьте на все вопросы перед отправкой.", "error")
            return redirect(url_for("main.lesson_detail", course_id=lesson.course_id, lesson_id=return_lesson.id, _anchor="lesson-quiz"))
        correct = selected == int(question["correct"])
        score += int(correct)
        answers.append({"selected": selected, "correct": correct})
    attempt = QuizAttempt(user_id=current_user.id, lesson_id=lesson.id, score=score, question_count=len(questions), answers_json=answers)
    from .extensions import db
    db.session.add(attempt)
    db.session.commit()
    flash(f"Результат: {score} из {len(questions)}. Попытка сохранена в прогрессе.", "success" if score == len(questions) else "info")
    return redirect(url_for("main.lesson_detail", course_id=lesson.course_id, lesson_id=return_lesson.id, _anchor="lesson-quiz"))
