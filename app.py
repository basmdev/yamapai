from flask import Flask, flash, redirect, render_template, url_for
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

import config
from forms import LoginForm, RegisterForm
from models import User, db

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.unauthorized_handler
def unauthorized():
    flash("Войдите в систему для доступа к этой странице", "warning")
    return redirect(url_for("login"))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    secret_code = config.SECRET_CODE

    if form.validate_on_submit():
        if form.secret_code.data != secret_code:
            flash("Неверный секретный код", "danger")
            return redirect(url_for("register"))

        username = form.username.data
        password = form.password.data

        if User.query.filter_by(username=username).first():
            flash("Такое имя пользователя уже существует", "danger")
            return redirect(url_for("register"))

        new_user = User(username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()
        flash("Регистрация прошла успешно", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Неверное имя пользователя или пароль", "danger")

    return render_template("login.html", form=form)


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", username=current_user.username)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
