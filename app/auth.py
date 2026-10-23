from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_user, logout_user

from .extensions import db
from .forms import LoginForm
from .models import User

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Рады видеть вас, {user.name.split()[0]}!", "success")
            return redirect(url_for("main.dashboard"))
        flash("Не получилось войти. Проверьте почту и пароль.", "error")
    return render_template("auth.html", form=form, mode="login")


@bp.post("/logout")
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("main.index"))
