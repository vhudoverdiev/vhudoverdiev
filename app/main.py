from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from .forms import AdminUserForm, CourseForm, LessonForm
from .models import Course, Lesson, User
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
    return render_template("course_detail.html", course=course)


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
