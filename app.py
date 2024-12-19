import os

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

import config
from forms import LoginForm
from models import Client, User, db

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


def create_initial_user():
    """Создание первоначального пользователя."""
    username = os.getenv("USER")
    password = os.getenv("PASS")

    if not username or not password:
        raise ValueError("Переменные окружения USER и PASS не заданы")

    if not User.query.first():
        admin = User(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()


@login_manager.unauthorized_handler
def unauthorized():
    """Обработка запросов без авторизации."""
    flash("Войдите в систему для доступа к этой странице", "warning")
    return redirect(url_for("login"))


@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя."""
    return db.session.get(User, int(user_id))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Страница профиля организации."""
    client = Client.query.first()

    if request.method == "POST":
        name = request.form.get("name")
        file = request.files.get("file")

        if not name:
            flash("Наименование обязательно для заполнения", "danger")
            return render_template(
                "profile.html",
                client=client,
                name=name,
                file_exists=bool(client and client.csv_file_path),
            )

        if file and file.filename.endswith(".csv"):
            client_folder = app.config["UPLOAD_FOLDER"]
            os.makedirs(client_folder, exist_ok=True)

            for existing_file in os.listdir(client_folder):
                file_path = os.path.join(client_folder, existing_file)
                os.remove(file_path)

            new_file_path = os.path.join(client_folder, "data.csv")
            file.save(new_file_path)

            client.name = name
            client.csv_file_path = new_file_path
            flash("Изменения в профиле сохранены", "success")
        else:
            if client:
                client.name = name
                flash("Изменения в профиле сохранены", "success")
            else:
                client = Client(name=name)
                db.session.add(client)
                flash("Изменения в профиле сохранены", "success")

        db.session.commit()
        return redirect(url_for("index"))

    file_exists = bool(client and client.csv_file_path)
    return render_template("profile.html", client=client, file_exists=file_exists)


@app.route("/")
@login_required
def index():
    """Главная страница."""
    client = Client.query.first()
    return render_template("index.html", client=client)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Страница авторизации."""
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


@app.route("/logout")
@login_required
def logout():
    """Функция для выхода пользователя."""
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_initial_user()
    app.run(debug=True)
