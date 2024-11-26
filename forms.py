from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import EqualTo, InputRequired, Length


class RegisterForm(FlaskForm):
    username = StringField(
        "Username", validators=[InputRequired(), Length(min=4, max=150)]
    )
    password = PasswordField("Password", validators=[InputRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            InputRequired(),
            Length(min=6),
            EqualTo("password", message="Пароли не совпадают"),
        ],
    )
    secret_code = PasswordField("Секретный код", validators=[InputRequired()])


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
