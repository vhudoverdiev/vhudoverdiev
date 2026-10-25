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

    @app.cli.command("create-user")
    @click.option("--name", prompt="Имя ученика")
    @click.option("--email", prompt="Электронная почта")
    @click.password_option()
    @with_appcontext
    def create_user(name, email, password):
        """Create a student from the terminal; no account management web UI."""
        from email_validator import validate_email, EmailNotValidError
        from .models import User
        try:
            email = validate_email(email.strip(), check_deliverability=False).normalized.lower()
        except EmailNotValidError as error:
            raise click.ClickException(str(error)) from error
        if not name.strip() or len(name.strip()) > 120 or len(password) < 8:
            raise click.ClickException("Укажите имя до 120 символов и пароль от 8 символов.")
        if User.query.filter_by(email=email).first():
            raise click.ClickException("Аккаунт с такой почтой уже существует.")
        user = User(name=name.strip(), email=email, is_admin=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Аккаунт {email} создан.")

    @app.cli.command("retire-ai-course")
    @click.option("--delete-media", is_flag=True, help="Удалить серверную папку courses/1")
    @with_appcontext
    def retire_ai_course_command(delete_media):
        """Remove the AI course retired by its owner and its learning records."""
        from .services.retired_courses import retire_ai_course
        count = retire_ai_course()
        if delete_media:
            import shutil
            from pathlib import Path
            folder = Path(app.config["MEDIA_ROOT"]) / "courses" / "1"
            if folder.is_symlink():
                folder.unlink()
            elif folder.exists():
                shutil.rmtree(folder)
        click.echo(f"Удалено курсов AI Developer: {count}.")

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
    @click.option("--root", default=None, help="Папка с материалами Курсы/2, 3, 4")
    @click.option("--course", "selected_courses", multiple=True, type=click.Choice(["2", "3", "4"]), help="Номер папки курса для импорта; можно указать несколько раз")
    @with_appcontext
    def import_courses(root, selected_courses):
        """Import selected prepared course folders into the catalog."""
        from .course_importer import import_course_folders
        source = root or os.path.join(app.instance_path, "media", "courses")
        summary = import_course_folders(source, selected_courses or ("2", "3"))
        click.echo(summary)

    @app.errorhandler(403)
    def forbidden(_error):
        from flask import render_template
        from flask import request, url_for
        locked_course_id = request.environ.get("vhiti.locked_course_id")
        message = "Сначала пройдите тест предыдущего урока: не менее 5 правильных ответов из 10." if request.path.startswith(("/courses/", "/lessons/", "/media/")) else "Недостаточно прав для этого действия."
        return render_template("error.html", code=403, message=message, back_url=url_for("main.course_detail", course_id=locked_course_id) if locked_course_id else None), 403

    @app.errorhandler(404)
    def not_found(_error):
        from flask import render_template
        return render_template("error.html", code=404, message="Кажется, эта страница потерялась."), 404

    return app
