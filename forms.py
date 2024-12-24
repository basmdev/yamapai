from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import InputRequired


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
