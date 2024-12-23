import csv
import datetime
import os

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

import config
from forms import LoginForm
from models import Affiliate, Client, User, db

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


def process_csv_file(file_path):
    """Функция для обработки CSV файла."""
    with open(file_path, mode="r", newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            affiliate = Affiliate(
                name=row["name"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                comment=row["comment"],
            )
            db.session.add(affiliate)
    db.session.commit()


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
            return render_template("profile.html", client=client)

        client_folder = app.config["UPLOAD_FOLDER"]
        data_file_path = os.path.join(client_folder, "data.csv")

        if file:
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension != ".csv":
                flash("Неверный формат файла", "danger")
                return render_template("profile.html", client=client)

            os.makedirs(client_folder, exist_ok=True)
            temp_file_path = os.path.join(client_folder, "temp.csv")

            try:
                file.save(temp_file_path)

                db.session.query(Affiliate).delete()
                db.session.commit()

                process_csv_file(temp_file_path)

                if os.path.exists(data_file_path):
                    os.remove(data_file_path)

                os.rename(temp_file_path, data_file_path)

                if client:
                    client.name = name
                    client.csv_file_path = data_file_path
                    client.created_at = datetime.datetime.now()
                else:
                    client = Client(
                        name=name,
                        csv_file_path=data_file_path,
                        created_at=datetime.datetime.now(),
                    )
                    db.session.add(client)

                db.session.commit()
                flash("Данные изменены успешно", "success")
            except KeyError:
                if os.path.exists(data_file_path):
                    process_csv_file(data_file_path)

                os.remove(temp_file_path)
                flash("Ошибка в структуре файла CSV", "danger")
            except Exception as e:
                if os.path.exists(data_file_path):
                    process_csv_file(data_file_path)

                os.remove(temp_file_path)
                flash(f"Неизвестная ошибка, данные не изменены", "danger")

            return redirect(url_for("index"))

        if client:
            client.name = name
        else:
            client = Client(name=name)
            db.session.add(client)

        db.session.commit()
        flash("Данные изменены успешно", "success")
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
