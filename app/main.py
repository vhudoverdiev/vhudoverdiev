from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import safe_join

from .forms import AdminUserForm, CourseForm, LessonForm
from .models import Course, Lesson, LessonProgress, QuizAttempt, User
from .services.course_service import create_course, published_courses
import secrets

bp = Blueprint("main", __name__)


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
    module_quiz = None
    if not lesson.quiz_data:
        module_quiz = Lesson.query.filter_by(course_id=course.id, module_name=lesson.module_name).filter(Lesson.quiz_data.isnot(None)).first()
        last_module_lesson = Lesson.query.filter_by(course_id=course.id, module_name=lesson.module_name).filter(Lesson.quiz_data.is_(None)).order_by(Lesson.position.desc()).first()
        if not last_module_lesson or last_module_lesson.id != lesson.id:
            module_quiz = None
    quiz_lesson = lesson if lesson.quiz_data else module_quiz
    quiz_questions = quiz_lesson.quiz_data if quiz_lesson else None
    attempt = None if request.args.get("retake") == "1" or not quiz_lesson else QuizAttempt.query.filter_by(user_id=current_user.id, lesson_id=quiz_lesson.id).order_by(QuizAttempt.created_at.desc()).first()
    previous = Lesson.query.filter_by(course_id=course.id).filter(Lesson.position < lesson.position).order_by(Lesson.position.desc()).first()
    following = Lesson.query.filter_by(course_id=course.id).filter(Lesson.position > lesson.position).order_by(Lesson.position.asc()).first()
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
    return "", 204


@bp.post("/lessons/<int:lesson_id>/quiz")
@login_required
def submit_lesson_quiz(lesson_id):
    lesson = Lesson.query.join(Course).filter(Lesson.id == lesson_id, Course.published.is_(True)).first_or_404()
    questions = lesson.quiz_data or []
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


@bp.route("/admin/courses/new", methods=["GET", "POST"])
@login_required
def new_course():
    if not current_user.is_admin:
        abort(403)
    form = CourseForm()
    if form.validate_on_submit():
        course = create_course(form)
        flash("Черновик курса сохранён. Добавьте уроки и опубликуйте его, когда будете готовы.", "success")
        return redirect(url_for("main.admin_courses"))
    return render_template("course_form.html", form=form)


@bp.get("/admin/courses")
@login_required
def admin_courses():
    if not current_user.is_admin:
        abort(403)
    return render_template("admin_courses.html", courses=Course.query.order_by(Course.created_at.desc()).all())


@bp.get("/admin/analytics")
@login_required
def admin_analytics():
    if not current_user.is_admin:
        abort(403)
    rows = []
    for course in Course.query.order_by(Course.title).all():
        lessons = [lesson for lesson in course.lessons if not lesson.quiz_data]
        lesson_ids = [lesson.id for lesson in lessons]
        progress_rows = LessonProgress.query.filter(LessonProgress.lesson_id.in_(lesson_ids)).all() if lesson_ids else []
        attempts = QuizAttempt.query.join(Lesson).filter(Lesson.course_id == course.id).all()
        students = {row.user_id for row in progress_rows} | {row.user_id for row in attempts}
        rows.append({
            "course": course,
            "lesson_count": len(lessons),
            "completed": sum(row.completed for row in progress_rows),
            "active_students": len(students),
            "attempt_count": len(attempts),
            "average_score": round(100 * sum(row.score / row.question_count for row in attempts) / len(attempts)) if attempts else None,
        })
    return render_template("admin_analytics.html", rows=rows)


@bp.route("/admin/courses/<int:course_id>/lessons/new", methods=["GET", "POST"])
@login_required
def new_lesson(course_id):
    if not current_user.is_admin:
        abort(403)
    course = Course.query.get_or_404(course_id)
    form = LessonForm()
    if form.validate_on_submit():
        lesson = Lesson(course=course, title=form.title.data.strip(), video_url=(form.video_url.data or "").strip() or None, content=(form.content.data or "").strip(), position=len(course.lessons) + 1)
        from .extensions import db
        db.session.add(lesson)
        db.session.commit()
        flash("Урок добавлен в программу.", "success")
        return redirect(url_for("main.admin_courses"))
    return render_template("lesson_form.html", form=form, course=course)


@bp.post("/admin/courses/<int:course_id>/publish")
@login_required
def publish_course(course_id):
    if not current_user.is_admin:
        abort(403)
    course = Course.query.get_or_404(course_id)
    if not course.lessons:
        flash("Добавьте хотя бы один урок перед публикацией.", "error")
    else:
        course.published = not course.published
        from .extensions import db
        db.session.commit()
        flash("Курс опубликован." if course.published else "Курс снят с публикации.", "success")
    return redirect(url_for("main.admin_courses"))


@bp.route("/admin/users/new", methods=["GET", "POST"])
@login_required
def new_user():
    if not current_user.is_admin:
        abort(403)
    form = AdminUserForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash("Аккаунт с такой почтой уже существует.", "error")
        else:
            temporary_password = secrets.token_urlsafe(12)
            user = User(name=form.name.data.strip(), email=email)
            user.set_password(temporary_password)
            from .extensions import db
            db.session.add(user)
            db.session.commit()
            return render_template("user_created.html", user=user, temporary_password=temporary_password)
    return render_template("user_form.html", form=form)
