from ..extensions import db
from ..models import Course


def published_courses():
    return Course.query.filter_by(published=True).order_by(Course.created_at.desc()).all()


def create_course(form):
    course = Course(
        title=form.title.data.strip(),
        category=form.category.data.strip(),
        description=form.description.data.strip(),
        level=form.level.data.strip(),
        duration=form.duration.data.strip(),
        published=False,
    )
    db.session.add(course)
    db.session.commit()
    return course
