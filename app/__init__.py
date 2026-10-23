import logging
import os
from logging.handlers import RotatingFileHandler

import click
from flask import Flask
from flask.cli import with_appcontext

from config import Config
from .extensions import csrf, db, login_manager, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config.setdefault("MEDIA_ROOT", os.path.join(app.instance_path, "media"))
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401
    from .auth import bp as auth_bp
    from .main import bp as main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    from datetime import datetime
    app.context_processor(lambda: {"now": datetime.now})

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["MEDIA_ROOT"], exist_ok=True)
    handler = RotatingFileHandler(os.path.join(app.instance_path, "viti.log"), maxBytes=1_000_000, backupCount=3)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Имя администратора")
    @click.option("--email", prompt="Электронная почта")
    @click.password_option()
    @with_appcontext
    def create_admin(name, email, password):
        """Create an administrator account interactively."""
        from .models import User
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            raise click.ClickException("Пользователь с такой почтой уже существует.")
        user = User(name=name.strip(), email=email, is_admin=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Администратор {email} создан.")

    @app.cli.command("seed-demo")
    @with_appcontext
    def seed_demo():
        """Add clearly marked demo courses to an empty course catalog."""
        from .models import Course
        if Course.query.first():
            click.echo("Каталог уже содержит курсы; демо-данные не добавлены.")
            return
        demo = [
            Course(title="Как устроен IT", category="Старт в IT", description="Разберёмся в ролях, командах и том, как выбрать своё направление.", level="С нуля", duration="2 недели", icon="⌘", color="lime", published=True),
            Course(title="Основы веб-разработки", category="Разработка", description="Первые шаги в устройстве сайтов: браузер, HTML, CSS и логика интерфейса.", level="С нуля", duration="4 недели", icon="</>", color="blue", published=True),
            Course(title="Тестирование без паники", category="QA", description="Научитесь замечать проблемы и описывать их так, чтобы команда могла исправить.", level="Начальный", duration="3 недели", icon="✓", color="peach", published=True),
        ]
        db.session.add_all(demo)
        db.session.commit()
        click.echo("Добавлены демо-курсы. Замените их реальными материалами перед запуском.")

    @app.cli.command("import-courses")
    @click.option("--root", default=None, help="Папка с материалами Курсы/1…4")
    @with_appcontext
    def import_courses(root):
        """Import the four prepared course folders into the catalog."""
        from .course_importer import import_course_folders
        source = root or os.path.join(app.instance_path, "media", "courses")
        summary = import_course_folders(source)
        click.echo(summary)

    @app.errorhandler(403)
    def forbidden(_error):
        from flask import render_template
        return render_template("error.html", code=403, message="Этот раздел доступен только администратору."), 403

    @app.errorhandler(404)
    def not_found(_error):
        from flask import render_template
        return render_template("error.html", code=404, message="Кажется, эта страница потерялась."), 404

    return app
