from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="Основы")
    description = db.Column(db.Text, nullable=False, default="")
    level = db.Column(db.String(40), nullable=False, default="С нуля")
    duration = db.Column(db.String(40), nullable=False, default="4 недели")
    icon = db.Column(db.String(8), nullable=False, default="✳")
    color = db.Column(db.String(20), nullable=False, default="lime")
    published = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    lessons = db.relationship("Lesson", backref="course", cascade="all, delete-orphan", order_by="Lesson.position")


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    video_url = db.Column(db.String(500))
    content = db.Column(db.Text, nullable=False, default="")
    position = db.Column(db.Integer, nullable=False, default=0)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
