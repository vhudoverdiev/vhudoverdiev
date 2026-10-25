"""Restricted progress management; never alters a learner's actual answers."""
from datetime import datetime
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from .extensions import db, login_manager
from .models import User, Course, Lesson, LearningOverride
from .services.learning_access import course_states

bp = Blueprint('admin_progress', __name__, url_prefix='/admin/progress')


@bp.before_request
def require_administrator():
    if not current_user.is_authenticated:
        return login_manager.unauthorized()
    if not current_user.is_admin:
        abort(403)


@bp.get('')
def index():
    users = User.query.order_by(User.name, User.id).all()
    courses = Course.query.filter_by(published=True).order_by(Course.title).all()
    user_id = request.args.get('user_id', type=int) or current_user.id
    learner = db.session.get(User, user_id)
    if not learner:
        abort(404)
    course_id = request.args.get('course_id', type=int)
    course = db.session.get(Course, course_id) if course_id else (courses[0] if courses else None)
    if course_id and not course:
        abort(404)
    modules = {}
    if course:
        for lesson in course.lessons:
            if not lesson.quiz_data:
                modules.setdefault(lesson.module_name or 'Материалы курса', []).append(lesson)
    return render_template('admin_progress.html', users=users, courses=courses, learner=learner,
                           course=course, modules=modules, states=course_states(course, learner.id) if course else {})


@bp.post('/grant')
def grant():
    learner = db.session.get(User, request.form.get('user_id', type=int))
    course = db.session.get(Course, request.form.get('course_id', type=int))
    if not learner or not course:
        abort(404)
    action = request.form.get('action')
    if action not in {'unlock_module', 'pass_module', 'unlock_lesson', 'pass_lesson'}:
        abort(400)
    lessons = [lesson for lesson in course.lessons if not lesson.quiz_data]
    if action.endswith('_module'):
        module = request.form.get('module', '')
        lessons = [lesson for lesson in lessons if (lesson.module_name or 'Материалы курса') == module]
    else:
        lesson_id = request.form.get('lesson_id', type=int)
        lessons = [lesson for lesson in lessons if lesson.id == lesson_id]
    if not lessons:
        abort(404)
    try:
        for lesson in lessons:
            override = LearningOverride.query.filter_by(user_id=learner.id, lesson_id=lesson.id).first()
            if override is None:
                override = LearningOverride(user_id=learner.id, lesson_id=lesson.id, granted_by_id=current_user.id)
                db.session.add(override)
            override.unlocked = True
            if action.startswith('pass_'):
                override.manual_score = 10
            override.granted_by_id = current_user.id
            override.updated_at = datetime.utcnow()
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('Запись уже обновляется. Повторите действие.', 'info')
    else:
        current_app.logger.info('Progress override: actor=%s learner=%s course=%s action=%s lesson_ids=%s', current_user.id, learner.id, course.id, action, [lesson.id for lesson in lessons])
        count = len(lessons)
        noun = 'урок' if count % 10 == 1 and count % 100 != 11 else 'урока' if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14) else 'уроков'
        flash(f"{'Зачтено на 10/10' if action.startswith('pass_') else 'Открыт доступ'}: {count} {noun}. Ученик: {learner.name}.", 'success')
    return redirect(url_for('admin_progress.index', user_id=learner.id, course_id=course.id), code=303)
