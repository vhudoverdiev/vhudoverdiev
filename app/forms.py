from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class LoginForm(FlaskForm):
    email = StringField("Электронная почта", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class CourseForm(FlaskForm):
    title = StringField("Название курса", validators=[DataRequired(), Length(max=180)])
    category = StringField("Направление", validators=[DataRequired(), Length(max=80)])
    description = TextAreaField("Описание", validators=[DataRequired(), Length(max=1000)])
    level = StringField("Уровень", validators=[DataRequired(), Length(max=40)])
    duration = StringField("Длительность", validators=[DataRequired(), Length(max=40)])
    submit = SubmitField("Сохранить курс")


class LessonForm(FlaskForm):
    title = StringField("Название урока", validators=[DataRequired(), Length(max=180)])
    video_url = StringField("Ссылка на видео", validators=[Length(max=500)])
    content = TextAreaField("Конспект / описание", validators=[Length(max=10000)])
    submit = SubmitField("Добавить урок")


class AdminUserForm(FlaskForm):
    name = StringField("Имя ученика", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Электронная почта", validators=[DataRequired(), Email()])
    submit = SubmitField("Создать аккаунт")
